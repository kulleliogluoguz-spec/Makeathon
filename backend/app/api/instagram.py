from dotenv import load_dotenv
load_dotenv()
import os
import httpx
from datetime import datetime
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from app.services.intent_scorer import score_conversation
from app.services.category_tagger import auto_tag_conversation
from app.services.business_hours import is_within_business_hours
from app.core.database import async_session
from app.models.conversation_state import ConversationState
from app.models.customer import Customer
from app.services.csat_sender import is_csat_response
from app.models.csat import CSATResponse
from sqlalchemy import select

router = APIRouter()

VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "bigm_verify_123")
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

conversation_history = {}

@router.get("/instagram/webhook")
async def verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403)

@router.post("/instagram/webhook")
async def webhook(request: Request):
    data = await request.json()
    if data.get("object") != "instagram":
        return {"status": "ignored"}
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" not in event:
                continue
            msg = event["message"]
            if msg.get("is_echo"):
                continue
            sender = event["sender"]["id"]
            text = msg.get("text", "")
            if not text:
                continue
            # Create or update customer record
            profile_name = None
            try:
                profile_name = event.get("sender", {}).get("username") or event.get("sender", {}).get("name")
            except Exception:
                pass
            await upsert_customer_from_instagram(sender, profile_name)
            # Check if this is a CSAT rating response
            csat_rating = is_csat_response(text)
            if csat_rating > 0:
                try:
                    async with async_session() as session:
                        conv_result = await session.execute(
                            select(ConversationState).where(ConversationState.sender_id == sender)
                        )
                        conv = conv_result.scalar_one_or_none()
                        conv_id = conv.id if conv else ""
                        csat = CSATResponse(
                            conversation_id=conv_id,
                            sender_id=sender,
                            channel="instagram",
                            rating=csat_rating,
                        )
                        session.add(csat)
                        await session.commit()
                    thank_msg = "Değerlendirmeniz için teşekkür ederiz! 🙏" if csat_rating >= 4 else "Geri bildiriminiz için teşekkür ederiz. Daha iyi olmak için çalışacağız! 🙏"
                    await send_reply(sender, thank_msg)
                    # Trigger self-learning on low CSAT
                    if csat_rating <= 2:
                        try:
                            from app.services.ai_learning import trigger_learning_on_negative_signal
                            import asyncio
                            asyncio.create_task(trigger_learning_on_negative_signal(sender, "low_csat", "instagram"))
                        except Exception:
                            pass
                    continue
                except Exception as e:
                    print(f"CSAT save error: {e}")

            # Check for negative signals and trigger learning
            negative_keywords = ["not interested", "no thanks", "too expensive", "stop", "unsubscribe", "terrible", "worst", "never again", "waste of time", "horrible service"]
            last_msg_lower = text.lower()
            if any(kw in last_msg_lower for kw in negative_keywords):
                try:
                    from app.services.ai_learning import trigger_learning_on_negative_signal
                    import asyncio
                    asyncio.create_task(trigger_learning_on_negative_signal(sender, "negative_reaction", "instagram"))
                except Exception:
                    pass

            # Auto-assign conversation
            try:
                from app.services.assignment import auto_assign_conversation
                await auto_assign_conversation(sender)
            except Exception as e:
                print(f"Auto-assign error: {e}")

            # Check response mode
            response_mode = "ai_auto"
            try:
                from app.core.database import async_session as asess
                from app.models.conversation_state import ConversationState as CS
                async with asess() as sess:
                    conv_result = await sess.execute(select(CS).where(CS.sender_id == sender))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state:
                        response_mode = conv_state.response_mode or "ai_auto"
            except Exception:
                pass

            if response_mode == "human_only":
                print(f"Human-only mode for {sender}, skipping AI reply")
                continue

            # Check business hours
            is_open, closed_message = await is_within_business_hours()
            if not is_open and closed_message:
                await send_reply(sender, closed_message)
                continue
            reply = await get_reply(sender, text)

            # If ai_suggest mode, save reply as pending instead of sending
            if response_mode == "ai_suggest" and reply is not None:
                try:
                    async with asess() as sess:
                        conv_result = await sess.execute(select(CS).where(CS.sender_id == sender))
                        conv_state = conv_result.scalar_one_or_none()
                        if conv_state:
                            conv_state.pending_reply = reply
                            conv_state.pending_product_ids = []
                            await sess.commit()
                    print(f"AI Suggest mode: saved pending reply for {sender}")
                    continue
                except Exception as e:
                    print(f"Pending save error: {e}")

            if reply is not None:
                await send_reply(sender, reply)

            # Auto-escalation based on intent score
            try:
                async with asess() as sess:
                    conv_result = await sess.execute(select(CS).where(CS.sender_id == sender))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state and conv_state.intent_score >= 80 and conv_state.response_mode == "ai_auto":
                        conv_state.response_mode = "ai_suggest"
                        conv_state.escalated = True
                        conv_state.escalation_reason = f"Intent score reached {conv_state.intent_score}"
                        await sess.commit()
                        print(f"Auto-escalated {sender}: score {conv_state.intent_score}")
            except Exception as e:
                print(f"Escalation check error: {e}")

            # Auto-trigger HappyRobot call for very high intent
            try:
                async with asess() as sess:
                    from app.models.customer import Customer
                    conv_result = await sess.execute(select(CS).where(CS.sender_id == sender))
                    conv_state = conv_result.scalar_one_or_none()
                    if conv_state and conv_state.intent_score >= 90:
                        cust_result = await sess.execute(
                            select(Customer).where(Customer.instagram_sender_id == sender)
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
                            print(f"HappyRobot call triggered for {sender}, score {conv_state.intent_score}")
            except Exception as e:
                print(f"HappyRobot auto-call error: {e}")
    return {"status": "ok"}

async def get_active_persona_prompt():
    try:
        from app.core.database import async_session
        from app.models.models import Persona
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(
                select(Persona).order_by(Persona.updated_at.desc()).limit(1)
            )
            persona = result.scalar_one_or_none()
            if not persona:
                return "You are a helpful assistant. Be concise and professional."

            if persona.system_prompt and len(persona.system_prompt.strip()) > 10:
                return persona.system_prompt

            # Build prompt from fields if system_prompt is empty
            parts = []
            if persona.display_name:
                parts.append(f"You are {persona.display_name}.")
            if persona.role_title:
                parts.append(f"Your role is {persona.role_title}.")
            if persona.company_name:
                parts.append(f"You work at {persona.company_name}.")
            if persona.background_story:
                parts.append(f"Background: {persona.background_story}")
            if persona.speaking_style:
                parts.append(f"Speaking style: {persona.speaking_style}")
            if persona.tone_description:
                parts.append(f"Tone: {persona.tone_description}")

            traits = []
            if persona.friendliness and persona.friendliness > 70:
                traits.append("very friendly")
            if persona.formality and persona.formality > 70:
                traits.append("formal")
            elif persona.formality and persona.formality < 30:
                traits.append("casual")
            if persona.empathy and persona.empathy > 70:
                traits.append("empathetic")
            if persona.patience and persona.patience > 70:
                traits.append("patient")
            if traits:
                parts.append(f"Personality: {', '.join(traits)}.")

            if persona.example_phrases:
                phrases = persona.example_phrases if isinstance(persona.example_phrases, list) else []
                if phrases:
                    parts.append(f"Example phrases you use: {', '.join(phrases[:3])}")

            if persona.forbidden_phrases:
                forbidden = persona.forbidden_phrases if isinstance(persona.forbidden_phrases, list) else []
                if forbidden:
                    parts.append(f"Never say: {', '.join(forbidden[:3])}")

            parts.append("Keep responses concise, 2-3 sentences maximum.")
            parts.append("Respond in the same language the user writes to you.")

            return " ".join(parts) if parts else "You are a helpful assistant."
    except Exception as e:
        print(f"Persona load error: {e}")
        return "You are a helpful assistant. Be concise and professional."


async def get_products_for_persona(persona_id: str):
    """Get all products from enabled catalogs assigned to this persona."""
    try:
        from app.core.database import async_session
        from app.models.catalog_models import Catalog, Product
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(Product).join(Catalog).where(
                    and_(
                        Catalog.persona_id == persona_id,
                        Catalog.enabled == "true",
                    )
                )
            )
            products = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "price": p.price,
                    "features": p.features or [],
                    "tags": p.tags or [],
                    "image_url": p.image_url,
                }
                for p in products
            ]
    except Exception as e:
        print(f"Product load error: {e}")
        return []


