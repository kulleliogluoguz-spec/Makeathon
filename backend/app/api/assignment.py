"""Conversation assignment API."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation_state import ConversationState
from app.models.user import User

router = APIRouter()


@router.post("/conversations/{conv_id}/assign")
async def assign_conversation(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Assign conversation to a user."""
    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    agent_id = body.get("agent_id", "")

    if agent_id:
        agent_result = await db.execute(select(User).where(User.id == agent_id))
        if not agent_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Agent not found")

    conv.assigned_to = agent_id
    conv.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "assigned", "assigned_to": agent_id}


@router.post("/conversations/{conv_id}/set-mode")
async def set_response_mode(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Set conversation response mode: ai_auto, ai_suggest, human_only."""
    mode = body.get("mode", "")
    if mode not in ("ai_auto", "ai_suggest", "human_only"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    conv.response_mode = mode
    conv.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "mode_set", "mode": mode}


@router.post("/conversations/{conv_id}/approve-reply")
async def approve_reply(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Approve or edit the AI's pending reply (ai_suggest mode). Then send it."""
    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    final_text = body.get("text", conv.pending_reply or "")
    if not final_text:
        raise HTTPException(status_code=400, detail="No reply text")

    sender_id = conv.sender_id
    channel = conv.channel

    if channel == "instagram":
        from app.api.instagram import send_reply
        await send_reply(sender_id, final_text)
    elif channel == "messenger":
        from app.api.messenger import send_messenger_reply
        await send_messenger_reply(sender_id, final_text)

    product_ids = body.get("product_ids", conv.pending_product_ids or [])
    if product_ids:
        try:
            from app.core.database import async_session as asess
            from app.models.catalog_models import Product
            async with asess() as session:
                for pid in product_ids[:3]:
                    prod_result = await session.execute(select(Product).where(Product.id == pid))
                    prod = prod_result.scalar_one_or_none()
                    if prod and prod.image_url:
                        if channel == "instagram":
                            from app.api.instagram import send_instagram_image
                            await send_instagram_image(sender_id, prod.image_url)
                        elif channel == "messenger":
                            from app.api.messenger import send_messenger_image
                            await send_messenger_image(sender_id, prod.image_url)
        except Exception as e:
            print(f"Image send error: {e}")

    msgs = list(conv.messages or [])
    msgs.append({"role": "assistant", "content": final_text, "timestamp": datetime.utcnow().isoformat(), "sent_by": "human"})
    conv.messages = msgs
    conv.pending_reply = ""
    conv.pending_product_ids = []
    conv.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "sent"}


@router.post("/conversations/{conv_id}/send-manual")
async def send_manual_reply(conv_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Send a manual reply (human_only mode)."""
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    result = await db.execute(select(ConversationState).where(ConversationState.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    sender_id = conv.sender_id
    channel = conv.channel

    if channel == "instagram":
        from app.api.instagram import send_reply
        await send_reply(sender_id, text)
    elif channel == "messenger":
        from app.api.messenger import send_messenger_reply
        await send_messenger_reply(sender_id, text)

    msgs = list(conv.messages or [])
    msgs.append({"role": "assistant", "content": text, "timestamp": datetime.utcnow().isoformat(), "sent_by": "human"})
    conv.messages = msgs
    conv.message_count = len(msgs)
    conv.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "sent"}
