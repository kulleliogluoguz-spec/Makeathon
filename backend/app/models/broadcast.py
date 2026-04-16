"""Broadcast campaign model."""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    subject = Column(String, default="")
    message = Column(Text, nullable=False)
    channels = Column(JSON, default=list)
    recipient_filter = Column(JSON, default=dict)
    recipient_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String, default="draft")
    results = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
