"""Business settings API."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business_settings import BusinessSettings

router = APIRouter()


@router.get("/settings/business-hours")
async def get_business_hours(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BusinessSettings).limit(1))
    s = result.scalar_one_or_none()
    if not s:
        from app.services.business_hours import DEFAULT_HOURS
        return {
            "working_hours": DEFAULT_HOURS,
            "timezone": "Europe/Berlin",
            "outside_hours_message": "We are currently outside of business hours. We will get back to you as soon as possible.",
            "outside_hours_enabled": True,
            "holidays": [],
            "holiday_message": "We are closed today due to a holiday.",
            "auto_archive_hours": "48",
        }
    return {
        "working_hours": s.working_hours or {},
        "timezone": s.timezone,
        "outside_hours_message": s.outside_hours_message,
        "outside_hours_enabled": s.outside_hours_enabled,
        "holidays": s.holidays or [],
        "holiday_message": s.holiday_message,
        "auto_archive_hours": s.auto_archive_hours,
    }


@router.put("/settings/business-hours")
async def update_business_hours(body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BusinessSettings).limit(1))
    s = result.scalar_one_or_none()
    if not s:
        s = BusinessSettings()
        db.add(s)

    for field in ("working_hours", "timezone", "outside_hours_message",
                  "outside_hours_enabled", "holidays", "holiday_message", "auto_archive_hours"):
        if field in body:
            setattr(s, field, body[field])

    s.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(s)
    return {"status": "saved"}
