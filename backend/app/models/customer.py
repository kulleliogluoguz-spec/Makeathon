"""Customer CRM model — unified identity across all channels."""

from sqlalchemy import Column, String, Text, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=gen_uuid)

    # Identity
    display_name = Column(String, default="")
    handle = Column(String, default="")  # @username on the source platform
    email = Column(String, default="")
    phone = Column(String, default="")
    avatar_url = Column(String, default="")

    # Classification
    tags = Column(JSON, default=list)  # ["vip", "wholesale", ...]
    custom_fields = Column(JSON, default=dict)  # {"company": "X", "source": "ads"}
    notes = Column(Text, default="")

    # Source & External IDs
    source = Column(String, default="manual")  # "instagram" | "manual" | "whatsapp" | "livechat"
    instagram_sender_id = Column(String, default="", index=True)
    whatsapp_phone = Column(String, default="", index=True)
    external_ids = Column(JSON, default=dict)  # flexible future-proof

    # Stats (updated by system)
    last_contact_at = Column(DateTime, nullable=True)
    total_messages = Column(String, default="0")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
