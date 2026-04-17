"""Check if current time is within business hours."""

from datetime import datetime, date
import pytz
from sqlalchemy import select

from app.core.database import async_session
from app.models.business_settings import BusinessSettings


DEFAULT_HOURS = {
    "mon": {"start": "09:00", "end": "18:00", "enabled": True},
    "tue": {"start": "09:00", "end": "18:00", "enabled": True},
    "wed": {"start": "09:00", "end": "18:00", "enabled": True},
    "thu": {"start": "09:00", "end": "18:00", "enabled": True},
    "fri": {"start": "09:00", "end": "18:00", "enabled": True},
    "sat": {"start": "00:00", "end": "00:00", "enabled": False},
    "sun": {"start": "00:00", "end": "00:00", "enabled": False},
}

DAY_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}


async def get_settings() -> dict:
    """Load business settings from DB. Returns dict with all fields."""
    async with async_session() as session:
        result = await session.execute(select(BusinessSettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
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
            "working_hours": settings.working_hours or DEFAULT_HOURS,
            "timezone": settings.timezone or "Europe/Berlin",
            "outside_hours_message": settings.outside_hours_message or "",
            "outside_hours_enabled": settings.outside_hours_enabled if settings.outside_hours_enabled is not None else True,
            "holidays": settings.holidays or [],
            "holiday_message": settings.holiday_message or "",
            "auto_archive_hours": settings.auto_archive_hours or "48",
        }


async def is_within_business_hours() -> tuple:
    """Returns (is_open: bool, message_if_closed: str)"""
    settings = await get_settings()

    if not settings["outside_hours_enabled"]:
        return True, ""

    try:
        tz = pytz.timezone(settings["timezone"])
    except Exception:
        tz = pytz.timezone("Europe/Berlin")

    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d")

    # Check holidays
    if today_str in settings["holidays"]:
        return False, settings["holiday_message"]

    # Check working hours for today
    day_key = DAY_MAP.get(now.weekday(), "mon")
    hours = settings["working_hours"].get(day_key, {})

    if not hours.get("enabled", False):
        return False, settings["outside_hours_message"]

    start_str = hours.get("start", "09:00")
    end_str = hours.get("end", "18:00")

    try:
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))

        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= current_minutes <= end_minutes:
            return True, ""
        else:
            return False, settings["outside_hours_message"]
    except Exception:
        return True, ""
