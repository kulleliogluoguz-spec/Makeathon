"""Quick reply templates for common questions."""

from sqlalchemy import Column, String, Text, DateTime, Integer
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class QuickReply(Base):
    __tablename__ = "quick_replies"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)  # Short label: "Return Policy"
    content = Column(Text, nullable=False)   # Full reply text
    category = Column(String, default="")    # Optional grouping: "shipping", "payment", etc.
    keywords = Column(String, default="")    # Comma-separated trigger words: "return,refund,exchange"
    use_count = Column(Integer, default=0)   # How many times used
    persona_id = Column(String, default="")  # Optional: link to specific persona, empty = all
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
