"""Admin availability for meetings."""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Availability(Base):
    __tablename__ = "availability"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, nullable=False)

    # Weekly schedule: {"mon": {"start": "09:00", "end": "17:00", "enabled": true}, ...}
    weekly_schedule = Column(JSON, default=dict)

    # Blocked dates: ["2026-04-20", "2026-04-25"]
    blocked_dates = Column(JSON, default=list)

    # Meeting preferences
    default_duration = Column(String, default="15")
    buffer_minutes = Column(String, default="10")
    timezone = Column(String, default="Europe/Berlin")

    updated_at = Column(DateTime, default=datetime.utcnow)
