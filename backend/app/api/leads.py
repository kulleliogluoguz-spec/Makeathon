"""Lead generation API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.lead import SavedLead
from app.models.models import Persona
from app.services.lead_generator import (
    generate_icp_from_persona,
    search_leads_with_ai,
    ai_score_leads,
    generate_outreach_message,
)

router = APIRouter()


@router.post("/leads/generate-icp")
async def generate_icp(body: dict = {}, db: AsyncSession = Depends(get_db)):
    """Generate ICP from persona. Optionally pass persona_id."""
    persona_id = body.get("persona_id", "")

    # Load persona
    if persona_id:
        result = await db.execute(select(Persona).where(Persona.id == persona_id))
    else:
        result = await db.execute(select(Persona).order_by(Persona.updated_at.desc()).limit(1))
    persona = result.scalar_one_or_none()

    if not persona:
        raise HTTPException(status_code=404, detail="No persona found")

    persona_dict = {
        "company_name": persona.company_name or "",
        "role_title": persona.role_title or "",
        "description": persona.description or "",
        "expertise_areas": persona.expertise_areas or [],
        "background_story": persona.background_story or "",
        "display_name": persona.display_name or "",
    }

    icp = await generate_icp_from_persona(persona_dict)
    return {"icp": icp, "persona_id": persona.id}


@router.post("/leads/search")
async def search_leads(body: dict, db: AsyncSession = Depends(get_db)):
    """Search web for leads matching ICP criteria, then AI-score them."""
    icp = body.get("icp", {})
    persona_id = body.get("persona_id", "")
    page = body.get("page", 1)

    # Search via AI web search
    results = await search_leads_with_ai(icp=icp, page=page, per_page=10)

    if results.get("error"):
        raise HTTPException(status_code=400, detail=results["error"])

    # Load persona for AI scoring
    persona_dict = {}
    if persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == persona_id))
        persona = p_result.scalar_one_or_none()
        if persona:
            persona_dict = {
                "company_name": persona.company_name or "",
                "description": persona.description or "",
                "display_name": persona.display_name or "",
            }

    # AI score the leads
    people = results.get("people", [])
    if people:
        people = await ai_score_leads(people, persona_dict, icp)

    return {
        "total": results.get("total", 0),
        "page": page,
        "leads": people,
    }


@router.post("/leads/save")
async def save_lead(body: dict, db: AsyncSession = Depends(get_db)):
    """Save a lead to the database."""
    # Check if already saved
    existing = await db.execute(
        select(SavedLead).where(SavedLead.apollo_id == body.get("apollo_id", ""))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Lead already saved")

    lead = SavedLead(
        apollo_id=body.get("apollo_id", ""),
        first_name=body.get("first_name", ""),
        last_name=body.get("last_name", ""),
        title=body.get("title", ""),
        company_name=body.get("company_name", ""),
        company_industry=body.get("company_industry", ""),
        company_size=str(body.get("company_size", "")),
        company_revenue=body.get("company_revenue", ""),
        company_website=body.get("company_website", ""),
        linkedin_url=body.get("linkedin_url", ""),
        city=body.get("city", ""),
        country=body.get("country", ""),
        ai_score=body.get("ai_score", 0),
        ai_reason=body.get("ai_reason", ""),
        ai_approach=body.get("ai_approach", ""),
        persona_id=body.get("persona_id", ""),
        status="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return _serialize_lead(lead)


@router.get("/leads/saved")
async def list_saved_leads(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all saved leads."""
    query = select(SavedLead).order_by(desc(SavedLead.ai_score))
    if status:
        query = query.where(SavedLead.status == status)
    result = await db.execute(query)
    leads = result.scalars().all()
    return [_serialize_lead(l) for l in leads]


@router.patch("/leads/saved/{lead_id}")
async def update_saved_lead(lead_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Update a saved lead's status or notes."""
    result = await db.execute(select(SavedLead).where(SavedLead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404)
    for field in ("status", "notes", "outreach_message"):
        if field in body:
            setattr(lead, field, body[field])
    lead.updated_at = datetime.utcnow()
    await db.commit()
    return _serialize_lead(lead)


@router.delete("/leads/saved/{lead_id}")
async def delete_saved_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedLead).where(SavedLead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404)
    await db.delete(lead)
    await db.commit()
    return {"status": "deleted"}


@router.post("/leads/outreach-message")
async def gen_outreach(body: dict, db: AsyncSession = Depends(get_db)):
    """Generate personalized outreach message for a lead."""
    lead = body.get("lead", {})
    icp = body.get("icp", {})
    channel = body.get("channel", "email")
    persona_id = body.get("persona_id", "")

    persona_dict = {}
    if persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == persona_id))
        persona = p_result.scalar_one_or_none()
        if persona:
            persona_dict = {
                "company_name": persona.company_name or "",
                "description": persona.description or "",
                "display_name": persona.display_name or "",
            }

    message = await generate_outreach_message(lead, persona_dict, icp, channel)
    return {"message": message}


def _serialize_lead(l: SavedLead) -> dict:
    return {
        "id": l.id,
        "apollo_id": l.apollo_id,
        "first_name": l.first_name,
        "last_name": l.last_name,
        "title": l.title,
        "company_name": l.company_name,
        "company_industry": l.company_industry,
        "company_size": l.company_size,
        "company_revenue": l.company_revenue,
        "company_website": l.company_website,
        "linkedin_url": l.linkedin_url,
        "city": l.city,
        "country": l.country,
        "ai_score": l.ai_score,
        "ai_reason": l.ai_reason,
        "ai_approach": l.ai_approach,
        "status": l.status,
        "notes": l.notes or "",
        "outreach_message": l.outreach_message or "",
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
