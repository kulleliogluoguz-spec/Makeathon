"""Unipile LinkedIn + HappyRobot API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.services.unipile_service import (
    search_linkedin_people,
    get_linkedin_profile,
    send_linkedin_invite,
    send_linkedin_message,
)
from app.services.happyrobot_service import trigger_outbound_call, get_call_status

router = APIRouter()


# ---- LinkedIn via Unipile ----

@router.post("/linkedin/search")
async def linkedin_search(body: dict):
    """Search LinkedIn for people."""
    results = await search_linkedin_people(
        keywords=body.get("keywords", ""),
        location=body.get("location", []),
        industry=body.get("industry", []),
        limit=body.get("limit", 10),
    )
    return results


@router.get("/linkedin/profile/{identifier}")
async def linkedin_profile(identifier: str):
    """Get a LinkedIn profile."""
    return await get_linkedin_profile(identifier)


@router.post("/linkedin/invite")
async def linkedin_invite(body: dict):
    """Send a LinkedIn connection request."""
    provider_id = body.get("provider_id", "")
    message = body.get("message", "")
    if not provider_id:
        raise HTTPException(status_code=400, detail="provider_id required")
    return await send_linkedin_invite(provider_id, message)


@router.post("/linkedin/message")
async def linkedin_message(body: dict):
    """Send a LinkedIn message to a connection."""
    provider_id = body.get("provider_id", "")
    text = body.get("text", "")
    if not provider_id or not text:
        raise HTTPException(status_code=400, detail="provider_id and text required")
    return await send_linkedin_message(provider_id, text)


# ---- HappyRobot ----

@router.post("/happyrobot/call")
async def trigger_call(body: dict):
    """Trigger an outbound AI phone call."""
    phone = body.get("phone_number", "")
    if not phone:
        raise HTTPException(status_code=400, detail="phone_number required")
    return await trigger_outbound_call(
        phone_number=phone,
        customer_name=body.get("customer_name", ""),
        context=body.get("context", ""),
        language=body.get("language", "en-US"),
    )


@router.get("/happyrobot/call/{call_id}")
async def call_status(call_id: str):
    """Get call status and transcript."""
    return await get_call_status(call_id)