async def send_instagram_image(recipient_id: str, image_url: str):
    """Send an image attachment via Instagram Graph API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
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
            print(f"IG Image [{resp.status_code}]: {image_url}")
            return resp.status_code == 200
    except Exception as e:
        print(f"Send image error: {e}")
        return False


async def upsert_customer_from_instagram(sender_id: str, profile_name: str = None):
    """Create or update a Customer record for an Instagram sender."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.instagram_sender_id == sender_id)
            )
            customer = result.scalar_one_or_none()

            if customer:
                customer.last_contact_at = datetime.utcnow()
                customer.updated_at = datetime.utcnow()
                if customer.is_archived:
                    customer.is_archived = False
                if profile_name and not customer.display_name:
                    customer.display_name = profile_name
                try:
                    msgs = int(customer.total_messages or "0") + 1
                except (ValueError, TypeError):
                    msgs = 1
                customer.total_messages = str(msgs)
                await session.commit()
                return customer.id

            customer = Customer(
                display_name=profile_name or "",
                handle="",
                source="instagram",
                instagram_sender_id=sender_id,
                tags=[],
                custom_fields={},
                notes="",
                external_ids={},
                last_contact_at=datetime.utcnow(),
                total_messages="1",
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)
            return customer.id
    except Exception as e:
        print(f"Customer upsert error: {e}")
        return None


