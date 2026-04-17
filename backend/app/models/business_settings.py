"""Business settings — working hours, holidays, auto-reply messages."""

from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BusinessSettings(Base):
    __tablename__ = "business_settings"

    id = Column(String, primary_key=True, default=gen_uuid)

    # Working hours: {"mon": {"start": "09:00", "end": "18:00", "enabled": true}, ...}
    working_hours = Column(JSON, default=dict)

    # Timezone (IANA format)
    timezone = Column(String, default="Europe/Berlin")

    # Auto-reply when outside business hours
    outside_hours_message = Column(Text, default="We are currently outside of business hours. We will get back to you as soon as possible. Business hours: Monday-Friday 09:00-18:00")
    outside_hours_enabled = Column(Boolean, default=True)

    # Holiday dates: ["2026-01-01", "2026-04-23", ...]
    holidays = Column(JSON, default=list)
    holiday_message = Column(Text, default="We are closed today due to a holiday. We will get back to you on the next business day.")

    # Auto-archive inactive conversations after N hours (0 = disabled)
    auto_archive_hours = Column(String, default="48")

    updated_at = Column(DateTime, default=datetime.utcnow)
