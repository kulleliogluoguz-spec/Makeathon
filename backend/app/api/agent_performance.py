"""Agent performance metrics API."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.conversation_state import ConversationState
from app.models.csat import CSATResponse

router = APIRouter()


def get_cutoff(period: str):
    if period == "today":
        return datetime.utcnow().replace(hour=0, minute=0, second=0)
    elif period == "week":
        return datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        return datetime.utcnow() - timedelta(days=30)
    return None


@router.get("/agent-performance/")
async def get_all_agent_performance(period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    cutoff = get_cutoff(period)

    user_result = await db.execute(
        select(User).where(User.role.in_(["agent", "supervisor", "admin"]))
    )
    users = user_result.scalars().all()

    conv_query = select(ConversationState)
    if cutoff:
        conv_query = conv_query.where(ConversationState.last_message_at >= cutoff)
    conv_result = await db.execute(conv_query)
    all_convs = conv_result.scalars().all()

    csat_query = select(CSATResponse)
    if cutoff:
        csat_query = csat_query.where(CSATResponse.created_at >= cutoff)
    csat_result = await db.execute(csat_query)
    all_csat = csat_result.scalars().all()

    metrics = []
    for user in users:
        user_convs = [c for c in all_convs if c.assigned_to == user.id]
        total_convs = len(user_convs)
        total_messages = sum(c.message_count or 0 for c in user_convs)
        resolved = sum(1 for c in user_convs if c.stage in ("purchase", "post_purchase"))
        avg_intent = round(sum(c.intent_score or 0 for c in user_convs) / max(total_convs, 1), 1)

        conv_ids = {c.id for c in user_convs}
        user_csat = [r for r in all_csat if r.conversation_id in conv_ids]
        avg_csat = round(sum(r.rating for r in user_csat) / max(len(user_csat), 1), 1) if user_csat else 0

        high_intent = sum(1 for c in user_convs if (c.intent_score or 0) >= 70)
        active = sum(1 for c in user_convs if c.stage not in ("post_purchase",))

        metrics.append({
            "user_id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "total_conversations": total_convs,
            "total_messages": total_messages,
            "resolved_conversations": resolved,
            "active_conversations": active,
            "avg_intent_score": avg_intent,
            "high_intent_count": high_intent,
            "avg_csat": avg_csat,
            "csat_count": len(user_csat),
        })

    metrics.sort(key=lambda x: x["total_conversations"], reverse=True)
    return {"period": period, "agents": metrics}


@router.get("/agent-performance/{user_id}")
async def get_agent_detail(user_id: str, period: str = Query("month"), db: AsyncSession = Depends(get_db)):
    cutoff = get_cutoff(period)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    conv_query = select(ConversationState).where(ConversationState.assigned_to == user_id)
    if cutoff:
        conv_query = conv_query.where(ConversationState.last_message_at >= cutoff)
    conv_result = await db.execute(conv_query)
    convs = conv_result.scalars().all()

    channel_counts = {}
    stage_counts = {}
    for c in convs:
        ch = c.channel or "unknown"
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
        st = c.stage or "awareness"
        stage_counts[st] = stage_counts.get(st, 0) + 1

    return {
        "user": {"id": user.id, "display_name": user.display_name, "role": user.role},
        "total_conversations": len(convs),
        "channel_breakdown": channel_counts,
        "stage_breakdown": stage_counts,
        "conversations": [
            {
                "id": c.id, "sender_id": c.sender_id, "channel": c.channel,
                "intent_score": c.intent_score, "stage": c.stage,
                "response_mode": c.response_mode, "message_count": c.message_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in convs[:50]
        ],
    }
