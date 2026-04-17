"""Saved leads model."""

from sqlalchemy import Column, String, Text, DateTime, Integer
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SavedLead(Base):
    __tablename__ = "saved_leads"

    id = Column(String, primary_key=True, default=gen_uuid)
    apollo_id = Column(String, default="", index=True)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    title = Column(String, default="")
    company_name = Column(String, default="")
    company_industry = Column(String, default="")
    company_size = Column(String, default="")
    company_revenue = Column(String, default="")
    company_website = Column(String, default="")
    linkedin_url = Column(String, default="")
    city = Column(String, default="")
    country = Column(String, default="")
    ai_score = Column(Integer, default=0)
    ai_reason = Column(Text, default="")
    ai_approach = Column(Text, default="")
    status = Column(String, default="new")  # new, contacted, responded, converted, rejected
    notes = Column(Text, default="")
    outreach_message = Column(Text, default="")
    persona_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
