"""Agent CRUD API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import Agent
from app.schemas.schemas import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    status: str = None,
    category: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent)
    if status:
        query = query.where(Agent.status == status)
    if category:
        query = query.where(Agent.category == category)
    query = query.order_by(Agent.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        **data.model_dump(exclude={"voice_settings"}),
        voice_settings=data.voice_settings.model_dump(),
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = data.model_dump(exclude_unset=True)
    if "voice_settings" in update_data and update_data["voice_settings"]:
        update_data["voice_settings"] = update_data["voice_settings"].model_dump() if hasattr(update_data["voice_settings"], "model_dump") else update_data["voice_settings"]

    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.flush()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_agent = Agent(
        name=f"{agent.name} (Copy)",
        description=agent.description,
        category=agent.category,
        tags=agent.tags,
        persona_id=agent.persona_id,
        voice_provider=agent.voice_provider,
        voice_id=agent.voice_id,
        voice_model=agent.voice_model,
        voice_settings=agent.voice_settings,
        llm_provider=agent.llm_provider,
        llm_model=agent.llm_model,
        llm_temperature=agent.llm_temperature,
        llm_max_tokens=agent.llm_max_tokens,
        first_message=agent.first_message,
        end_call_message=agent.end_call_message,
        max_conversation_duration=agent.max_conversation_duration,
        silence_timeout=agent.silence_timeout,
        interruption_threshold=agent.interruption_threshold,
        enable_backchannel=agent.enable_backchannel,
        backchannel_words=agent.backchannel_words,
        language=agent.language,
        fallback_language=agent.fallback_language,
    )
    db.add(new_agent)
    await db.flush()
    await db.refresh(new_agent)
    return new_agent
