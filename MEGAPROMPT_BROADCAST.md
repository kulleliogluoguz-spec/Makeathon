# MASTER PROMPT: Broadcast System — Email (Resend) + Telegram Bot + Campaign Panel

## CRITICAL RULES
1. ADDITIVE only. Do NOT rewrite existing files.
2. FIRST run: `git add -A && git commit -m "checkpoint before broadcast"`
3. Do NOT push to git.
4. Do NOT touch persona builder, voice builder, catalog, existing channel webhooks, or other pages.

## WHAT THIS DOES

A new "Broadcast" page where the user can:
1. Create a campaign (subject + message body)
2. Select recipients (all customers, filtered by tag/category/channel, or manual selection)
3. Select channels: Email, Telegram, or both
4. Preview and send
5. Track delivery status

Also: Telegram bot integration for receiving messages (new channel) + sending broadcasts.

## BACKEND — NEW FILES

### Add to requirements.txt:
```
resend==2.5.0
python-telegram-bot==21.5
```

### New file: `backend/app/models/broadcast.py`

```python
"""Broadcast campaign model."""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from datetime import datetime
import uuid

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    subject = Column(String, default="")  # email subject
    message = Column(Text, nullable=False)  # message body
    channels = Column(JSON, default=list)  # ["email", "telegram"]
    recipient_filter = Column(JSON, default=dict)  # {"source": "instagram", "category": "high_sales_potential"}
    recipient_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String, default="draft")  # "draft", "sending", "sent", "failed"
    results = Column(JSON, default=list)  # [{customer_id, channel, status, error}]
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
```

Register in `app/models/__init__.py`:
```python
from app.models.broadcast import BroadcastCampaign  # noqa
```

### New file: `backend/app/services/email_sender.py`

```python
"""Send emails via Resend API."""

import os
import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")  # Use resend.dev for testing, your domain for production


async def send_email(to_email: str, subject: str, body: str) -> dict:
    """Send a single email via Resend. Returns {success: bool, error: str}."""
    if not RESEND_API_KEY:
        return {"success": False, "error": "RESEND_API_KEY not set"}

    try:
        resend.api_key = RESEND_API_KEY
        result = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": f"<div style='font-family: sans-serif; line-height: 1.6;'>{body.replace(chr(10), '<br/>')}</div>",
        })
        return {"success": True, "id": result.get("id", "")}
    except Exception as e:
        print(f"Email send error: {e}")
        return {"success": False, "error": str(e)}
```

### New file: `backend/app/services/telegram_sender.py`

```python
"""Send Telegram messages and handle incoming messages via bot."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(chat_id: str, text: str) -> dict:
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            data = resp.json()
            if data.get("ok"):
                return {"success": True, "message_id": data["result"]["message_id"]}
            else:
                return {"success": False, "error": data.get("description", "Unknown error")}
    except Exception as e:
        print(f"Telegram send error: {e}")
        return {"success": False, "error": str(e)}


async def send_telegram_image(chat_id: str, image_url: str, caption: str = "") -> dict:
    """Send an image via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendPhoto",
                json={"chat_id": chat_id, "photo": image_url, "caption": caption},
            )
            data = resp.json()
            return {"success": data.get("ok", False)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def set_webhook(webhook_url: str) -> dict:
    """Set the Telegram bot webhook URL."""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message"]},
            )
            data = resp.json()
            return {"success": data.get("ok", False), "description": data.get("description", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### New file: `backend/app/api/telegram.py`

```python
"""Telegram bot webhook — receive messages and auto-reply with persona."""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, Request