async def load_or_create_conversation_state(sender_id: str, persona_id: str = None):
    """Load existing ConversationState or create new one."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = ConversationState(
                sender_id=sender_id,
                persona_id=persona_id,
                channel="instagram",
                messages=[],
                score_history=[],
                signals=[],
                products_mentioned=[],
            )
            session.add(state)
            await session.commit()
            await session.refresh(state)
        return state.id, state.messages or [], state.products_mentioned or []


async def update_conversation_state(
    sender_id: str,
    new_messages: list,
    scoring: dict,
    products_added: list = None,
):
    """Append new messages, update scoring, append to score history."""
    async with async_session() as session:
        result = await session.execute(
            select(ConversationState).where(ConversationState.sender_id == sender_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            return

        # Append messages
        existing_messages = list(state.messages or [])
        for m in new_messages:
            existing_messages.append({
                "role": m["role"],
                "content": m["content"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        state.messages = existing_messages[-100:]  # keep last 100

        # Update scoring snapshot
        state.intent_score = scoring.get("intent_score", 0)
        state.stage = scoring.get("stage", "awareness")
        state.signals = scoring.get("signals", [])
        state.next_action = scoring.get("next_action", "")
        state.score_breakdown = scoring.get("score_breakdown", "")

        # Append to score history
        history = list(state.score_history or [])
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "intent_score": scoring.get("intent_score", 0),
            "stage": scoring.get("stage", "awareness"),
            "trigger_message": (new_messages[-1]["content"] if new_messages else "")[:200],
        })
        state.score_history = history[-50:]  # keep last 50

        # Update product mentions
        if products_added:
            existing = list(state.products_mentioned or [])
            for p in products_added:
                if p not in existing:
                    existing.append(p)
            state.products_mentioned = existing[-50:]

        state.message_count = (state.message_count or 0) + len(new_messages)
        state.last_message_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()

        # Auto-tag the conversation
        try:
            tags = await auto_tag_conversation(list(state.messages or []))
            if tags:
                state.categories = tags
        except Exception as e:
            print(f"Auto-tagging error: {e}")

        await session.commit()


async def get_active_persona():
    """Get the most recently updated persona object."""
    try:
        from app.core.database import async_session
        from app.models.models import Persona
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(
                select(Persona).order_by(Persona.updated_at.desc()).limit(1)
            )
            return result.scalar_one_or_none()
    except Exception as e:
        print(f"Persona load error: {e}")
        return None


async def get_reply(sender_id, user_msg):
    if sender_id not in conversation_history:
        conversation_history[sender_id] = []
    history = conversation_history[sender_id]
    history.append({"role": "user", "content": user_msg})
    if len(history) > 20:
        conversation_history[sender_id] = history[-20:]
        history = conversation_history[sender_id]

    persona = await get_active_persona()
    system_prompt = await get_active_persona_prompt()

    # Load products for this persona
    persona_id = persona.id if persona else None
    products = await get_products_for_persona(persona_id) if persona_id else []

    # Build products context
    products_text = ""
    if products:
        products_text = "\n\n## PRODUCT CATALOG\nYou have a product catalog. When you put product IDs in recommend_product_ids, the system will AUTOMATICALLY send the product images to the customer. You DO have the ability to show images — just include the IDs.\n\nAvailable products:\n\n"
        for p in products:
            products_text += f"ID: {p['id']}\nName: {p['name']}\nPrice: {p['price']}\nDescription: {p['description']}\nTags: {', '.join(p['tags'])}\n\n"
        products_text += "\nYou MUST respond in this JSON format: {\"message\": \"your reply text\", \"recommend_product_ids\": [\"id1\", \"id2\"]}\nRULES:\n- If the customer asks about ANY product, category, or shows interest, you MUST include 1-3 matching product IDs in recommend_product_ids.\n- Describe the recommended products briefly in your message text.\n- NEVER say you cannot send images or pictures. The system sends them automatically when you include IDs.\n- Only use an empty recommend_product_ids [] for pure greetings like 'hi' or 'hello' with zero product context."

    # Load conversation state and score intent
    state_id, state_messages, state_products = await load_or_create_conversation_state(sender_id, persona_id)
    scoring_messages = state_messages + [{"role": "user", "content": user_msg}]
    scoring = await score_conversation(scoring_messages, state_products)

    scoring_context = f"""

