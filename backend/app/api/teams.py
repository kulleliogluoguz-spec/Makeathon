"""Team management API."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.team import Team
from app.models.user import User

router = APIRouter()


@router.get("/teams/")
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team))
    teams = result.scalars().all()
    return [_serialize(t) for t in teams]


@router.post("/teams/")
async def create_team(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(status_code=400, detail="Name required")
    team = Team(
        name=body["name"],
        description=body.get("description", ""),
        color=body.get("color", "#3b82f6"),
        member_ids=body.get("member_ids", []),
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return _serialize(team)


@router.patch("/teams/{team_id}")
async def update_team(team_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    for field in ("name", "description", "color", "member_ids", "auto_assign_enabled"):
        if field in body:
            setattr(team, field, body[field])
    team.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(team)
    return _serialize(team)


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    await db.delete(team)
    await db.commit()
    return {"status": "deleted"}


@router.post("/teams/{team_id}/members")
async def add_member(team_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    user_id = body.get("user_id", "")
    if not user_id:
        raise HTTPException(status_code=400)
    members = list(team.member_ids or [])
    if user_id not in members:
        members.append(user_id)
    team.member_ids = members
    await db.commit()
    return {"status": "added", "members": members}


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_member(team_id: str, user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)
    members = list(team.member_ids or [])
    members = [m for m in members if m != user_id]
    team.member_ids = members
    await db.commit()
    return {"status": "removed", "members": members}


@router.get("/teams/{team_id}/conversations")
async def get_team_conversations(team_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.conversation_state import ConversationState
    from sqlalchemy import or_

    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404)

    member_ids = team.member_ids or []

    conv_query = select(ConversationState).where(
        or_(
            ConversationState.assigned_team == team_id,
            ConversationState.assigned_to.in_(member_ids) if member_ids else False,
        )
    )
    conv_result = await db.execute(conv_query)
    conversations = conv_result.scalars().all()

    return [
        {
            "id": c.id,
            "sender_id": c.sender_id,
            "channel": c.channel,
            "intent_score": c.intent_score,
            "stage": c.stage,
            "assigned_to": c.assigned_to or "",
            "response_mode": c.response_mode or "ai_auto",
            "message_count": c.message_count,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        }
        for c in conversations
    ]


def _serialize(t: Team) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "color": t.color or "#3b82f6",
        "member_ids": t.member_ids or [],
        "auto_assign_enabled": t.auto_assign_enabled == "true",
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
