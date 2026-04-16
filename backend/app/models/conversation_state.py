"""Conversation state tracking — per-customer intent scoring."""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(String, primary_key=True, default=gen_uuid)
    sender_id = Column(String, nullable=False, index=True, unique=True)  # Instagram sender ID
    persona_id = Column(String, nullable=True, index=True)
    channel = Column(String, default="instagram")  # for future: whatsapp, voice, etc.

    # Current scoring snapshot
    intent_score = Column(Integer, default=0)
    stage = Column(String, default="awareness")
    signals = Column(JSON, default=list)
    next_action = Column(String, default="")
    score_breakdown = Column(Text, default="")

    # History of score changes (for timeline)
    score_history = Column(JSON, default=list)  # [{timestamp, score, stage, trigger_message}]

    # Message history (full transcript for dashboard)
    messages = Column(JSON, default=list)  # [{role, content, timestamp}]

    # Metadata
    message_count = Column(Integer, default=0)
    products_mentioned = Column(JSON, default=list)  # product IDs mentioned
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
