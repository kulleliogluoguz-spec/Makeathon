"""Category/Tag model for conversation classification."""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    color = Column(String, default="#64748b")
    is_builtin = Column(Boolean, default=False)
    sort_order = Column(String, default="0")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
