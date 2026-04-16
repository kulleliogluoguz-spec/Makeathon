"""Broadcast campaign API — create, send, track campaigns."""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.broadcast import BroadcastCampaign
from app.models.customer import Customer
from app.services.email_sender import send_email
from app.services.telegram_sender import send_telegram_message

router = APIRouter()


@router.get("/broadcasts/")
async def list_broadcasts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BroadcastCampaign).order_by(desc(BroadcastCampaign.created_at)))
    campaigns = result.scalars().all()
    return [_serialize(c) for c in campaigns]


@router.post("/broadcasts/")
async def create_broadcast(body: dict, db: AsyncSession = Depends(get_db)):
    campaign = BroadcastCampaign(
        name=body.get("name", "Untitled Campaign"),
        subject=body.get("subject", ""),
        message=body.get("message", ""),
        channels=body.get("channels", []),
        recipient_filter=body.get("recipient_filter", {}),
        status="draft",
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _serialize(campaign)


@router.get("/broadcasts/{campaign_id}")
async def get_broadcast(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404)
    return _serialize(campaign)


@router.post("/broadcasts/{campaign_id}/send")
async def send_broadcast(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404)
    if campaign.status == "sent":
        raise HTTPException(status_code=400, detail="Already sent")

    campaign.status = "sending"
    await db.commit()

    cust_query = select(Customer).where(Customer.is_archived == False)
    filters = campaign.recipient_filter or {}

    if filters.get("source"):
        cust_query = cust_query.where(Customer.source == filters["source"])

    cust_result = await db.execute(cust_query)
    customers = cust_result.scalars().all()

    if filters.get("tag"):
        customers = [c for c in customers if filters["tag"] in (c.tags or [])]

    if filters.get("category"):
        from app.models.conversation_state import ConversationState
        conv_result = await db.execute(select(ConversationState))
        all_convs = conv_result.scalars().all()
        matching_senders = {c.sender_id for c in all_convs if filters["category"] in (c.categories or [])}
        customers = [c for c in customers if c.instagram_sender_id in matching_senders]

    channels = campaign.channels or []
    results = []
    sent = 0
    failed = 0

    for customer in customers:
        if "email" in channels and customer.email:
            resp = await send_email(customer.email, campaign.subject or campaign.name, campaign.message)
            if resp["success"]:
                sent += 1
                results.append({"customer_id": customer.id, "channel": "email", "status": "sent"})
            else:
                failed += 1
                results.append({"customer_id": customer.id, "channel": "email", "status": "failed", "error": resp.get("error", "")})

        if "telegram" in channels and customer.source == "telegram" and customer.instagram_sender_id:
            resp = await send_telegram_message(customer.instagram_sender_id, campaign.message)
            if resp["success"]:
                sent += 1
                results.append({"customer_id": customer.id, "channel": "telegram", "status": "sent"})
            else:
                failed += 1
                results.append({"customer_id": customer.id, "channel": "telegram", "status": "failed", "error": resp.get("error", "")})

    campaign.recipient_count = len(customers)
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.results = results
    campaign.status = "sent"
    campaign.sent_at = datetime.utcnow()
    await db.commit()
    await db.refresh(campaign)

    return _serialize(campaign)


@router.get("/broadcasts/{campaign_id}/preview")
async def preview_recipients(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404)

    cust_query = select(Customer).where(Customer.is_archived == False)
    filters = campaign.recipient_filter or {}
    if filters.get("source"):
        cust_query = cust_query.where(Customer.source == filters["source"])
    cust_result = await db.execute(cust_query)
    customers = cust_result.scalars().all()

    if filters.get("tag"):
        customers = [c for c in customers if filters["tag"] in (c.tags or [])]

    channels = campaign.channels or []
    email_count = sum(1 for c in customers if "email" in channels and c.email)
    telegram_count = sum(1 for c in customers if "telegram" in channels and c.source == "telegram")

    return {
        "total_customers": len(customers),
        "email_recipients": email_count,
        "telegram_recipients": telegram_count,
        "customers": [
            {"id": c.id, "display_name": c.display_name, "email": c.email or "", "source": c.source}
            for c in customers[:50]
        ],
    }


@router.delete("/broadcasts/{campaign_id}")
async def delete_broadcast(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404)
    await db.delete(campaign)
    await db.commit()
    return {"status": "deleted"}


def _serialize(c: BroadcastCampaign) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "subject": c.subject or "",
        "message": c.message,
        "channels": c.channels or [],
        "recipient_filter": c.recipient_filter or {},
        "recipient_count": c.recipient_count or 0,
        "sent_count": c.sent_count or 0,
        "failed_count": c.failed_count or 0,
        "status": c.status,
        "results": c.results or [],
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
    }
