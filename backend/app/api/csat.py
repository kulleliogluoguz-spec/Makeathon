"""CSAT survey API — send surveys and collect ratings."""

import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.models.csat import CSATResponse
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/csat/responses")
async def list_csat_responses(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """List all CSAT responses with optional time filter."""
    query = select(CSATResponse).order_by(desc(CSATResponse.created_at))

    if period == "today":
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
        query = query.where(CSATResponse.created_at >= cutoff)
    elif period == "week":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=7))
    elif period == "month":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=30))

    result = await db.execute(query)
    responses = result.scalars().all()

    return [
        {
            "id": r.id,
            "conversation_id": r.conversation_id,
            "sender_id": r.sender_id,
            "channel": r.channel,
            "rating": r.rating,
            "feedback": r.feedback or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in responses
    ]


@router.get("/csat/stats")
async def get_csat_stats(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """Get CSAT statistics: average rating, distribution, response count."""
    query = select(CSATResponse)

    if period == "today":
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
        query = query.where(CSATResponse.created_at >= cutoff)
    elif period == "week":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=7))
    elif period == "month":
        query = query.where(CSATResponse.created_at >= datetime.utcnow() - timedelta(days=30))

    result = await db.execute(query)
    responses = result.scalars().all()

    total = len(responses)
    if total == 0:
        return {
            "total_responses": 0,
            "average_rating": 0,
            "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "satisfaction_rate": 0,
        }

    avg = round(sum(r.rating for r in responses) / total, 1)
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in responses:
        if 1 <= r.rating <= 5:
            dist[r.rating] += 1

    satisfied = dist[4] + dist[5]
    sat_rate = round((satisfied / total) * 100, 1) if total > 0 else 0

    return {
        "total_responses": total,
        "average_rating": avg,
        "distribution": dist,
        "satisfaction_rate": sat_rate,
    }


@router.post("/csat/submit")
async def submit_csat(body: dict, db: AsyncSession = Depends(get_db)):
    """Submit a CSAT rating."""
    response = CSATResponse(
        conversation_id=body.get("conversation_id", ""),
        sender_id=body.get("sender_id", ""),
        channel=body.get("channel", ""),
        rating=max(1, min(5, int(body.get("rating", 3)))),
        feedback=body.get("feedback", ""),
    )
    db.add(response)
    await db.commit()
    return {"status": "submitted", "id": response.id}


@router.get("/csat/conversation/{conversation_id}")
async def get_conversation_csat(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get CSAT rating for a specific conversation."""
    result = await db.execute(
        select(CSATResponse)
        .where(CSATResponse.conversation_id == conversation_id)
        .order_by(desc(CSATResponse.created_at))
        .limit(1)
    )
    response = result.scalar_one_or_none()
    if not response:
        return {"has_rating": False}
    return {
        "has_rating": True,
        "rating": response.rating,
        "feedback": response.feedback or "",
        "created_at": response.created_at.isoformat() if response.created_at else None,
    }
