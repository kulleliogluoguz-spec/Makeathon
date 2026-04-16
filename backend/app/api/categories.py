"""Category management API."""

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.category import Category

router = APIRouter()


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")
    return slug


@router.get("/categories/")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.is_builtin.desc(), Category.name))
    cats = result.scalars().all()
    return [_serialize(c) for c in cats]


@router.post("/categories/")
async def create_category(body: dict, db: AsyncSession = Depends(get_db)):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    slug = slugify(body.get("slug") or name)
    result = await db.execute(select(Category).where(Category.slug == slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Slug already exists: {slug}")

    category = Category(
        slug=slug,
        name=name,
        description=body.get("description", ""),
        color=body.get("color", "#64748b"),
        is_builtin=False,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return _serialize(category)


@router.patch("/categories/{category_id}")
async def update_category(category_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.is_builtin:
        for field in ("description", "color"):
            if field in body:
                setattr(category, field, body[field])
    else:
        for field in ("name", "description", "color"):
            if field in body:
                setattr(category, field, body[field])

    category.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(category)
    return _serialize(category)


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in categories")
    await db.delete(category)
    await db.commit()
    return {"status": "deleted"}


def _serialize(c: Category) -> dict:
    return {
        "id": c.id,
        "slug": c.slug,
        "name": c.name,
        "description": c.description or "",
        "color": c.color or "#64748b",
        "is_builtin": c.is_builtin,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
