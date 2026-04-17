"""Send Telegram messages and handle incoming messages via bot."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(chat_id: str, text: str) -> dict:
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
            return {"success": False, "error": data.get("description", "Unknown error")}
    except Exception as e:
        print(f"Telegram send error: {e}")
        return {"success": False, "error": str(e)}


async def send_telegram_image(chat_id: str, image_url: str, caption: str = "") -> dict:
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


async def send_telegram_video(chat_id: str, video_url: str, caption: str = "") -> dict:
    """Send a video via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendVideo",
                json={"chat_id": chat_id, "video": video_url, "caption": caption},
            )
            data = resp.json()
            return {"success": data.get("ok", False)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def set_webhook(webhook_url: str) -> dict:
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
