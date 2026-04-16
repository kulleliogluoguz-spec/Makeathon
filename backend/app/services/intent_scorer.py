"""Intent scoring using gpt-4.1-nano. Analyzes conversation and returns structured scoring data."""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


SCORING_SYSTEM_PROMPT = """You are a sales conversation analyst. Analyze the conversation between a customer and a business AI assistant, and score the customer's purchase intent.

Return a JSON object with EXACTLY these fields:

{
  "intent_score": integer 0-100,
  "stage": one of "awareness" | "interest" | "consideration" | "decision" | "purchase" | "objection" | "post_purchase",
  "signals": array of short strings describing what the customer has done (e.g. "asked about pricing", "mentioned budget", "asked about shipping", "showed urgency", "compared two products"),
  "next_action": one of "provide_info" | "send_pricing" | "send_product_images" | "create_urgency" | "ask_for_commitment" | "handle_objection" | "nurture" | "transfer_to_human",
  "score_breakdown": 1-2 sentence explanation of why you gave this score,
  "recommended_tone": one of "informative" | "enthusiastic" | "consultative" | "assertive" | "empathetic" | "urgent"
}

SCORING GUIDE:
- 0-20: Just browsing, vague questions, no clear product interest
- 21-40: Showing curiosity, asking general questions, early exploration
- 41-60: Active interest, asking about specific products or features, comparing options
- 61-80: Serious consideration, asking about price/shipping/availability, showing buying signals
- 81-100: Ready to buy, asking about checkout/payment/delivery logistics, high urgency

STAGE DEFINITIONS:
- awareness: just discovered the business, general questions
- interest: asking about specific products or categories
- consideration: comparing options, asking detailed questions about features
- decision: asking about price, availability, shipping, warranty
- purchase: ready to transact, asking how to buy
- objection: hesitating, raising concerns (price too high, wrong fit, etc.)
- post_purchase: already bought, follow-up questions

Return ONLY valid JSON, no other text."""


async def score_conversation(messages: list, products_mentioned: list = None) -> dict:
    """Score a conversation based on message history.
    messages: [{role: 'user' | 'assistant', content: str}]
    Returns dict with intent_score, stage, signals, next_action, score_breakdown, recommended_tone
    """
    if not OPENAI_API_KEY or not messages:
        return {
            "intent_score": 0,
            "stage": "awareness",
            "signals": [],
            "next_action": "provide_info",
            "score_breakdown": "Not enough data",
            "recommended_tone": "informative",
        }

    # Limit to last 20 messages
    recent = messages[-20:] if len(messages) > 20 else messages

    transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

    context = ""
    if products_mentioned:
        context = f"\n\nProducts mentioned in conversation: {', '.join(products_mentioned[:10])}"

    user_message = f"Analyze this conversation and return the JSON scoring:\n\n{transcript}{context}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [
                        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 600,
                    "response_format": {"type": "json_object"},
                },
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        # Validate and sanitize
        return {
            "intent_score": max(0, min(100, int(parsed.get("intent_score", 0)))),
            "stage": parsed.get("stage", "awareness"),
            "signals": parsed.get("signals", [])[:10],
            "next_action": parsed.get("next_action", "provide_info"),
            "score_breakdown": parsed.get("score_breakdown", "")[:500],
            "recommended_tone": parsed.get("recommended_tone", "informative"),
        }
    except Exception as e:
        print(f"Intent scoring error: {e}")
        return {
            "intent_score": 0,
            "stage": "awareness",
            "signals": [],
            "next_action": "provide_info",
            "score_breakdown": f"Scoring failed: {e}",
            "recommended_tone": "informative",
        }
