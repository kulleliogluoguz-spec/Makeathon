"""Auto-assignment of conversations to agents (round-robin)."""

from sqlalchemy import select, func
from app.core.database import async_session
from app.models.user import User
from app.models.conversation_state import ConversationState


async def get_next_agent() -> str:
    """Get the agent with fewest active conversations for round-robin assignment."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_active == True, User.role == "agent")
        )
        agents = result.scalars().all()

        if not agents:
            result = await session.execute(
                select(User).where(User.is_active == True, User.role == "supervisor")
            )
            agents = result.scalars().all()

        if not agents:
            return ""

        agent_loads = {}
        for agent in agents:
            conv_result = await session.execute(
                select(func.count()).where(
                    ConversationState.assigned_to == agent.id,
                    ConversationState.stage != "post_purchase",
                )
            )
            count = conv_result.scalar() or 0
            agent_loads[agent.id] = count

        return min(agent_loads, key=agent_loads.get)


async def auto_assign_conversation(sender_id: str):
    """Assign a conversation to the next available agent if not already assigned."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        conv = result.scalar_one_or_none()

        if not conv or conv.assigned_to:
            return

        agent_id = await get_next_agent()
        if agent_id:
            conv.assigned_to = agent_id
            await session.commit()
            print(f"Auto-assigned {sender_id} to agent {agent_id}")
