"""Meeting model — scheduled meetings from HappyRobot calls."""

from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=gen_uuid)
    customer_name = Column(String, default="")
    customer_company = Column(String, default="")
    customer_title = Column(String, default="")
    customer_phone = Column(String, default="")
    customer_email = Column(String, default="")
    customer_linkedin = Column(String, default="")

    # Meeting details
    scheduled_date = Column(DateTime, nullable=False)
    duration_minutes = Column(String, default="15")
    meeting_type = Column(String, default="call")  # call, video, in_person
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled, no_show

    # How they were contacted
    source_channel = Column(String, default="")  # linkedin, instagram, messenger, telegram, phone
    initial_contact_method = Column(String, default="")  # ai_call, linkedin_invite, dm_conversation

    # AI-generated report
    conversation_summary = Column(Text, default="")
    customer_interests = Column(Text, default="")
    recommended_approach = Column(Text, default="")
    talking_points = Column(JSON, default=list)
    risk_factors = Column(Text, default="")
    estimated_deal_value = Column(String, default="")

    # Call transcript from HappyRobot
    call_transcript = Column(Text, default="")
    call_duration_seconds = Column(String, default="")
    call_id = Column(String, default="")

    # Admin availability
    assigned_to = Column(String, default="")  # user_id of sales manager
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
