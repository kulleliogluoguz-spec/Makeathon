"""Conversations dashboard API - list and view conversation states."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/conversations/")
async def list_conversations(
    tag: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations ordered by most recent activity."""
    result = await db.execute(
        select(ConversationState).order_by(desc(ConversationState.last_message_at))
    )
    states = result.scalars().all()

    if tag:
        states = [s for s in states if tag in (s.categories or [])]

    return [
        {
            "id": s.id,
            "sender_id": s.sender_id,
            "persona_id": s.persona_id,
            "channel": s.channel,
            "intent_score": s.intent_score,
            "stage": s.stage,
            "signals": s.signals or [],
            "next_action": s.next_action,
            "score_breakdown": s.score_breakdown,
            "categories": s.categories or [],
            "message_count": s.message_count,
            "products_mentioned": s.products_mentioned or [],
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in states
    ]


@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Search inside all conversation messages for a keyword."""
    result = await db.execute(select(ConversationState).order_by(desc(ConversationState.last_message_at)))
    all_convs = result.scalars().all()

    matches = []
    query_lower = q.lower()

    for conv in all_convs:
        msgs = conv.messages or []
        matching_msgs = []
        for i, m in enumerate(msgs):
            if query_lower in (m.get("content", "") or "").lower():
                matching_msgs.append({
                    "index": i,
                    "role": m.get("role", ""),
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp", ""),
                })

        if matching_msgs:
            matches.append({
                "conversation_id": conv.id,
                "sender_id": conv.sender_id,
                "channel": conv.channel,
                "intent_score": conv.intent_score,
                "stage": conv.stage,
                "categories": conv.categories or [],
                "message_count": conv.message_count,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "matching_messages": matching_msgs[:5],
                "total_matches": len(matching_msgs),
            })

    return {"query": q, "total_conversations": len(matches), "results": matches}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get full details of a single conversation including messages and score history."""
    result = await db.execute(
        select(ConversationState).where(ConversationState.id == conversation_id)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": state.id,
        "sender_id": state.sender_id,
        "persona_id": state.persona_id,
        "channel": state.channel,
        "intent_score": state.intent_score,
        "stage": state.stage,
        "signals": state.signals or [],
        "next_action": state.next_action,
        "score_breakdown": state.score_breakdown,
        "score_history": state.score_history or [],
        "messages": state.messages or [],
        "message_count": state.message_count,
        "categories": state.categories or [],
        "products_mentioned": state.products_mentioned or [],
        "last_message_at": state.last_message_at.isoformat() if state.last_message_at else None,
        "created_at": state.created_at.isoformat() if state.created_at else None,
    }
