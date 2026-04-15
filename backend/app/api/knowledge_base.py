"""Knowledge base CRUD API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import KnowledgeEntry
from app.schemas.schemas import KnowledgeEntryCreate, KnowledgeEntryUpdate, KnowledgeEntryResponse

router = APIRouter()


@router.get("/", response_model=List[KnowledgeEntryResponse])
async def list_entries(
    agent_id: str = None,
    category: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeEntry)
    if agent_id:
        query = query.where(KnowledgeEntry.agent_id == agent_id)
    if category:
        query = query.where(KnowledgeEntry.category == category)
    query = query.order_by(KnowledgeEntry.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.post("/", response_model=KnowledgeEntryResponse, status_code=201)
async def create_entry(data: KnowledgeEntryCreate, db: AsyncSession = Depends(get_db)):
    entry = KnowledgeEntry(**data.model_dump())
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_entry(entry_id: str, data: KnowledgeEntryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    await db.delete(entry)


@router.post("/search")
async def search_knowledge(
    query: str,
    agent_id: str = None,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """Simple keyword search. Replace with vector search for production."""
    stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
    if agent_id:
        stmt = stmt.where(KnowledgeEntry.agent_id == agent_id)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    # Simple keyword matching (replace with embedding similarity in production)
    query_lower = query.lower()
    scored = []
    for entry in entries:
        score = 0
        for word in query_lower.split():
            if word in entry.title.lower():
                score += 2
            if word in entry.content.lower():
                score += 1
            for tag in entry.tags:
                if word in tag.lower():
                    score += 1
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "entry": KnowledgeEntryResponse.model_validate(e)} for s, e in scored[:limit]]
