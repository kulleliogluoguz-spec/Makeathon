"""AI lessons learned from past conversations."""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AILesson(Base):
    __tablename__ = "ai_lessons"

    id = Column(String, primary_key=True, default=gen_uuid)

    # What happened
    category = Column(String, default="")  # pricing, objection, greeting, closing, product_pitch, tone, pushy, timing

    # The mistake
    ai_said = Column(Text, default="")  # What the AI said
    customer_reaction = Column(Text, default="")  # How customer reacted (negative)
    outcome = Column(String, default="")  # lost_customer, negative_feedback, low_csat, objection, ignored

    # The lesson
    lesson = Column(Text, default="")  # What the AI should do differently
    better_alternative = Column(Text, default="")  # What should be said instead

    # Context
    channel = Column(String, default="")
    conversation_id = Column(String, default="")

    # Weight — how important this lesson is (increases each time same mistake is detected)
    weight = Column(Integer, default=1)
    times_applied = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
