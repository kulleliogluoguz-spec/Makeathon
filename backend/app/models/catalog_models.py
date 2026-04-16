"""Catalog and Product database models."""

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Catalog(Base):
    __tablename__ = "catalogs"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, xlsx, csv, docx
    original_filename = Column(String)
    product_count = Column(Integer, default=0)
    enabled = Column(String, default="true")  # stored as string for simplicity
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="catalog", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_uuid)
    catalog_id = Column(String, ForeignKey("catalogs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    price = Column(String, default="")  # string to handle currencies, ranges
    features = Column(JSON, default=list)  # list of strings
    tags = Column(JSON, default=list)  # list of strings for categorization
    image_url = Column(String, default="")  # public URL to product image
    image_local_path = Column(String, default="")  # local path for serving
    sku = Column(String, default="")
    extra_data = Column(JSON, default=dict)  # any additional fields from catalog
    created_at = Column(DateTime, default=datetime.utcnow)

    catalog = relationship("Catalog", back_populates="products")
