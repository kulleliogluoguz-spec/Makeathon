from dotenv import load_dotenv
load_dotenv()
import os
import httpx
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse

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
            reply = await get_reply(sender, text)
            if reply is not None:
                await send_reply(sender, reply)
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

    full_system_prompt = system_prompt + products_text
    messages = [{"role": "system", "content": full_system_prompt}] + history

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

        history.append({"role": "assistant", "content": reply_text})

        # Send product images if recommended
        if recommend_product_ids:
            await send_reply(sender_id, reply_text)
            for pid in recommend_product_ids[:3]:
                product = next((p for p in products if p["id"] == pid), None)
                if product and product.get("image_url"):
                    await send_instagram_image(sender_id, product["image_url"])
            return None  # Already sent reply + images

        return reply_text
    except Exception as e:
        print(f"LLM Error: {e}")
        return "Sorry, I am having a technical issue. Please try again!"

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
