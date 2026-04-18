"""Facebook Messenger webhook and auto-reply. Very similar to Instagram webhook."""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from app.services.csat_sender import is_csat_response
from app.models.csat import CSATResponse

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

            # Check if this is a CSAT rating response
            csat_rating = is_csat_response(text)
            if csat_rating > 0:
                try:
                    from app.core.database import async_session
                    from sqlalchemy import select
                    from app.models.conversation_state import ConversationState

                    async with async_session() as session:
                        conv_result = await session.execute(
                            select(ConversationState).where(ConversationState.sender_id == sender_id)
                        )
                        conv = conv_result.scalar_one_or_none()
                        conv_id = conv.id if conv else ""
                        csat = CSATResponse(
                            conversation_id=conv_id,
                            sender_id=sender_id,
                            channel="messenger",
                            rating=csat_rating,
                        )
                        session.add(csat)
                        await session.commit()
                    thank_msg = "Thank you for your feedback! 🙏" if csat_rating >= 4 else "Thank you for your feedback. We'll work to improve! 🙏"
                    await send_messenger_reply(sender_id, thank_msg)
                    if csat_rating <= 2:
                        try:
                            from app.services.ai_learning import trigger_learning_on_negative_signal
                            import asyncio
                            asyncio.create_task(trigger_learning_on_negative_signal(sender_id, "low_csat", "messenger"))
                        except Exception:
                            pass
                    return {"status": "ok"}
                except Exception as e:
                    print(f"CSAT save error: {e}")

            # Check for negative signals and trigger learning
            negative_keywords = ["not interested", "no thanks", "too expensive", "stop", "unsubscribe", "terrible", "worst", "never again", "waste of time", "horrible service"]
            if any(kw in text.lower() for kw in negative_keywords):
                try:
                    from app.services.ai_learning import trigger_learning_on_negative_signal
                    import asyncio
                    asyncio.create_task(trigger_learning_on_negative_signal(sender_id, "negative_reaction", "messenger"))
                except Exception:
                    pass

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

            # Auto-assign
            try:
                from app.services.assignment import auto_assign_conversation
                await auto_assign_conversation(sender_id)
            except Exception as e:
                print(f"Auto-assign error: {e}")

            # Check response mode
            response_mode = "ai_auto"
            try:
                from app.core.database import async_session as asess
                from app.models.conversation_state import ConversationState as CS
                from sqlalchemy import select as sel3
                async with asess() as sess:
                    conv_result = await sess.execute(sel3(CS).where(CS.sender_id == sender_id))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state:
                        response_mode = conv_state.response_mode or "ai_auto"
            except Exception:
                pass

            if response_mode == "human_only":
                print(f"Human-only mode for {sender_id}, skipping AI reply")
                await save_messenger_conversation(sender_id, text, "", [])
                continue

            # Generate reply
            reply_text, product_images, recommend_ids, all_products = await get_messenger_reply(sender_id, text)

            # If ai_suggest mode, save as pending
            if response_mode == "ai_suggest":
                try:
                    async with asess() as sess:
                        conv_result = await sess.execute(sel3(CS).where(CS.sender_id == sender_id))
                        conv_state = conv_result.scalar_one_or_none()
                        if conv_state:
                            conv_state.pending_reply = reply_text
                            conv_state.pending_product_ids = [p for p in product_images]
                            await sess.commit()
                    print(f"AI Suggest mode: saved pending reply for {sender_id}")
                    await save_messenger_conversation(sender_id, text, "", [])
                    continue
                except Exception as e:
                    print(f"Pending save error: {e}")

            # Send text reply
            await send_messenger_reply(sender_id, reply_text)

            # Send product images
            for img_url in product_images[:3]:
                await send_messenger_image(sender_id, img_url)

            # Auto-trigger try-on for first recommended product
            if recommend_ids and all_products:
                first_product = next((p for p in all_products if p["id"] == recommend_ids[0]), None)
                if first_product and first_product.get("image_url"):
                    import asyncio
                    asyncio.create_task(_handle_tryon_async_messenger(sender_id, first_product))

            # Save to conversation state
            await save_messenger_conversation(sender_id, text, reply_text, product_images)

            # Auto-escalation
            try:
                async with asess() as sess:
                    conv_result = await sess.execute(sel3(CS).where(CS.sender_id == sender_id))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state and conv_state.intent_score >= 80 and conv_state.response_mode == "ai_auto":
                        conv_state.response_mode = "ai_suggest"
                        conv_state.escalated = True
                        conv_state.escalation_reason = f"Intent score reached {conv_state.intent_score}"
                        await sess.commit()
            except Exception as e:
                print(f"Escalation error: {e}")

            # Auto-trigger HappyRobot call for very high intent
            try:
                async with asess() as sess:
                    from app.models.customer import Customer
                    conv_result = await sess.execute(sel3(CS).where(CS.sender_id == sender_id))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state and conv_state.intent_score >= 90:
                        cust_result = await sess.execute(
                            select(Customer).where(Customer.messenger_sender_id == sender_id)
                        )
                        customer = cust_result.scalar_one_or_none()
                        if customer and customer.phone and not conv_state.escalation_reason.startswith("call_triggered"):
                            from app.services.happyrobot_service import trigger_outbound_call
                            import asyncio
                            asyncio.create_task(
                                trigger_outbound_call(
                                    phone_number=customer.phone,
                                    customer_name=customer.display_name or "",
                                    context=f"High intent customer (score: {conv_state.intent_score}). Stage: {conv_state.stage}. They have been chatting about products and showing strong buying signals.",
                                )
                            )
                            conv_state.escalation_reason = f"call_triggered_score_{conv_state.intent_score}"
                            await sess.commit()
                            print(f"HappyRobot call triggered for {sender_id}, score {conv_state.intent_score}")
            except Exception as e:
                print(f"HappyRobot auto-call error: {e}")

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

    # Load quick reply templates
    quick_replies_text = ""
    try:
        from app.core.database import async_session
        from app.models.quick_reply import QuickReply
        from sqlalchemy import select as sel2
        async with async_session() as session:
            qr_result = await session.execute(sel2(QuickReply))
            qr_list = qr_result.scalars().all()
            if qr_list:
                quick_replies_text = "\n\n## PREDEFINED Q&A\nBelow are predefined question-answer pairs. When the customer asks about any of these topics, use the provided answer as your source of truth. IMPORTANT: The answers below may be written in a different language than the customer is using. You MUST translate the answer into the customer's language while keeping the exact same meaning and information. Do NOT change the facts — only translate.\n\n"
                for qr in qr_list:
                    quick_replies_text += f"QUESTION: {qr.title}\nANSWER: {qr.content}\n\n"
    except Exception as e:
        print(f"Quick replies load error: {e}")

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

    # Self-learning: inject lessons from past conversations
    try:
        from app.services.ai_learning import get_lessons_for_prompt
        lessons_text = await get_lessons_for_prompt()
    except Exception:
        lessons_text = ""

    full_prompt = system_prompt + products_text + scoring_context + call_offer_text + quick_replies_text + lessons_text

    # Call LLM
    try:
        last_user_text = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_text = m.get("content", "")
                break
        language_override = {"role": "system", "content": f"OVERRIDE: The customer wrote: '{last_user_text}'. You MUST reply in the same language as this text. If this is English, your entire reply must be in English. If Turkish, reply in Turkish. NO EXCEPTIONS."}
        messages = [{"role": "system", "content": full_prompt}, language_override] + history[-20:]
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
                async with asess() as sess:
                    cust_result = await sess.execute(
                        select(Customer).where(Customer.messenger_sender_id == sender_id)
                    )
                    customer = cust_result.scalar_one_or_none()
                    if customer:
                        customer.phone = call_number
                        await sess.commit()

                recent_msgs = conversation_history.get(sender_id, [])[-5:]
                context = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in recent_msgs])
                asyncio.create_task(_handle_happyrobot_call_messenger(sender_id, call_number, context))
            except Exception as e:
                print(f"Call trigger error: {e}")

        for pid in recommend_ids[:3]:
            prod = next((p for p in products if p["id"] == pid), None)
            if prod and prod.get("image_url"):
                product_images.append(prod["image_url"])

        history.append({"role": "assistant", "content": reply_text})
        return reply_text, product_images, recommend_ids, products

    except Exception as e:
        print(f"LLM Error: {e}")
        return "Sorry, I'm having a technical issue. Please try again!", [], [], []


