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
    reply_text, product_images, recommend_ids, all_products = await get_telegram_reply(chat_id, text)
    await send_telegram_message(chat_id, reply_text)
    for img_url in product_images[:3]:
        await send_telegram_image(chat_id, img_url)

    # Auto-trigger try-on for first recommended product
    if recommend_ids and all_products:
        first_product = next((p for p in all_products if p["id"] == recommend_ids[0]), None)
        if first_product and first_product.get("image_url"):
            import asyncio
            asyncio.create_task(_handle_tryon_async_telegram(chat_id, first_product))

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

    # Add phone call offer instruction for high intent
    call_offer_text = ""
    if scoring_context:
        try:
            score = scoring.get("intent_score", 0)
            if score >= 70:
                call_offer_text = """

## PHONE CALL OFFER
The customer's intent score is high (70+). They are very interested in buying. You should naturally offer them a phone call to help complete their purchase. Here's how:

1. FIRST, naturally mention: "If you'd like, we can call you right now to help you with your purchase — it'll only take a minute!"
2. If they say yes, ask: "Would you like us to call you, or would you prefer our number so you can call us?"
3. If they want YOU to call THEM, say: "Great! Just share your phone number and we'll call you right away! 📞"
4. When the customer provides a phone number, respond with EXACTLY this JSON format:
   {"message": "Perfect! We're calling you right now! 📞", "recommend_product_ids": [], "trigger_call": true, "call_number": "+XXXXXXXXXXX"}
   Replace +XXXXXXXXXXX with the actual phone number they provided. Make sure to include country code.
5. IMPORTANT: Only set trigger_call to true when the customer has EXPLICITLY provided their phone number.
6. Do NOT offer to call if you already offered in this conversation.
"""
        except Exception:
            pass

    full_prompt = system_prompt + products_text + scoring_context + call_offer_text + quick_replies_text

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

        # Detect phone call trigger
        trigger_call = False
        call_number = ""
        if products:
            try:
                if isinstance(parsed, dict):
                    trigger_call = parsed.get("trigger_call", False)
                    call_number = parsed.get("call_number", "")
            except Exception:
                pass

        if trigger_call and call_number:
            import asyncio
            try:
                from app.models.customer import Customer
                from app.core.database import async_session as asess2
                async with asess2() as sess:
                    cust_result = await sess.execute(
                        select(Customer).where(Customer.telegram_sender_id == str(chat_id))
                    )
                    customer = cust_result.scalar_one_or_none()
                    if customer:
                        customer.phone = call_number
                        await sess.commit()

                recent_msgs = conversation_history.get(str(chat_id), [])[-5:]
                context = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in recent_msgs])
                asyncio.create_task(_handle_happyrobot_call_telegram(chat_id, call_number, context))
            except Exception as e:
                print(f"Call trigger error: {e}")

        for pid in recommend_ids[:3]:
            prod = next((p for p in products if p["id"] == pid), None)
            if prod and prod.get("image_url"):
                product_images.append(prod["image_url"])

        history.append({"role": "assistant", "content": reply_text})
        return reply_text, product_images, recommend_ids, products
    except Exception as e:
        print(f"Telegram LLM error: {e}")
        return "Sorry, technical issue. Please try again!", [], [], []


async def _handle_tryon_async_telegram(chat_id: str, product: dict):
    """Background task: generate try-on image + video and send to customer."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video
        from app.services.telegram_sender import send_telegram_video

        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            await send_telegram_image(chat_id, model_result["image_url"])

            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                await send_telegram_video(chat_id, video_result["video_url"], f"{product['name']} - Fashion Video")
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")


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

            # Auto-trigger HappyRobot call for very high intent
            try:
                if state.intent_score >= 90:
                    from app.models.customer import Customer
                    cust_result = await session.execute(
                        select(Customer).where(Customer.telegram_sender_id == str(chat_id))
                    )
                    customer = cust_result.scalar_one_or_none()
                    if customer and customer.phone and not (state.escalation_reason or "").startswith("call_triggered"):
                        from app.services.happyrobot_service import trigger_outbound_call
                        import asyncio
                        asyncio.create_task(
                            trigger_outbound_call(
                                phone_number=customer.phone,
                                customer_name=customer.display_name or "",
                                context=f"High intent customer (score: {state.intent_score}). Stage: {state.stage}. They have been chatting about products and showing strong buying signals.",
                            )
                        )
                        state.escalation_reason = f"call_triggered_score_{state.intent_score}"
                        print(f"HappyRobot call triggered for telegram {chat_id}, score {state.intent_score}")
            except Exception as e:
                print(f"HappyRobot auto-call error: {e}")

            await session.commit()
    except Exception as e:
        print(f"Telegram save error: {e}")


async def _handle_happyrobot_call_telegram(chat_id: int, phone_number: str, context: str):
    """Background task: trigger HappyRobot outbound call for Telegram."""
    try:
        from app.services.happyrobot_service import trigger_outbound_call
        from app.core.database import async_session as asess
        from app.models.customer import Customer
        from sqlalchemy import select

        customer_name = ""
        async with asess() as sess:
            result = await sess.execute(
                select(Customer).where(Customer.telegram_sender_id == str(chat_id))
            )
            cust = result.scalar_one_or_none()
            if cust:
                customer_name = cust.display_name or ""

        import asyncio
        await asyncio.sleep(2)

        result = await trigger_outbound_call(
            phone_number=phone_number,
            customer_name=customer_name,
            context=f"Customer was chatting on Telegram and showed high buying intent. Recent conversation: {context}",
        )

        if result.get("success"):
            await send_telegram_message(chat_id, "📞 We're connecting your call now! Please pick up in a moment.")
            print(f"HappyRobot call initiated: {result.get('call_id')}")
        else:
            await send_telegram_message(chat_id, "Sorry, we couldn't connect the call right now. Can we try again in a few minutes?")
            print(f"HappyRobot call failed: {result.get('error')}")

    except Exception as e:
        print(f"HappyRobot call error: {e}")
