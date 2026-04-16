"""Send CSAT survey messages to customers on each channel."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
MESSENGER_TOKEN = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN", "")

SURVEY_MESSAGE = """How was your experience? Please rate us by replying with a number:

⭐ 1 — Very Unsatisfied
⭐⭐ 2 — Unsatisfied
⭐⭐⭐ 3 — Neutral
⭐⭐⭐⭐ 4 — Satisfied
⭐⭐⭐⭐⭐ 5 — Very Satisfied

Just reply with a number (1-5)!"""

SURVEY_MESSAGE_TR = """Deneyiminizi nasıl değerlendirirsiniz? Lütfen bir sayı ile yanıtlayın:

⭐ 1 — Çok Memnuniyetsiz
⭐⭐ 2 — Memnuniyetsiz
⭐⭐⭐ 3 — Nötr
⭐⭐⭐⭐ 4 — Memnun
⭐⭐⭐⭐⭐ 5 — Çok Memnun

Sadece bir sayı ile yanıtlayın (1-5)!"""


async def send_csat_survey(sender_id: str, channel: str, language: str = "en"):
    """Send CSAT survey message to the customer."""
    msg = SURVEY_MESSAGE_TR if language == "tr" else SURVEY_MESSAGE

    if channel == "instagram":
        await _send_instagram(sender_id, msg)
    elif channel == "messenger":
        await _send_messenger(sender_id, msg)


async def _send_instagram(recipient_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.instagram.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {INSTAGRAM_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"CSAT Survey IG [{resp.status_code}]")
    except Exception as e:
        print(f"CSAT IG error: {e}")


async def _send_messenger(recipient_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                headers={"Authorization": f"Bearer {MESSENGER_TOKEN}", "Content-Type": "application/json"},
                json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            )
            print(f"CSAT Survey MSG [{resp.status_code}]")
    except Exception as e:
        print(f"CSAT MSG error: {e}")


def is_csat_response(text: str) -> int:
    """Check if a message is a CSAT rating response. Returns 0 if not, 1-5 if it is."""
    cleaned = text.strip()
    if cleaned in ("1", "2", "3", "4", "5"):
        return int(cleaned)
    return 0
