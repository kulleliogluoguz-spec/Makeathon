"""Send emails via Resend API."""

import os
import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")


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
