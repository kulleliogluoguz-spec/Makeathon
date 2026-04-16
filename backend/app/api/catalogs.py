"""Catalog upload and management API."""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.catalog_models import Catalog, Product
from app.services.catalog_parser import parse_catalog_file

load_dotenv()

router = APIRouter()

UPLOAD_DIR = Path("media/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_base_url(request: Request) -> str:
    """Return the public base URL for serving media. Uses ngrok URL if configured."""
    base = os.getenv("PUBLIC_BASE_URL", "").strip()
    if base:
        return base
    # Fallback: use request's URL (works for localhost)
    return f"{request.url.scheme}://{request.url.netloc}"


@router.post("/catalogs/upload")
async def upload_catalog(
    request: Request,
    file: UploadFile = File(...),
    persona_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a catalog file. Returns parsed products."""

    # Save file
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "pdf"
    if ext not in ("pdf", "xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Parse
    base_url = get_base_url(request)
    try:
        products_data = await parse_catalog_file(str(file_path), ext, base_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    # Create catalog
    catalog = Catalog(
        persona_id=persona_id,
        filename=filename,
        original_filename=file.filename,
        file_type=ext,
        product_count=len(products_data),
        enabled="true",
    )
    db.add(catalog)
    await db.flush()

    # Create products
    for p in products_data:
        product = Product(
            catalog_id=catalog.id,
            name=p.get("name", "")[:500],
            description=p.get("description", "")[:5000],
            price=str(p.get("price", ""))[:100],
            features=p.get("features", []),
            tags=p.get("tags", []),
            sku=p.get("sku", "")[:100],
            image_url=p.get("image_url", ""),
            image_local_path=p.get("image_local_path", ""),
            extra_data={},
        )
        db.add(product)

    await db.commit()
    await db.refresh(catalog)

    return {
        "catalog_id": catalog.id,
        "filename": catalog.original_filename,
        "product_count": catalog.product_count,
        "products": products_data[:10],  # preview first 10
    }


@router.get("/catalogs/")
async def list_catalogs(persona_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List all catalogs, optionally filtered by persona."""
    query = select(Catalog)
    if persona_id:
        query = query.where(Catalog.persona_id == persona_id)
    result = await db.execute(query)
    catalogs = result.scalars().all()
    return [
        {
            "id": c.id,
            "persona_id": c.persona_id,
            "original_filename": c.original_filename,
            "file_type": c.file_type,
            "product_count": c.product_count,
            "enabled": c.enabled == "true",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in catalogs
    ]


@router.get("/catalogs/{catalog_id}/products")
async def get_catalog_products(catalog_id: str, db: AsyncSession = Depends(get_db)):
    """Get all products in a catalog."""
    result = await db.execute(select(Product).where(Product.catalog_id == catalog_id))
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "features": p.features,
            "tags": p.tags,
            "image_url": p.image_url,
            "sku": p.sku,
        }
        for p in products
    ]


@router.delete("/catalogs/{catalog_id}")
async def delete_catalog(catalog_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a catalog and its products."""
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(status_code=404)
    await db.delete(catalog)
    await db.commit()
    return {"status": "deleted"}


@router.patch("/catalogs/{catalog_id}")
async def update_catalog(catalog_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Enable/disable a catalog or reassign to another persona."""
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(status_code=404)
    if "enabled" in body:
        catalog.enabled = "true" if body["enabled"] else "false"
    if "persona_id" in body:
        catalog.persona_id = body["persona_id"]
    await db.commit()
    return {"status": "updated"}
