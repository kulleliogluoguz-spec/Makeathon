"""Meetings API — calendar, reports, availability."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.meeting import Meeting
from app.models.availability import Availability

router = APIRouter()


@router.get("/meetings/")
async def list_meetings(
    status: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Meeting).order_by(Meeting.scheduled_date)
    if status:
        query = query.where(Meeting.status == status)
    if month:
        try:
            year, mon = month.split("-")
            start = datetime(int(year), int(mon), 1)
            if int(mon) == 12:
                end = datetime(int(year) + 1, 1, 1)
            else:
                end = datetime(int(year), int(mon) + 1, 1)
            query = query.where(Meeting.scheduled_date >= start, Meeting.scheduled_date < end)
        except Exception:
            pass
    result = await db.execute(query)
    return [_serialize_meeting(m) for m in result.scalars().all()]


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404)
    return _serialize_meeting(meeting)


@router.post("/meetings/")
async def create_meeting(body: dict, db: AsyncSession = Depends(get_db)):
    meeting = Meeting(
        customer_name=body.get("customer_name", ""),
        customer_company=body.get("customer_company", ""),
        customer_title=body.get("customer_title", ""),
        customer_phone=body.get("customer_phone", ""),
        customer_email=body.get("customer_email", ""),
        customer_linkedin=body.get("customer_linkedin", ""),
        scheduled_date=datetime.fromisoformat(body.get("scheduled_date", datetime.utcnow().isoformat())),
        duration_minutes=str(body.get("duration_minutes", "15")),
        meeting_type=body.get("meeting_type", "call"),
        status=body.get("status", "scheduled"),
        source_channel=body.get("source_channel", ""),
        initial_contact_method=body.get("initial_contact_method", ""),
        conversation_summary=body.get("conversation_summary", ""),
        customer_interests=body.get("customer_interests", ""),
        recommended_approach=body.get("recommended_approach", ""),
        talking_points=body.get("talking_points", []),
        risk_factors=body.get("risk_factors", ""),
        estimated_deal_value=body.get("estimated_deal_value", ""),
        call_transcript=body.get("call_transcript", ""),
        call_duration_seconds=str(body.get("call_duration_seconds", "")),
        call_id=body.get("call_id", ""),
        assigned_to=body.get("assigned_to", ""),
        notes=body.get("notes", ""),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return _serialize_meeting(meeting)


@router.patch("/meetings/{meeting_id}")
async def update_meeting(meeting_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404)
    for field in ("status", "notes", "assigned_to", "scheduled_date"):
        if field in body:
            if field == "scheduled_date":
                setattr(meeting, field, datetime.fromisoformat(body[field]))
            else:
                setattr(meeting, field, body[field])
    meeting.updated_at = datetime.utcnow()
    await db.commit()
    return _serialize_meeting(meeting)


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404)
    await db.delete(meeting)
    await db.commit()
    return {"status": "deleted"}


# Availability
@router.get("/availability/")
async def get_availability(user_id: str = Query(""), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Availability).limit(1))
    avail = result.scalar_one_or_none()
    if not avail:
        return {
            "weekly_schedule": {
                "mon": {"start": "09:00", "end": "17:00", "enabled": True},
                "tue": {"start": "09:00", "end": "17:00", "enabled": True},
                "wed": {"start": "09:00", "end": "17:00", "enabled": True},
                "thu": {"start": "09:00", "end": "17:00", "enabled": True},
                "fri": {"start": "09:00", "end": "17:00", "enabled": True},
                "sat": {"start": "00:00", "end": "00:00", "enabled": False},
                "sun": {"start": "00:00", "end": "00:00", "enabled": False},
            },
            "blocked_dates": [],
            "default_duration": "15",
            "buffer_minutes": "10",
            "timezone": "Europe/Berlin",
        }
    return {
        "weekly_schedule": avail.weekly_schedule or {},
        "blocked_dates": avail.blocked_dates or [],
        "default_duration": avail.default_duration,
        "buffer_minutes": avail.buffer_minutes,
        "timezone": avail.timezone,
    }


@router.put("/availability/")
async def update_availability(body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Availability).limit(1))
    avail = result.scalar_one_or_none()
    if not avail:
        avail = Availability(user_id="admin")
        db.add(avail)
    for field in ("weekly_schedule", "blocked_dates", "default_duration", "buffer_minutes", "timezone"):
        if field in body:
            setattr(avail, field, body[field])
    avail.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "saved"}


def _serialize_meeting(m: Meeting) -> dict:
    return {
        "id": m.id,
        "customer_name": m.customer_name,
        "customer_company": m.customer_company,
        "customer_title": m.customer_title,
        "customer_phone": m.customer_phone,
        "customer_email": m.customer_email,
        "customer_linkedin": m.customer_linkedin,
        "scheduled_date": m.scheduled_date.isoformat() if m.scheduled_date else None,
        "duration_minutes": m.duration_minutes,
        "meeting_type": m.meeting_type,
        "status": m.status,
        "source_channel": m.source_channel,
        "initial_contact_method": m.initial_contact_method,
        "conversation_summary": m.conversation_summary,
        "customer_interests": m.customer_interests,
        "recommended_approach": m.recommended_approach,
        "talking_points": m.talking_points or [],
        "risk_factors": m.risk_factors,
        "estimated_deal_value": m.estimated_deal_value,
        "call_transcript": m.call_transcript,
        "call_duration_seconds": m.call_duration_seconds,
        "call_id": m.call_id,
        "assigned_to": m.assigned_to,
        "notes": m.notes or "",
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
