"""Team/Department model."""

from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    color = Column(String, default="#3b82f6")
    member_ids = Column(JSON, default=list)
    auto_assign_enabled = Column(String, default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