async def send_messenger_video(recipient_id: str, video_url: str):
    """Send a video via Messenger API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "video",
                            "payload": {"url": video_url, "is_reusable": True},
                        }
                    },
                },
            )
            print(f"Messenger Video [{resp.status_code}]: {video_url[:50]}")
    except Exception as e:
        print(f"Messenger video send error: {e}")


async def _handle_tryon_async_messenger(sender_id: str, product: dict):
    """Background task: generate try-on image + video and send to customer."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video

        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            await send_messenger_image(sender_id, model_result["image_url"])

            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                await send_messenger_video(sender_id, video_result["video_url"])
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")


async def _handle_happyrobot_call_messenger(sender_id: str, phone_number: str, context: str):
    """Background task: trigger HappyRobot outbound call for Messenger."""
    try:
        from app.services.happyrobot_service import trigger_outbound_call
        from app.core.database import async_session as asess
        from app.models.customer import Customer
        from sqlalchemy import select

        customer_name = ""
        async with asess() as sess:
            result = await sess.execute(
                select(Customer).where(Customer.messenger_sender_id == sender_id)
            )
            cust = result.scalar_one_or_none()
            if cust:
                customer_name = cust.display_name or ""

        import asyncio
        await asyncio.sleep(2)

        result = await trigger_outbound_call(
            phone_number=phone_number,
            customer_name=customer_name,
            context=f"Customer was chatting on Messenger and showed high buying intent. Recent conversation: {context}",
        )

        if result.get("success"):
            await send_messenger_reply(sender_id, "📞 We're connecting your call now! Please pick up in a moment.")
            print(f"HappyRobot call initiated: {result.get('call_id')}")
        else:
            await send_messenger_reply(sender_id, "Sorry, we couldn't connect the call right now. Can we try again in a few minutes?")
            print(f"HappyRobot call failed: {result.get('error')}")

    except Exception as e:
        print(f"HappyRobot call error: {e}")


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
