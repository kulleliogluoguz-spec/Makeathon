"""Conversation management and workflow execution engine."""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime

from app.core.database import get_db, async_session
from app.models.models import (
    Conversation, ConversationMessage, Agent, Workflow, WorkflowNode, WorkflowEdge
)
from app.schemas.schemas import ConversationCreate, ConversationResponse, ConversationMessageResponse

router = APIRouter()


# ─── Conversation CRUD ────────────────────────────────────────────────

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    agent_id: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Conversation).options(selectinload(Conversation.messages))
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    if status:
        query = query.where(Conversation.status == status)
    query = query.order_by(Conversation.started_at.desc())
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/", response_model=ConversationResponse, status_code=201)
async def start_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """Start a new conversation — initializes from agent's active workflow."""
    # Get agent
    agent_result = await db.execute(select(Agent).where(Agent.id == data.agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Initialize conversation
    conversation = Conversation(
        agent_id=data.agent_id,
        caller_phone=data.caller_phone,
        caller_name=data.caller_name,
        caller_email=data.caller_email,
    )

    # If agent has active workflow, find start node
    if agent.active_workflow_id:
        workflow_result = await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.nodes))
            .where(Workflow.id == agent.active_workflow_id)
        )
        workflow = workflow_result.scalar_one_or_none()
        if workflow:
            conversation.variables = workflow.variables.copy()
            start_node = next(
                (n for n in workflow.nodes if n.node_type.value == "start"),
                None,
            )
            if start_node:
                conversation.current_node_id = start_node.id

    db.add(conversation)
    await db.flush()

    # Add first message if agent has one
    if agent.first_message:
        msg = ConversationMessage(
            conversation_id=conversation.id,
            role="agent",
            content=agent.first_message,
            node_id=conversation.current_node_id,
        )
        db.add(msg)
        conversation.total_messages = 1

    await db.flush()

    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    return result.scalar_one()


@router.post("/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def add_message(
    conversation_id: str,
    role: str = "caller",
    content: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Add a message to the conversation and advance the workflow."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save caller message
    msg = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(msg)
    conv.total_messages += 1
    await db.flush()
    await db.refresh(msg)
    return msg


@router.post("/{conversation_id}/end")
async def end_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.status = "completed"
    conv.ended_at = datetime.utcnow()
    if conv.started_at:
        conv.duration_seconds = int((conv.ended_at - conv.started_at).total_seconds())

    await db.flush()
    return {"status": "completed", "duration_seconds": conv.duration_seconds}


# ─── Analytics ────────────────────────────────────────────────────────

@router.get("/analytics/summary")
async def conversation_analytics(agent_id: str = None, db: AsyncSession = Depends(get_db)):
    """Get conversation analytics summary."""
    query = select(Conversation)
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)

    result = await db.execute(query)
    conversations = result.scalars().all()

    total = len(conversations)
    completed = sum(1 for c in conversations if c.status == "completed")
    avg_duration = (
        sum(c.duration_seconds for c in conversations if c.duration_seconds > 0) / max(completed, 1)
    )
    avg_messages = sum(c.total_messages for c in conversations) / max(total, 1)
    avg_sentiment = None
    sentiments = [c.sentiment_score for c in conversations if c.sentiment_score is not None]
    if sentiments:
        avg_sentiment = sum(sentiments) / len(sentiments)

    return {
        "total_conversations": total,
        "completed": completed,
        "active": sum(1 for c in conversations if c.status == "active"),
        "failed": sum(1 for c in conversations if c.status == "failed"),
        "avg_duration_seconds": round(avg_duration, 1),
        "avg_messages": round(avg_messages, 1),
        "avg_sentiment": round(avg_sentiment, 2) if avg_sentiment else None,
        "completion_rate": round(completed / max(total, 1) * 100, 1),
    }


# ─── WebSocket for real-time voice ────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[conversation_id] = websocket

    def disconnect(self, conversation_id: str):
        self.active_connections.pop(conversation_id, None)

    async def send_message(self, conversation_id: str, data: dict):
        ws = self.active_connections.get(conversation_id)
        if ws:
            await ws.send_json(data)


manager = ConnectionManager()


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time voice conversation.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 audio>"}
    - Client sends: {"type": "text", "content": "user message"}
    - Server sends: {"type": "transcript", "content": "transcribed text", "role": "caller"}
    - Server sends: {"type": "response", "content": "agent response", "audio": "<base64>"}
    - Server sends: {"type": "node_change", "node_id": "...", "node_type": "..."}
    - Server sends: {"type": "variable_update", "variable": "...", "value": "..."}
    - Server sends: {"type": "end", "reason": "workflow_complete"}
    """
    await manager.connect(conversation_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "text":
                # Process text message through workflow engine
                async with async_session() as db:
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conv = result.scalar_one_or_none()
                    if not conv:
                        await websocket.send_json({"type": "error", "message": "Conversation not found"})
                        continue

                    # Save message
                    msg = ConversationMessage(
                        conversation_id=conversation_id,
                        role="caller",
                        content=data["content"],
                    )
                    db.add(msg)
                    conv.total_messages += 1
                    await db.commit()

                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "transcript",
                        "content": data["content"],
                        "role": "caller",
                    })

                    # TODO: Process through LLM + workflow engine
                    # This is where you'd integrate with the LLM provider
                    # For now, echo back a placeholder
                    await websocket.send_json({
                        "type": "response",
                        "content": f"[Agent response to: {data['content']}]",
                        "role": "agent",
                    })

            elif data.get("type") == "audio":
                # TODO: Process audio through STT -> LLM -> TTS pipeline
                await websocket.send_json({
                    "type": "processing",
                    "stage": "stt",
                })

            elif data.get("type") == "end":
                async with async_session() as db:
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conv = result.scalar_one_or_none()
                    if conv:
                        conv.status = "completed"
                        conv.ended_at = datetime.utcnow()
                        await db.commit()
                break

    except WebSocketDisconnect:
        manager.disconnect(conversation_id)