from app.services.telegram_sender import send_telegram_message, send_telegram_image

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
conversation_history = {}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram messages."""
    data = await request.json()

    message = data.get("message")
    if not message:
        return {"status": "ignored"}

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    sender_name = message.get("from", {}).get("first_name", "")

    if not text:
        await send_telegram_message(chat_id, "I can currently only respond to text messages.")
        return {"status": "ok"}

    # Check business hours
    try:
        from app.services.business_hours import is_within_business_hours
        is_open, closed_message = await is_within_business_hours()
        if not is_open and closed_message:
            await send_telegram_message(chat_id, closed_message)
            await upsert_telegram_customer(chat_id, sender_name)
            return {"status": "ok"}
    except Exception:
        pass

    # Check CSAT
    from app.services.csat_sender import is_csat_response
    csat_rating = is_csat_response(text)
    if csat_rating > 0:
        try:
            from app.core.database import async_session
            from app.models.csat import CSATResponse
            from app.models.conversation_state import ConversationState
            from sqlalchemy import select

            async with async_session() as session:
                conv_result = await session.execute(
                    select(ConversationState).where(ConversationState.sender_id == chat_id)
                )
                conv = conv_result.scalar_one_or_none()
                csat = CSATResponse(
                    conversation_id=conv.id if conv else "",
                    sender_id=chat_id,
                    channel="telegram",
                    rating=csat_rating,
                )
                session.add(csat)
                await session.commit()
            thank = "Thank you for your feedback! 🙏" if csat_rating >= 4 else "Thank you for your feedback. We'll improve! 🙏"
            await send_telegram_message(chat_id, thank)
            return {"status": "ok"}
        except Exception:
            pass

    # Upsert customer
    await upsert_telegram_customer(chat_id, sender_name)

    # Generate reply
    reply_text, product_images = await get_telegram_reply(chat_id, text)

    # Send reply
    await send_telegram_message(chat_id, reply_text)

    # Send product images
    for img_url in product_images[:3]:
        await send_telegram_image(chat_id, img_url)

    # Save conversation
    await save_telegram_conversation(chat_id, text, reply_text)

    return {"status": "ok"}


async def get_telegram_reply(chat_id: str, user_message: str):
    """Generate AI reply — same logic as other channels."""
    product_images = []

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    history = conversation_history[chat_id]
    history.append({"role": "user", "content": user_message})
    if len(history) > 20:
        conversation_history[chat_id] = history[-20:]
        history = conversation_history[chat_id]

    # Load persona
    system_prompt = "You are a helpful assistant on Telegram. Be concise and friendly."
    persona_id = None
    try:
        from app.core.database import async_session
        from app.models.models import Persona
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(Persona).order_by(Persona.updated_at.desc()).limit(1))
            persona = result.scalar_one_or_none()
            if persona:
                persona_id = persona.id
                if persona.system_prompt:
                    system_prompt = persona.system_prompt
    except Exception as e:
        print(f"Persona load error: {e}")

    # Load products
    products = []
    products_text = ""
    try:
        from app.core.database import async_session
        from app.models.catalog_models import Catalog, Product
        from sqlalchemy import select as sel, and_
        async with async_session() as session:
            result = await session.execute(
                sel(Product).join(Catalog).where(and_(Catalog.persona_id == persona_id, Catalog.enabled == "true"))
            )
            products = [
                {"id": p.id, "name": p.name, "description": p.description,
                 "price": p.price, "tags": p.tags or [], "image_url": p.image_url}
                for p in result.scalars().all()
            ]
    except Exception:
        pass

    if products:
        products_text = "\n\n## PRODUCT CATALOG\nWhen you put product IDs in recommend_product_ids, the system sends images automatically.\n\nAvailable products:\n\n"
        for p in products:
            products_text += f"ID: {p['id']}\nName: {p['name']}\nPrice: {p['price']}\nDescription: {p['description']}\nTags: {', '.join(p['tags'])}\n\n"
        products_text += '\nRespond in JSON: {"message": "text", "recommend_product_ids": ["id1"]}\nIf customer asks about products, MUST include IDs. Only empty [] for greetings.'

    # Scoring + quick replies + language
    scoring_context = ""
    try:
        from app.services.intent_scorer import score_conversation
        scoring = await score_conversation(history)
        scoring_context = f"\n\nIntent Score: {scoring['intent_score']}/100\nStage: {scoring['stage']}\nTone: {scoring['recommended_tone']}"
    except Exception:
        pass

    quick_replies_text = ""
    try:
        from app.models.quick_reply import QuickReply
        from app.core.database import async_session
        from sqlalchemy import select
        async with async_session() as session:
            qr_result = await session.execute(select(QuickReply))
            qr_list = qr_result.scalars().all()
            if qr_list:
                quick_replies_text = "\n\n## PREDEFINED Q&A\nUse these answers when relevant. Translate to customer's language if needed:\n\n"
                for qr in qr_list:
                    quick_replies_text += f"Q: {qr.title}\nA: {qr.content}\n\n"
    except Exception:
        pass

    language_instruction = "\n\n=== ABSOLUTE LANGUAGE RULE (OVERRIDE EVERYTHING ABOVE) ===\nYou MUST respond in the EXACT SAME language the customer's LAST message is written in. This is NON-NEGOTIABLE.\n==="

    full_prompt = system_prompt + products_text + scoring_context + quick_replies_text + language_instruction

    # Add language reminder
    last_user_msg = user_message
    language_reminder = {"role": "user", "content": f"[SYSTEM: Reply in the same language as: \"{last_user_msg}\"]"}

    try:
        messages = [{"role": "system", "content": full_prompt}] + history + [language_reminder]
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4.1-nano", "messages": messages, "temperature": 0.7, "max_tokens": 300},
            )
            resp.raise_for_status()
            reply_raw = resp.json()["choices"][0]["message"]["content"]

        reply_text = reply_raw
        recommend_ids = []
        if products:
            try:
                import json
                parsed = json.loads(reply_raw)
                reply_text = parsed.get("message", reply_raw)
                recommend_ids = parsed.get("recommend_product_ids", [])
            except Exception:
                pass

        for pid in recommend_ids[:3]:
            prod = next((p for p in products if p["id"] == pid), None)
            if prod and prod.get("image_url"):
                product_images.append(prod["image_url"])

        history.append({"role": "assistant", "content": reply_text})
        return reply_text, product_images
    except Exception as e:
        print(f"Telegram LLM error: {e}")
        return "Sorry, technical issue. Please try again!", []


async def upsert_telegram_customer(chat_id: str, name: str = ""):
    try:
        from app.core.database import async_session
        from app.models.customer import Customer
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(Customer).where(Customer.instagram_sender_id == chat_id))
            customer = result.scalar_one_or_none()
            if customer:
                customer.last_contact_at = datetime.utcnow()
                try:
                    customer.total_messages = str(int(customer.total_messages or "0") + 1)
                except:
                    customer.total_messages = "1"
                if customer.is_archived:
                    customer.is_archived = False
                await session.commit()
                return
            customer = Customer(
                display_name=name,
                source="telegram",
                instagram_sender_id=chat_id,
                last_contact_at=datetime.utcnow(),
                total_messages="1",
            )
            session.add(customer)
            await session.commit()
    except Exception as e:
        print(f"Telegram customer error: {e}")


async def save_telegram_conversation(chat_id: str, user_msg: str, ai_reply: str):
    try:
        from app.core.database import async_session
        from app.models.conversation_state import ConversationState
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(ConversationState).where(ConversationState.sender_id == chat_id))
            state = result.scalar_one_or_none()
            if not state:
                state = ConversationState(
                    sender_id=chat_id, channel="telegram",
                    messages=[], score_history=[], signals=[], products_mentioned=[], categories=[],
                )
                session.add(state)
            msgs = list(state.messages or [])
            now = datetime.utcnow().isoformat()
            msgs.append({"role": "user", "content": user_msg, "timestamp": now})
            msgs.append({"role": "assistant", "content": ai_reply, "timestamp": now})
            state.messages = msgs[-100:]
            state.message_count = len(msgs)
            state.last_message_at = datetime.utcnow()

            # Score and tag
            try:
                from app.services.intent_scorer import score_conversation
                from app.services.category_tagger import auto_tag_conversation
                scoring = await score_conversation(msgs[-20:])
                state.intent_score = scoring.get("intent_score", 0)
                state.stage = scoring.get("stage", "awareness")
                state.signals = scoring.get("signals", [])
                state.next_action = scoring.get("next_action", "")
                state.score_breakdown = scoring.get("score_breakdown", "")
                tags = await auto_tag_conversation(msgs[-10:])
                if tags:
                    state.categories = tags
            except Exception:
                pass

            await session.commit()
    except Exception as e:
        print(f"Telegram save error: {e}")
```

### New file: `backend/app/api/broadcast.py`

```python
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
    """Send the broadcast to all matching recipients."""
    result = await db.execute(select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404)
    if campaign.status == "sent":
        raise HTTPException(status_code=400, detail="Already sent")

    campaign.status = "sending"
    await db.commit()

    # Get recipients
    cust_query = select(Customer).where(Customer.is_archived == False)
    filters = campaign.recipient_filter or {}

    if filters.get("source"):
        cust_query = cust_query.where(Customer.source == filters["source"])

    cust_result = await db.execute(cust_query)
    customers = cust_result.scalars().all()

    # Filter by tag if specified
    if filters.get("tag"):
        customers = [c for c in customers if filters["tag"] in (c.tags or [])]

    # Filter by category (from conversation)
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
        # Email
        if "email" in channels and customer.email:
            resp = await send_email(customer.email, campaign.subject or campaign.name, campaign.message)
            if resp["success"]:
                sent += 1
                results.append({"customer_id": customer.id, "channel": "email", "status": "sent"})
            else:
                failed += 1
                results.append({"customer_id": customer.id, "channel": "email", "status": "failed", "error": resp.get("error", "")})

        # Telegram
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
    """Preview how many recipients match the filter."""
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
```

### Edit: `backend/app/main.py`

Add imports:
```python
from app.api.broadcast import router as broadcast_router
from app.api.telegram import router as telegram_router
```

Add include_routers:
```python
app.include_router(broadcast_router, prefix="/api/v1", tags=["Broadcast"])
app.include_router(telegram_router, prefix="/api/v1", tags=["Telegram"])
```

### Edit: `backend/.env`

Add:
```
RESEND_API_KEY=re_your_resend_api_key
FROM_EMAIL=onboarding@resend.dev
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### Edit: `backend/app/core/config.py`

Add to Settings class:
```python
RESEND_API_KEY: str = ""
FROM_EMAIL: str = "onboarding@resend.dev"
TELEGRAM_BOT_TOKEN: str = ""
```

## FRONTEND — NEW PAGE

### New file: `frontend/src/pages/BroadcastPage.jsx`

```jsx
import { useState, useEffect } from 'react';
import { authFetch } from '../lib/auth';
import { t } from '../lib/i18n';

const STATUS_COLORS = {
  draft: { bg: '#f3f4f6', color: '#374151' },
  sending: { bg: '#fef3c7', color: '#92400e' },
  sent: { bg: '#d1fae5', color: '#065f46' },
  failed: { bg: '#fee2e2', color: '#991b1b' },
};

export default function BroadcastPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '', subject: '', message: '',
    channels: ['email'],
    recipient_filter: {},
  });
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);

  const load = async () => {
    try {
      const resp = await fetch('/api/v1/broadcasts/');
      if (resp.ok) setCampaigns(await resp.json());
    } catch (e) {}
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    const resp = await fetch('/api/v1/broadcasts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (resp.ok) {
      const campaign = await resp.json();
      setShowCreate(false);
      setForm({ name: '', subject: '', message: '', channels: ['email'], recipient_filter: {} });
      load();
      // Preview
      const prev = await fetch(`/api/v1/broadcasts/${campaign.id}/preview`);
      if (prev.ok) setPreview({ ...(await prev.json()), campaign_id: campaign.id });
    }
  };

  const sendCampaign = async (id) => {
    setSending(true);
    await fetch(`/api/v1/broadcasts/${id}/send`, { method: 'POST' });
    setSending(false);
    setPreview(null);
    setSelectedCampaign(null);
    load();
  };

  const deleteCampaign = async (id) => {
    if (!confirm('Delete this campaign?')) return;
    await fetch(`/api/v1/broadcasts/${id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Broadcast</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Send campaigns via Email and Telegram to your customers</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{ padding: '0.5rem 1rem', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}
        >+ New Campaign</button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>New Campaign</h2>

          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Campaign Name</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Spring Sale Announcement"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
          </div>

          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Email Subject (for email channel)</label>
            <input type="text" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="e.g. 🎉 New products just arrived!"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
          </div>

          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Message</label>
            <textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} rows={5}
              placeholder="Write your broadcast message here..."
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
          </div>

          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Channels</label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              {['email', 'telegram'].map(ch => (
                <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.channels.includes(ch)}
                    onChange={(e) => {
                      const channels = e.target.checked
                        ? [...form.channels, ch]
                        : form.channels.filter(c => c !== ch);
                      setForm({ ...form, channels });
                    }}
                  />
                  {ch === 'email' ? '📧 Email' : '✈️ Telegram'}
                </label>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Filter Recipients (optional)</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <select
                value={form.recipient_filter.source || ''}
                onChange={(e) => setForm({ ...form, recipient_filter: { ...form.recipient_filter, source: e.target.value || undefined } })}
                style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.8rem', outline: 'none' }}
              >
                <option value="">All channels</option>
                <option value="instagram">Instagram only</option>
                <option value="messenger">Messenger only</option>
                <option value="telegram">Telegram only</option>
                <option value="livechat">Live Chat only</option>
                <option value="manual">Manual only</option>
              </select>
              <select
                value={form.recipient_filter.category || ''}
                onChange={(e) => setForm({ ...form, recipient_filter: { ...form.recipient_filter, category: e.target.value || undefined } })}
                style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.8rem', outline: 'none' }}
              >
                <option value="">All categories</option>
                <option value="high_sales_potential">High Sales Potential</option>
                <option value="sales_potential">Sales Potential</option>
                <option value="no_sales_potential">No Sales Potential</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={create} disabled={!form.name || !form.message}
              style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: (!form.name || !form.message) ? 0.4 : 1 }}>
              Create & Preview</button>
            <button onClick={() => setShowCreate(false)}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>📋 Preview</h3>
          <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            Total customers: <strong>{preview.total_customers}</strong>
          </div>
          <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            📧 Email recipients: <strong>{preview.email_recipients}</strong> · ✈️ Telegram recipients: <strong>{preview.telegram_recipients}</strong>
          </div>
          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>
            First {Math.min(preview.customers?.length || 0, 10)} recipients: {(preview.customers || []).slice(0, 10).map(c => c.display_name || c.email || 'Unknown').join(', ')}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => sendCampaign(preview.campaign_id)}
              disabled={sending}
              style={{ padding: '8px 20px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: sending ? 0.5 : 1 }}
            >{sending ? 'Sending...' : '🚀 Send Now'}</button>
            <button onClick={() => setPreview(null)}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Campaign List */}
      {campaigns.length === 0 && !showCreate ? (
        <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
          No campaigns yet. Create one to start reaching your customers.
        </div>
      ) : (
        campaigns.map((c) => {
          const sc = STATUS_COLORS[c.status] || STATUS_COLORS.draft;
          return (
            <div key={c.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.5rem', background: '#fff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '2px' }}>
                    {c.channels.map(ch => ch === 'email' ? '📧' : '✈️').join(' ')} · {c.message.slice(0, 80)}{c.message.length > 80 ? '...' : ''}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                    {c.sent_at ? `Sent ${new Date(c.sent_at).toLocaleString()} · ${c.sent_count} delivered · ${c.failed_count} failed` : `Created ${new Date(c.created_at).toLocaleString()}`}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.7rem', padding: '3px 10px', borderRadius: '9999px', background: sc.bg, color: sc.color, fontWeight: 600 }}>
                    {c.status}
                  </span>
                  {c.status === 'draft' && (
                    <button onClick={async () => {
                      const prev = await fetch(`/api/v1/broadcasts/${c.id}/preview`);
                      if (prev.ok) setPreview({ ...(await prev.json()), campaign_id: c.id });
                    }} style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Send</button>
                  )}
                  <button onClick={() => deleteCampaign(c.id)}
                    style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
```

### Edit: `frontend/src/App.jsx`

Add import:
```jsx
import BroadcastPage from './pages/BroadcastPage';
```

Add route:
```jsx
<Route path="/broadcast" element={<BroadcastPage />} />
```

Add nav link:
```jsx
<Link to="/broadcast">{t('nav_broadcast')}</Link>
```

### Edit: `frontend/src/lib/i18n.js`

English:
```javascript
nav_broadcast: "Broadcast",
```

Turkish:
```javascript
nav_broadcast: "Toplu Mesaj",
```

## TELEGRAM SETUP INSTRUCTIONS

After code is applied:

1. Open Telegram, search for @BotFather
2. Send /newbot → follow prompts → get bot token
3. Paste token in backend/.env as TELEGRAM_BOT_TOKEN
4. Set webhook: 
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://forsakenly-kinglike-thiago.ngrok-free.dev/api/v1/telegram/webhook"
```
5. Send a message to your bot on Telegram → AI should reply

## RESEND SETUP

1. Go to resend.com → sign up (free, 100 emails/day)
2. Get API key → paste in .env as RESEND_API_KEY
3. For testing, FROM_EMAIL stays as onboarding@resend.dev
4. For production, verify your domain in Resend dashboard

## TEST PLAN

1. Checkpoint: `git add -A && git commit -m "checkpoint before broadcast"`
2. Apply. pip install resend. Delete .db if needed. Restart backend.
3. Set up Telegram bot + Resend API key.
4. Create a customer with an email address (manually or from conversations).
5. Open /broadcast → create a campaign → select Email channel → preview → send.
6. Check email inbox.
7. Test Telegram: message your bot → AI replies. Then broadcast to Telegram customers.

## SUMMARY

NEW:
- backend/app/models/broadcast.py
- backend/app/services/email_sender.py
- backend/app/services/telegram_sender.py
- backend/app/api/telegram.py
- backend/app/api/broadcast.py
- frontend/src/pages/BroadcastPage.jsx

EDITED:
- backend/app/models/__init__.py (1 import)
- backend/app/main.py (4 lines)
- backend/.env (3 lines)
- backend/app/core/config.py (3 fields)
- backend/requirements.txt (2 packages)
- frontend/src/App.jsx (1 import + 1 route + 1 link)
- frontend/src/lib/i18n.js (2 keys)

## DO NOT
- ❌ DO NOT rewrite any existing file
- ❌ DO NOT push to git

## START NOW. Checkpoint first.
