"""HappyRobot API integration — trigger outbound AI phone calls."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

HAPPYROBOT_API_KEY = os.getenv("HAPPYROBOT_API_KEY", "")
HAPPYROBOT_USE_CASE_ID = os.getenv("HAPPYROBOT_USE_CASE_ID", "")
HAPPYROBOT_NUMBER_ID = os.getenv("HAPPYROBOT_NUMBER_ID", "")
HAPPYROBOT_API_URL = os.getenv("HAPPYROBOT_API_URL", "https://app.happyrobot.ai/api/v1")
HAPPYROBOT_WEBHOOK_URL = os.getenv("HAPPYROBOT_WEBHOOK_URL", "https://workflows.platform.eu.happyrobot.ai/hooks/fhiyxhmghaqj")


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
                HAPPYROBOT_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
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


async def trigger_outbound_call_full(
    phone_number: str,
    customer_name: str = "",
    customer_company: str = "",
    customer_title: str = "",
    customer_email: str = "",
    persona_context: dict = None,
    available_slots: list = None,
    lead_reason: str = "",
    lead_approach: str = "",
    language: str = "en-US",
) -> dict:
    """Trigger an outbound AI phone call with full persona context and meeting scheduling."""
    if not HAPPYROBOT_API_KEY:
        return {"success": False, "error": "HAPPYROBOT_API_KEY not set"}

    persona = persona_context or {}
    company_name = persona.get("company_name", "our company")
    company_desc = persona.get("description", "")
    services = ", ".join(persona.get("expertise_areas", []))
    sales_manager = persona.get("display_name", "our sales manager")

    # Build available meeting slots text
    slots_text = ""
    if available_slots:
        slots_text = "Available meeting times you can offer:\n"
        for slot in available_slots[:6]:
            slots_text += f"- {slot}\n"
        slots_text += "\nOffer 2-3 of these times and let the customer pick one."
    else:
        slots_text = "For meeting scheduling, suggest 'sometime this week or next week' and say the sales manager will follow up with specific times."

    call_prompt = f"""You are a professional sales development representative calling on behalf of {company_name}.

## WHO YOU'RE CALLING
- Name: {customer_name}
- Company: {customer_company}
- Title: {customer_title}
- Why we're reaching out: {lead_reason}
- Recommended approach: {lead_approach}

## ABOUT {company_name.upper()}
{company_desc}

Our services/expertise: {services}

## YOUR CALL SCRIPT (follow this order)

1. GREETING (10 seconds):
   "Hi, is this {customer_name}? My name is {sales_manager} and I'm calling from {company_name}."

2. REASON FOR CALLING (15 seconds):
   Explain briefly why you're reaching out. Use this context: {lead_reason}
   Keep it natural and conversational, not scripted.

3. PRODUCT PITCH (30 seconds MAX):
   Explain what {company_name} does in 2-3 sentences. Be concise and focus on the value:
   {company_desc}
   Focus on how it solves THEIR specific problem.

4. EMAIL OFFER:
   "I'd love to send you a quick email with more details about how we can help {customer_company}. Would that be okay?"
   - If YES: "Great, I'll send that over right after our call to {customer_email if customer_email else 'your email. What would be the best email address?'}."
   - If they give an email, note it down.
   - If NO: That's fine, move to step 5.

5. MEETING OFFER:
   "Would you be open to a quick 15-minute call with {sales_manager}, our sales manager, to explore this further?"
   - If YES:
     {slots_text}
     Confirm the date and time clearly.
     "Perfect, I'll send you a calendar invite. {sales_manager} will be in touch!"
   - If NOT NOW: "No problem at all! I'll make sure {sales_manager} follows up when it's more convenient."
   - If NO: "I completely understand. If you change your mind, feel free to reach out anytime."

6. CLOSING:
   "Thank you for your time, {customer_name}. Have a great day!"

## RULES
- Keep the entire call under 3 minutes
- Be warm, professional, and NOT pushy
- If they say they're busy, offer to call back at a better time
- Never argue or pressure
- Listen more than you talk
- If they ask about pricing, say "That's something {sales_manager} can discuss in detail during the meeting"
- ALWAYS extract these from the conversation if possible:
  * Their email address (if not already known)
  * Whether they want the email sent
  * Whether they agreed to a meeting and what time
  * Any objections or concerns they mentioned
  * Their level of interest (1-10)
"""

    try:
        payload = {
            "use_case_id": HAPPYROBOT_USE_CASE_ID,
            "phone_number": phone_number,
            "language": language,
            "params": {
                "customer_name": customer_name,
                "customer_company": customer_company,
                "customer_title": customer_title,
                "company_name": company_name,
                "prompt": call_prompt,
            },
            "metadata": {
                "source": "persona_platform",
                "customer_name": customer_name,
                "customer_company": customer_company,
                "customer_email": customer_email,
                "lead_reason": lead_reason,
            },
        }

        if HAPPYROBOT_NUMBER_ID:
            payload["number_id"] = HAPPYROBOT_NUMBER_ID

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                HAPPYROBOT_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
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
