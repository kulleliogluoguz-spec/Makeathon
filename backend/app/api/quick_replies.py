"""Quick reply templates CRUD API."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.quick_reply import QuickReply

router = APIRouter()


@router.get("/quick-replies/")
async def list_quick_replies(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(QuickReply).order_by(desc(QuickReply.use_count))
    result = await db.execute(query)
    replies = result.scalars().all()

    if category:
        replies = [r for r in replies if r.category == category]
    if search:
        s = search.lower()
        replies = [r for r in replies if s in r.title.lower() or s in r.content.lower() or s in (r.keywords or "").lower()]

    return [_serialize(r) for r in replies]


@router.post("/quick-replies/")
async def create_quick_reply(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("title") or not body.get("content"):
        raise HTTPException(status_code=400, detail="Title and content are required")

    reply = QuickReply(
        title=body["title"],
        content=body["content"],
        category=body.get("category", ""),
        keywords=body.get("keywords", ""),
        persona_id=body.get("persona_id", ""),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return _serialize(reply)


@router.patch("/quick-replies/{reply_id}")
async def update_quick_reply(reply_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)

    for field in ("title", "content", "category", "keywords", "persona_id"):
        if field in body:
            setattr(reply, field, body[field])
    reply.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(reply)
    return _serialize(reply)


@router.delete("/quick-replies/{reply_id}")
async def delete_quick_reply(reply_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)
    await db.delete(reply)
    await db.commit()
    return {"status": "deleted"}


@router.post("/quick-replies/{reply_id}/use")
async def increment_use_count(reply_id: str, db: AsyncSession = Depends(get_db)):
    """Increment use count when a template is used."""
    result = await db.execute(select(QuickReply).where(QuickReply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404)
    reply.use_count = (reply.use_count or 0) + 1
    await db.commit()
    return {"status": "ok", "use_count": reply.use_count}


@router.get("/quick-replies/match")
async def match_quick_reply(q: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Find the best matching quick reply for a customer message."""
    result = await db.execute(select(QuickReply))
    replies = result.scalars().all()

    q_lower = q.lower()
    matches = []
    for r in replies:
        score = 0
        keywords = [k.strip().lower() for k in (r.keywords or "").split(",") if k.strip()]
        for kw in keywords:
            if kw in q_lower:
                score += 10
        if r.title.lower() in q_lower:
            score += 5
        if score > 0:
            matches.append({"reply": _serialize(r), "score": score})

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {"matches": matches[:3]}


def _serialize(r: QuickReply) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "content": r.content,
        "category": r.category or "",
        "keywords": r.keywords or "",
        "use_count": r.use_count or 0,
        "persona_id": r.persona_id or "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
