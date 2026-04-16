"""Facebook Messenger webhook and auto-reply. Very similar to Instagram webhook."""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse

load_dotenv()

router = APIRouter()

VERIFY_TOKEN = os.getenv("MESSENGER_VERIFY_TOKEN", "bigm_verify_123")
PAGE_ACCESS_TOKEN = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# In-memory conversation history per sender
conversation_history = {}


@router.get("/messenger/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403)


@router.post("/messenger/webhook")
async def handle_webhook(request: Request):
    data = await request.json()

    if data.get("object") != "page":
        return {"status": "ignored"}

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" not in event:
                continue
            msg = event["message"]
            if msg.get("is_echo"):
                continue

            sender_id = event["sender"]["id"]
            text = msg.get("text", "")

            if not text:
                await send_messenger_reply(sender_id, "I can currently only respond to text messages. Please type your question!")
                continue

            # Check business hours
            try:
                from app.services.business_hours import is_within_business_hours
                is_open, closed_message = await is_within_business_hours()
                if not is_open and closed_message:
                    await send_messenger_reply(sender_id, closed_message)
                    await upsert_messenger_customer(sender_id)
                    return {"status": "ok"}
            except Exception as e:
                print(f"Business hours check error: {e}")

            # Upsert customer
            await upsert_messenger_customer(sender_id)

            # Generate reply
            reply_text, product_images = await get_messenger_reply(sender_id, text)

            # Send text reply
            await send_messenger_reply(sender_id, reply_text)

            # Send product images
            for img_url in product_images[:3]:
                await send_messenger_image(sender_id, img_url)

            # Save to conversation state
            await save_messenger_conversation(sender_id, text, reply_text, product_images)

    return {"status": "ok"}


async def get_messenger_reply(sender_id: str, user_message: str):
    """Generate AI reply — same logic as Instagram."""
    product_images = []

    if sender_id not in conversation_history:
        conversation_history[sender_id] = []
    history = conversation_history[sender_id]
    history.append({"role": "user", "content": user_message})
    if len(history) > 20:
        conversation_history[sender_id] = history[-20:]
        history = conversation_history[sender_id]

    # Load persona
    system_prompt = "You are a helpful assistant on Facebook Messenger. Be concise and friendly."
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
                sel(Product).join(Catalog).where(
                    and_(Catalog.persona_id == persona_id, Catalog.enabled == "true")
                )
            )
            products = [
                {"id": p.id, "name": p.name, "description": p.description,
                 "price": p.price, "tags": p.tags or [], "image_url": p.image_url}
                for p in result.scalars().all()
            ]
    except Exception as e:
        print(f"Product load error: {e}")

    if products:
        products_text = "\n\n## PRODUCT CATALOG\nYou have a product catalog. When you put product IDs in recommend_product_ids, the system will AUTOMATICALLY send the product images to the customer.\n\nAvailable products:\n\n"
        for p in products:
            products_text += f"ID: {p['id']}\nName: {p['name']}\nPrice: {p['price']}\nDescription: {p['description']}\nTags: {', '.join(p['tags'])}\n\n"
        products_text += '\nYou MUST respond in this JSON format: {"message": "your reply text", "recommend_product_ids": ["id1", "id2"]}\nRULES:\n- If the customer asks about ANY product, you MUST include 1-3 matching product IDs.\n- NEVER say you cannot send images. The system sends them automatically.\n- Only use empty recommend_product_ids [] for pure greetings.'

    # Intent scoring context
    scoring_context = ""
    try:
        from app.services.intent_scorer import score_conversation
        scoring = await score_conversation(history)
        scoring_context = f"\n\n## CUSTOMER STATE\nIntent Score: {scoring['intent_score']}/100\nStage: {scoring['stage']}\nRecommended tone: {scoring['recommended_tone']}\nNext action: {scoring['next_action']}"
    except Exception as e:
        print(f"Scoring error: {e}")

    full_prompt = system_prompt + products_text + scoring_context

    # Call LLM
    try:
        messages = [{"role": "system", "content": full_prompt}] + history[-20:]
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
                parsed = json.loads(reply_raw)
                reply_text = parsed.get("message", reply_raw)
                recommend_ids = parsed.get("recommend_product_ids", [])
            except (json.JSONDecodeError, TypeError):
                reply_text = reply_raw

        for pid in recommend_ids[:3]:
            prod = next((p for p in products if p["id"] == pid), None)
            if prod and prod.get("image_url"):
                product_images.append(prod["image_url"])

        history.append({"role": "assistant", "content": reply_text})
        return reply_text, product_images

    except Exception as e:
        print(f"LLM Error: {e}")
        return "Sorry, I'm having a technical issue. Please try again!", []


async def send_messenger_reply(recipient_id: str, text: str):
    """Send text via Messenger Graph API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"Messenger Reply [{resp.status_code}]: {text[:50]}")
    except Exception as e:
        print(f"Messenger send error: {e}")


async def send_messenger_image(recipient_id: str, image_url: str):
    """Send image via Messenger Graph API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}", "Content-Type": "application/json"},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": image_url, "is_reusable": True},
                        }
                    },
                },
            )
            print(f"Messenger Image [{resp.status_code}]: {image_url}")
    except Exception as e:
        print(f"Messenger image error: {e}")


async def upsert_messenger_customer(sender_id: str):
    """Create or update customer from Messenger."""
    try:
        from app.core.database import async_session
        from app.models.customer import Customer
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.instagram_sender_id == sender_id)
            )
            customer = result.scalar_one_or_none()

            if customer:
                customer.last_contact_at = datetime.utcnow()
                customer.updated_at = datetime.utcnow()
                try:
                    msgs = int(customer.total_messages or "0") + 1
                except (ValueError, TypeError):
                    msgs = 1
                customer.total_messages = str(msgs)
                if customer.is_archived:
                    customer.is_archived = False
                await session.commit()
                return

            customer = Customer(
                display_name="",
                handle="",
                source="messenger",
                instagram_sender_id=sender_id,
                last_contact_at=datetime.utcnow(),
                total_messages="1",
            )
            session.add(customer)
            await session.commit()
    except Exception as e:
        print(f"Customer upsert error: {e}")


async def save_messenger_conversation(sender_id: str, user_msg: str, ai_reply: str, product_images: list):
    """Save to ConversationState with channel=messenger + scoring + tagging."""
    try:
        from app.core.database import async_session
        from app.models.conversation_state import ConversationState
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(ConversationState).where(ConversationState.sender_id == sender_id)
            )
            state = result.scalar_one_or_none()

            if not state:
                state = ConversationState(
                    sender_id=sender_id,
                    channel="messenger",
                    messages=[],
                    score_history=[],
                    signals=[],
                    products_mentioned=[],
                    categories=[],
                )
                session.add(state)

            msgs = list(state.messages or [])
            now = datetime.utcnow().isoformat()
            msgs.append({"role": "user", "content": user_msg, "timestamp": now})
            msgs.append({"role": "assistant", "content": ai_reply, "timestamp": now})
            state.messages = msgs[-100:]
            state.message_count = len(msgs)
            state.last_message_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()

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

                history = list(state.score_history or [])
                history.append({
                    "timestamp": now,
                    "intent_score": scoring.get("intent_score", 0),
                    "stage": scoring.get("stage", "awareness"),
                })
                state.score_history = history[-50:]

                tags = await auto_tag_conversation(msgs[-10:])
                if tags:
                    state.categories = tags
            except Exception as e:
                print(f"Scoring/tagging error: {e}")

            await session.commit()
    except Exception as e:
        print(f"Conversation save error: {e}")
