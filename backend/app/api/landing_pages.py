"""Landing page creator API."""

import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.landing_page import LandingPage
from app.models.models import Persona
from app.services.landing_page_generator import generate_landing_page, refine_landing_page

router = APIRouter()


@router.post("/landing-pages/generate")
async def generate_page(body: dict, db: AsyncSession = Depends(get_db)):
    """Generate a new landing page with AI."""
    persona_id = body.get("persona_id", "")

    # Load persona info
    persona_dict = {}
    if persona_id:
        result = await db.execute(select(Persona).where(Persona.id == persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            persona_dict = {
                "company_name": persona.company_name or "",
                "description": persona.description or "",
                "expertise_areas": persona.expertise_areas or [],
            }

    result = await generate_landing_page(
        customer_name=body.get("customer_name", ""),
        customer_company=body.get("customer_company", ""),
        customer_industry=body.get("customer_industry", ""),
        customer_description=body.get("customer_description", ""),
        persona_company=persona_dict.get("company_name", ""),
        persona_description=persona_dict.get("description", ""),
        persona_services=persona_dict.get("expertise_areas", []),
        style=body.get("style", "modern"),
        color_scheme=body.get("color_scheme", "auto"),
        language=body.get("language", "en"),
        additional_instructions=body.get("additional_instructions", ""),
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    # Save to database
    page = LandingPage(
        name=f"Landing Page for {body.get('customer_company', 'Customer')}",
        customer_name=body.get("customer_name", ""),
        customer_company=body.get("customer_company", ""),
        html_content=result["html"],
        style=body.get("style", "modern"),
        color_scheme=body.get("color_scheme", "auto"),
        language=body.get("language", "en"),
        status="draft",
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)

    return {
        "id": page.id,
        "html": result["html"],
        "name": page.name,
    }


@router.post("/landing-pages/{page_id}/refine")
async def refine_page(page_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Refine an existing landing page with AI based on feedback."""
    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)

    instruction = body.get("instruction", "")
    if not instruction:
        raise HTTPException(status_code=400, detail="Instruction required")

    refine_result = await refine_landing_page(page.html_content, instruction)

    if not refine_result["success"]:
        raise HTTPException(status_code=500, detail=refine_result["error"])

    page.html_content = refine_result["html"]
    page.updated_at = datetime.utcnow()
    await db.commit()

    return {"id": page.id, "html": refine_result["html"]}


@router.get("/landing-pages/")
async def list_pages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LandingPage).order_by(desc(LandingPage.created_at)))
    pages = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "customer_name": p.customer_name,
            "customer_company": p.customer_company,
            "style": p.style,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in pages
    ]


@router.get("/landing-pages/{page_id}")
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)
    return {
        "id": page.id,
        "name": page.name,
        "customer_name": page.customer_name,
        "customer_company": page.customer_company,
        "html_content": page.html_content,
        "style": page.style,
        "color_scheme": page.color_scheme,
        "language": page.language,
        "status": page.status,
        "created_at": page.created_at.isoformat() if page.created_at else None,
    }


@router.get("/landing-pages/{page_id}/preview")
async def preview_page(page_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the landing page HTML for preview."""
    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)
    return HTMLResponse(content=page.html_content)


@router.delete("/landing-pages/{page_id}")
async def delete_page(page_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)
    await db.delete(page)
    await db.commit()
    return {"status": "deleted"}


@router.patch("/landing-pages/{page_id}")
async def update_page(page_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)
    for field in ("name", "status", "html_content"):
        if field in body:
            setattr(page, field, body[field])
    page.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "updated"}


@router.post("/landing-pages/{page_id}/deploy")
async def deploy_page(page_id: str, db: AsyncSession = Depends(get_db)):
    """Deploy a landing page to Netlify and return the live URL."""
    from app.services.netlify_deploy import deploy_landing_page

    result = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404)

    site_name = page.customer_company.lower().replace(" ", "-") if page.customer_company else "landing-page"
    deploy_result = await deploy_landing_page(page.html_content, site_name)

    if deploy_result["success"]:
        page.status = "published"
        page.updated_at = datetime.utcnow()
        await db.commit()

    return deploy_result


@router.post("/landing-pages/auto-generate-for-lead")
async def auto_generate_for_lead(body: dict, db: AsyncSession = Depends(get_db)):
    """Auto-generate a landing page based on lead company info."""
    lead = body.get("lead", {})
    persona_id = body.get("persona_id", "")

    # Load persona
    persona_dict = {}
    if persona_id:
        result = await db.execute(select(Persona).where(Persona.id == persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            persona_dict = {
                "company_name": persona.company_name or "",
                "description": persona.description or "",
                "expertise_areas": persona.expertise_areas or [],
            }

    # Build description from lead info
    company_name = lead.get("company_name", "")
    customer_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    title = lead.get("title", lead.get("headline", ""))
    industry = lead.get("company_industry", "")
    location = lead.get("location", lead.get("city", ""))
    company_size = lead.get("company_size", "")
    ai_reason = lead.get("ai_reason", "")

    description = f"{company_name} is a company"
    if industry:
        description += f" in the {industry} industry"
    if location:
        description += f" based in {location}"
    if company_size:
        description += f" with approximately {company_size} employees"
    if title and customer_name:
        description += f". {customer_name} is their {title}"
    if ai_reason:
        description += f". Key insight: {ai_reason}"

    result = await generate_landing_page(
        customer_name=customer_name,
        customer_company=company_name,
        customer_industry=industry or "Technology",
        customer_description=description,
        persona_company=persona_dict.get("company_name", ""),
        persona_description=persona_dict.get("description", ""),
        persona_services=persona_dict.get("expertise_areas", []),
        style="modern",
        color_scheme="light",
        language="en",
        additional_instructions=f"This is a landing page for {company_name}. Make it bright, modern, with light colors and creative design. The company works in {industry or 'technology'}. Make it look premium and professional. Use gradients, smooth animations, and a clean layout. The landing page should showcase what {company_name} does and attract their potential customers.",
    )

    if not result["success"]:
        return {"success": False, "error": result["error"]}

    # Save to database
    page = LandingPage(
        name=f"Landing Page for {company_name}",
        customer_name=customer_name,
        customer_company=company_name,
        html_content=result["html"],
        style="modern",
        color_scheme="light",
        language="en",
        status="draft",
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)

    # Auto-deploy to Netlify
    deploy_url = ""
    try:
        from app.services.netlify_deploy import deploy_landing_page
        site_name = (company_name or "landing").lower().replace(" ", "-").replace(".", "-")
        deploy_result = await deploy_landing_page(result["html"], site_name)
        if deploy_result["success"]:
            deploy_url = deploy_result["url"]
            page.status = "published"
            await db.commit()
    except Exception as e:
        print(f"Auto-deploy error: {e}")

    return {
        "success": True,
        "id": page.id,
        "html": result["html"],
        "name": page.name,
        "company": company_name,
        "deploy_url": deploy_url,
    }
