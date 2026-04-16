"""CSAT survey responses."""

from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class CSATResponse(Base):
    __tablename__ = "csat_responses"

    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, nullable=False, index=True)
    sender_id = Column(String, nullable=False, index=True)
    channel = Column(String, default="")
    rating = Column(Integer, nullable=False)  # 1-5
    feedback = Column(Text, default="")  # optional text feedback
    created_at = Column(DateTime, default=datetime.utcnow)
