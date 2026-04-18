"""Saved landing pages model."""

from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class LandingPage(Base):
    __tablename__ = "landing_pages"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    customer_name = Column(String, default="")
    customer_company = Column(String, default="")
    html_content = Column(Text, default="")
    style = Column(String, default="modern")
    color_scheme = Column(String, default="auto")
    language = Column(String, default="en")
    status = Column(String, default="draft")  # draft, published, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