## CURRENT CUSTOMER STATE (use this to tailor your reply)
Intent Score: {scoring['intent_score']}/100
Stage: {scoring['stage']}
Recommended tone: {scoring['recommended_tone']}
Next action: {scoring['next_action']}
Signals detected: {', '.join(scoring['signals']) if scoring['signals'] else 'none yet'}
Analysis: {scoring['score_breakdown']}

STRATEGY BASED ON SCORE:
- If score 0-20: be welcoming and informative, introduce the business, ask what they're looking for
- If score 21-40: show interest in their needs, offer relevant product categories, be consultative
- If score 41-60: actively recommend specific products, send images, highlight features and benefits
- If score 61-80: address specifics (price, availability, shipping), create gentle urgency, ask for commitment softly
- If score 81-100: focus on closing — ask for the order, explain checkout, remove friction, be direct
- If stage is "objection": acknowledge their concern, address it directly with facts, reassure them
"""

    # Load quick reply templates
    quick_replies_text = ""
    try:
        from app.models.quick_reply import QuickReply
        async with async_session() as session:
            qr_result = await session.execute(select(QuickReply))
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
4. If they want YOUR number, say: "Of course! You can reach us at [COMPANY_PHONE]. We're looking forward to your call!"
5. When the customer provides a phone number, respond with EXACTLY this JSON format:
   {"message": "Perfect! We're calling you right now! 📞", "recommend_product_ids": [], "trigger_call": true, "call_number": "+XXXXXXXXXXX"}
   Replace +XXXXXXXXXXX with the actual phone number they provided. Make sure to include country code.
6. IMPORTANT: Only set trigger_call to true when the customer has EXPLICITLY provided their phone number. Never assume a phone number.
7. Do NOT offer to call if you already offered in this conversation (check previous messages).
"""
        except Exception:
            pass

    # Self-learning: inject lessons from past conversations
    try:
        from app.services.ai_learning import get_lessons_for_prompt
        lessons_text = await get_lessons_for_prompt()
    except Exception:
        lessons_text = ""

    full_system_prompt = system_prompt + products_text + scoring_context + call_offer_text + quick_replies_text + lessons_text
    # Detect language of last user message and add override system message
    last_user_text = ""
    for m in reversed(history):
        if m.get("role") == "user":
            last_user_text = m.get("content", "")
            break
    language_override = {"role": "system", "content": f"OVERRIDE: The customer wrote: '{last_user_text}'. You MUST reply in the same language as this text. If this is English, your entire reply must be in English. If Turkish, reply in Turkish. NO EXCEPTIONS."}

    messages = [{"role": "system", "content": full_system_prompt}, language_override] + history

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 300,
                    **({"response_format": {"type": "json_object"}} if products else {}),
                },
            )
            resp.raise_for_status()
            reply_raw = resp.json()["choices"][0]["message"]["content"]

        # Parse product recommendations if products are available
        reply_text = reply_raw
        recommend_product_ids = []
        if products:
            print(f"LLM raw response: {reply_raw[:300]}")
            try:
                import json
                parsed = json.loads(reply_raw)
                reply_text = parsed.get("message", reply_raw)
                recommend_product_ids = parsed.get("recommend_product_ids", [])
                print(f"Parsed recommend_product_ids: {recommend_product_ids}")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"JSON parse failed: {e}")
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

        # If call triggered, initiate HappyRobot call
        if trigger_call and call_number:
            import asyncio
            try:
                from app.models.customer import Customer
                async with asess() as sess:
                    cust_result = await sess.execute(
                        select(Customer).where(Customer.instagram_sender_id == sender)
                    )
                    customer = cust_result.scalar_one_or_none()
                    if customer:
                        customer.phone = call_number
                        await sess.commit()

                recent_msgs = conversation_history.get(sender, [])[-5:]
                context = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in recent_msgs])
                asyncio.create_task(_handle_happyrobot_call(sender, call_number, context))
            except Exception as e:
                print(f"Call trigger error: {e}")

        history.append({"role": "assistant", "content": reply_text})

        # Store interaction in Cognee memory
        try:
            from app.services.cognee_memory import remember_customer
            import asyncio
            customer_info = f"Customer {sender} said: '{text[:100]}'. AI responded about products/services. Channel: instagram."
            asyncio.create_task(remember_customer(customer_info))
        except Exception:
            pass

        # Update conversation state with scoring
        try:
            await update_conversation_state(
                sender_id=sender_id,
                new_messages=[
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": reply_text},
                ],
                scoring=scoring,
                products_added=recommend_product_ids if recommend_product_ids else [],
            )
        except Exception as e:
            print(f"State update error (non-fatal): {e}")

        # Send product images if recommended
        if recommend_product_ids:
            await send_reply(sender_id, reply_text)
            for pid in recommend_product_ids[:3]:
                product = next((p for p in products if p["id"] == pid), None)
                if product and product.get("image_url"):
                    print(f"Sending image: {product['image_url']}")
                    await send_instagram_image(sender_id, product["image_url"])
                else:
                    print(f"Product not found or no image_url for pid: {pid}")

            # Auto-trigger try-on for first recommended product
            if recommend_product_ids:
                first_product = next((p for p in products if p["id"] == recommend_product_ids[0]), None)
                if first_product and first_product.get("image_url"):
                    import asyncio
                    asyncio.create_task(_handle_tryon_async_instagram(sender_id, first_product))

            return None  # Already sent reply + images

        return reply_text
    except Exception as e:
        print(f"LLM Error: {e}")
        return "Sorry, I am having a technical issue. Please try again!"

