"""HappyRobot API integration — trigger outbound AI phone calls."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

HAPPYROBOT_API_KEY = os.getenv("HAPPYROBOT_API_KEY", "")
HAPPYROBOT_USE_CASE_ID = os.getenv("HAPPYROBOT_USE_CASE_ID", "")
HAPPYROBOT_NUMBER_ID = os.getenv("HAPPYROBOT_NUMBER_ID", "")
HAPPYROBOT_API_URL = os.getenv("HAPPYROBOT_API_URL", "https://app.happyrobot.ai/api/v1")


async def trigger_outbound_call(
    phone_number: str,
    customer_name: str = "",
    context: str = "",
    language: str = "en-US",
) -> dict:
    """Trigger an outbound AI phone call via HappyRobot."""
    if not HAPPYROBOT_API_KEY:
        return {"success": False, "error": "HAPPYROBOT_API_KEY not set"}

    try:
        payload = {
            "use_case_id": HAPPYROBOT_USE_CASE_ID,
            "phone_number": phone_number,
            "language": language,
            "params": {
                "customer_name": customer_name,
                "context": context,
            },
            "metadata": {
                "source": "persona_platform",
                "customer_name": customer_name,
            },
        }

        if HAPPYROBOT_NUMBER_ID:
            payload["number_id"] = HAPPYROBOT_NUMBER_ID

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{HAPPYROBOT_API_URL}/dial/outbound",
                headers={
                    "Content-Type": "application/json",
                    "authorization": f"Bearer {HAPPYROBOT_API_KEY}",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "call_id": data.get("id", ""),
                "status": data.get("status", ""),
                "data": data,
            }
    except Exception as e:
        print(f"HappyRobot call error: {e}")
        return {"success": False, "error": str(e)}


async def get_call_status(call_id: str) -> dict:
    """Get the status and transcript of a HappyRobot call."""
    if not HAPPYROBOT_API_KEY:
        return {"error": "HAPPYROBOT_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{HAPPYROBOT_API_URL}/calls/{call_id}",
                headers={"authorization": f"Bearer {HAPPYROBOT_API_KEY}"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}
