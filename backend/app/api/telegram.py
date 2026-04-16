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

    await upsert_telegram_customer(chat_id, sender_name)
    reply_text, product_images = await get_telegram_reply(chat_id, text)
    await send_telegram_message(chat_id, reply_text)
    for img_url in product_images[:3]:
        await send_telegram_image(chat_id, img_url)
    await save_telegram_conversation(chat_id, text, reply_text)
    return {"status": "ok"}


async def get_telegram_reply(chat_id: str, user_message: str):
    product_images = []

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    history = conversation_history[chat_id]
    history.append({"role": "user", "content": user_message})
    if len(history) > 20:
        conversation_history[chat_id] = history[-20:]
        history = conversation_history[chat_id]

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
                quick_replies_text = "\n\n## PREDEFINED Q&A\nBelow are predefined question-answer pairs. When the customer asks about any of these topics, use the provided answer as your source of truth. IMPORTANT: The answers below may be written in a different language than the customer is using. You MUST translate the answer into the customer's language while keeping the exact same meaning and information. Do NOT change the facts — only translate.\n\n"
                for qr in qr_list:
                    quick_replies_text += f"QUESTION: {qr.title}\nANSWER: {qr.content}\n\n"
    except Exception:
        pass

    full_prompt = system_prompt + products_text + scoring_context + quick_replies_text

    try:
        last_user_text = user_message
        language_override = {"role": "system", "content": f"OVERRIDE: The customer wrote: '{last_user_text}'. You MUST reply in the same language as this text. If this is English, your entire reply must be in English. If Turkish, reply in Turkish. NO EXCEPTIONS."}
        messages = [{"role": "system", "content": full_prompt}, language_override] + history
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