async def send_instagram_video(recipient_id: str, video_url: str):
    """Send a video via Instagram Messaging API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "video",
                            "payload": {"url": video_url},
                        }
                    },
                },
            )
            print(f"IG Video [{resp.status_code}]: {video_url[:50]}")
    except Exception as e:
        print(f"IG video send error: {e}")


async def _handle_tryon_async_instagram(sender_id: str, product: dict):
    """Background task: generate try-on image + video and send to customer."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video

        # Step 1: Generate try-on image
        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            # Send the try-on image
            await send_instagram_image(sender_id, model_result["image_url"])

            # Step 2: Generate video (silently)
            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                await send_instagram_video(sender_id, video_result["video_url"])
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")


async def _handle_happyrobot_call(sender_id: str, phone_number: str, context: str):
    """Background task: trigger HappyRobot outbound call."""
    try:
        from app.services.happyrobot_service import trigger_outbound_call
        from app.core.database import async_session as asess
        from app.models.customer import Customer
        from sqlalchemy import select

        customer_name = ""
        async with asess() as sess:
            result = await sess.execute(
                select(Customer).where(Customer.instagram_sender_id == sender_id)
            )
            cust = result.scalar_one_or_none()
            if cust:
                customer_name = cust.display_name or ""

        import asyncio
        await asyncio.sleep(2)

        result = await trigger_outbound_call(
            phone_number=phone_number,
            customer_name=customer_name,
            context=f"Customer was chatting on Instagram and showed high buying intent. Recent conversation: {context}",
        )

        if result.get("success"):
            await send_reply(sender_id, "📞 We're connecting your call now! Please pick up in a moment.")
            print(f"HappyRobot call initiated: {result.get('call_id')}")
        else:
            await send_reply(sender_id, "Sorry, we couldn't connect the call right now. Can we try again in a few minutes?")
            print(f"HappyRobot call failed: {result.get('error')}")

    except Exception as e:
        print(f"HappyRobot call error: {e}")


async def send_reply(recipient_id, text):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"IG Reply [{resp.status_code}]: {text[:50]}")
    except Exception as e:
        print(f"Send Error: {e}")
