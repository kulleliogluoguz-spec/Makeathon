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
            await send_reply(sender, reply)
    return {"status": "ok"}

async def get_reply(sender_id, user_msg):
    if sender_id not in conversation_history:
        conversation_history[sender_id] = []
    history = conversation_history[sender_id]
    history.append({"role": "user", "content": user_msg})
    if len(history) > 20:
        conversation_history[sender_id] = history[-20:]
        history = conversation_history[sender_id]
    try:
        from app.core.database import async_session
        from app.models.models import Persona
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(Persona).limit(1))
            persona = result.scalar_one_or_none()
            system_prompt = persona.system_prompt if persona and persona.system_prompt else "You are a helpful business assistant. Keep responses concise."
    except:
        system_prompt = "You are a helpful business assistant. Keep responses concise."
    messages = [{"role": "system", "content": system_prompt}] + history
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4.1-nano", "messages": messages, "temperature": 0.7, "max_tokens": 300},
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        return reply
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
