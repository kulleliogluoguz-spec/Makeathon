"""AI-powered category/tag assignment using gpt-4.1-nano."""

import os
import json
import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.core.database import async_session
from app.models.category import Category

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def get_all_categories() -> list:
    async with async_session() as session:
        result = await session.execute(select(Category))
        cats = result.scalars().all()
        return [
            {"slug": c.slug, "name": c.name, "description": c.description}
            for c in cats
        ]


async def auto_tag_conversation(messages: list) -> list:
    """Given a conversation, return a list of category slugs (1-4) that apply."""
    if not OPENAI_API_KEY or not messages:
        return []

    categories = await get_all_categories()
    if not categories:
        return []

    cat_list_text = "\n".join([
        f"- {c['slug']}: {c['name']} — {c['description']}"
        for c in categories
    ])
    valid_slugs = {c["slug"] for c in categories}

    recent = messages[-10:]
    transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

    system_prompt = f"""You are a conversation classifier. Given a conversation, select 1-4 category tags that best describe the current state of the conversation.

Available categories:
{cat_list_text}

Rules:
- Return ONLY slugs from the list above. Do not invent new slugs.
- Return 1-4 tags maximum. If only one clearly applies, return just one.
- If no category fits well, return an empty list.
- Base your decision on the most recent messages — what is the customer currently asking or doing?

Return JSON: {{"tags": ["slug1", "slug2"]}}"""

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        tags = parsed.get("tags", [])

        # Validate — only return slugs that exist
        return [t for t in tags if t in valid_slugs][:4]
    except Exception as e:
        print(f"Category tagging error: {e}")
        return []
