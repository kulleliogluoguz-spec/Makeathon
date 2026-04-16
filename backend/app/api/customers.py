"""Customer CRM API."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc

from app.core.database import get_db
from app.models.customer import Customer

router = APIRouter()


@router.get("/customers/")
async def list_customers(
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    archived: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List customers. Supports search by name/handle/email/phone, filter by tag, filter by source."""
    query = select(Customer)

    # Archive filter
    if archived == "true":
        query = query.where(Customer.is_archived == True)
    elif archived == "all":
        pass
    else:
        query = query.where(Customer.is_archived == False)

    if search:
        terms = search.strip().split()
        for word in terms:
            w = f"%{word.lower()}%"
            query = query.where(
                or_(
                    Customer.display_name.ilike(w),
                    Customer.handle.ilike(w),
                    Customer.email.ilike(w),
                    Customer.phone.ilike(w),
                    Customer.whatsapp_phone.ilike(w),
                )
            )

    if source:
        query = query.where(Customer.source == source)

    query = query.order_by(desc(Customer.updated_at))
    result = await db.execute(query)
    customers = result.scalars().all()

    # Filter by tag (post-query, since tags are JSON)
    if tag:
        customers = [c for c in customers if tag in (c.tags or [])]

    # Filter by conversation category
    if category:
        from app.models.conversation_state import ConversationState
        conv_result = await db.execute(select(ConversationState))
        all_convs = conv_result.scalars().all()
        matching_ids = set()
        for conv in all_convs:
            if category in (conv.categories or []):
                if conv.sender_id:
                    matching_ids.add(conv.sender_id)
        customers = [
            c for c in customers
            if c.instagram_sender_id in matching_ids or c.whatsapp_phone in matching_ids
        ]

    return [_serialize(c) for c in customers]


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize(customer)


@router.post("/customers/")
async def create_customer(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a customer manually."""
    customer = Customer(
        display_name=body.get("display_name", ""),
        handle=body.get("handle", ""),
        email=body.get("email", ""),
        phone=body.get("phone", ""),
        avatar_url=body.get("avatar_url", ""),
        tags=body.get("tags", []),
        custom_fields=body.get("custom_fields", {}),
        notes=body.get("notes", ""),
        source=body.get("source", "manual"),
        instagram_sender_id=body.get("instagram_sender_id", ""),
        whatsapp_phone=body.get("whatsapp_phone", ""),
        external_ids=body.get("external_ids", {}),
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return _serialize(customer)


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field in (
        "display_name", "handle", "email", "phone", "avatar_url",
        "tags", "custom_fields", "notes", "source",
        "instagram_sender_id", "whatsapp_phone", "external_ids",
    ):
        if field in body:
            setattr(customer, field, body[field])

    customer.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(customer)
    return _serialize(customer)


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.delete(customer)
    await db.commit()
    return {"status": "deleted"}


@router.get("/customers/{customer_id}/conversations")
async def get_customer_conversations(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Get all conversations linked to this customer (by matching external IDs)."""
    from app.models.conversation_state import ConversationState

    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Find conversations matching any of the customer's external IDs
    conv_query = select(ConversationState)
    match_ids = []
    if customer.instagram_sender_id:
        match_ids.append(customer.instagram_sender_id)
    if customer.whatsapp_phone:
        match_ids.append(customer.whatsapp_phone)

    if not match_ids:
        return []

    conv_query = conv_query.where(ConversationState.sender_id.in_(match_ids))
    result = await db.execute(conv_query.order_by(desc(ConversationState.last_message_at)))
    conversations = result.scalars().all()

    return [
        {
            "id": c.id,
            "sender_id": c.sender_id,
            "channel": c.channel,
            "intent_score": c.intent_score,
            "stage": c.stage,
            "signals": c.signals or [],
            "message_count": c.message_count,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        }
        for c in conversations
    ]


def _serialize(c: Customer) -> dict:
    return {
        "id": c.id,
        "display_name": c.display_name,
        "handle": c.handle,
        "email": c.email,
        "phone": c.phone,
        "avatar_url": c.avatar_url,
        "tags": c.tags or [],
        "custom_fields": c.custom_fields or {},
        "notes": c.notes or "",
        "source": c.source,
        "instagram_sender_id": c.instagram_sender_id,
        "whatsapp_phone": c.whatsapp_phone,
        "external_ids": c.external_ids or {},
        "last_contact_at": c.last_contact_at.isoformat() if c.last_contact_at else None,
        "total_messages": c.total_messages,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "is_archived": c.is_archived or False,
    }


@router.post("/customers/{customer_id}/archive")
async def archive_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404)
    customer.is_archived = True
    customer.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "archived"}


@router.post("/customers/{customer_id}/unarchive")
async def unarchive_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404)
    customer.is_archived = False
    customer.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "unarchived"}
