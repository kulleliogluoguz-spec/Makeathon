"""AI Self-Learning System — analyzes conversations and learns from mistakes."""

import os
import json
import httpx
from datetime import datetime
from sqlalchemy import select, desc
from app.core.database import async_session
from app.models.ai_lesson import AILesson

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def analyze_conversation_for_lessons(messages: list, outcome: str, channel: str = "", conversation_id: str = ""):
    """Analyze a completed or ongoing conversation to extract lessons.
    Called after negative signals are detected (low CSAT, lost customer, negative reaction)."""

    if not messages or len(messages) < 4 or not OPENAI_API_KEY:
        return

    # Build conversation text
    conv_text = ""
    for m in messages[-20:]:  # Last 20 messages max
        role = "AI" if m.get("role") == "assistant" else "Customer"
        conv_text += f"{role}: {m.get('content', '')}\n"

    prompt = f"""Analyze this customer conversation and identify any mistakes the AI made that caused negative outcomes.

Conversation:
{conv_text}

Outcome: {outcome}

Look for these types of mistakes:
1. Being too pushy or aggressive with sales
2. Ignoring customer concerns or objections
3. Providing wrong information
4. Bad timing (offering something too early or too late)
5. Wrong tone (too formal, too casual, insensitive)
6. Not listening to what customer actually wants
7. Making promises that can't be kept
8. Responding with generic templates instead of personalized answers
9. Not offering alternatives when customer says no
10. Failing to de-escalate when customer is frustrated

For each mistake found, provide:
- What the AI said (exact quote from conversation)
- How the customer reacted negatively
- What category this falls under
- What the AI should have said instead
- A general lesson for future conversations

Return JSON only:
{{
    "mistakes_found": true/false,
    "lessons": [
        {{
            "category": "pushy|objection|greeting|closing|product_pitch|tone|timing|listening|generic|escalation",
            "ai_said": "exact quote of what AI said wrong",
            "customer_reaction": "how customer reacted",
            "outcome": "lost_customer|negative_feedback|low_csat|objection|ignored",
            "lesson": "what should be done differently in the future",
            "better_alternative": "what should be said instead in a similar situation"
        }}
    ]
}}

If the AI did everything well and no mistakes were made, return:
{{"mistakes_found": false, "lessons": []}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            data = resp.json()
            result = json.loads(data["choices"][0]["message"]["content"])

        if not result.get("mistakes_found"):
            print(f"Self-learning: No mistakes found in conversation {conversation_id}")
            return

        # Save lessons to database
        async with async_session() as session:
            for lesson_data in result.get("lessons", []):
                # Check if similar lesson already exists
                existing = await session.execute(
                    select(AILesson).where(
                        AILesson.category == lesson_data.get("category", ""),
                        AILesson.lesson == lesson_data.get("lesson", ""),
                    )
                )
                existing_lesson = existing.scalar_one_or_none()

                if existing_lesson:
                    # Increase weight — same mistake happening again
                    existing_lesson.weight += 1
                    existing_lesson.updated_at = datetime.utcnow()
                    print(f"Self-learning: Existing lesson reinforced (weight: {existing_lesson.weight}): {existing_lesson.lesson[:50]}")
                else:
                    # New lesson
                    new_lesson = AILesson(
                        category=lesson_data.get("category", ""),
                        ai_said=lesson_data.get("ai_said", ""),
                        customer_reaction=lesson_data.get("customer_reaction", ""),
                        outcome=lesson_data.get("outcome", outcome),
                        lesson=lesson_data.get("lesson", ""),
                        better_alternative=lesson_data.get("better_alternative", ""),
                        channel=channel,
                        conversation_id=conversation_id,
                    )
                    session.add(new_lesson)
                    print(f"Self-learning: New lesson learned: {new_lesson.lesson[:50]}")

            await session.commit()

    except Exception as e:
        print(f"Self-learning analysis error: {e}")


async def get_lessons_for_prompt(max_lessons: int = 10) -> str:
    """Get the most important lessons to inject into the AI prompt.
    Returns a text block that should be added to the system prompt."""

    try:
        async with async_session() as session:
            result = await session.execute(
                select(AILesson)
                .order_by(desc(AILesson.weight), desc(AILesson.updated_at))
                .limit(max_lessons)
            )
            lessons = result.scalars().all()

            if not lessons:
                return ""

            lessons_text = "\n\n## LESSONS FROM PAST CONVERSATIONS (VERY IMPORTANT — DO NOT REPEAT THESE MISTAKES)\n"
            lessons_text += "You have learned from previous customer interactions. Follow these rules strictly:\n\n"

            for i, lesson in enumerate(lessons, 1):
                lessons_text += f"{i}. **{lesson.category.upper()}** (importance: {'HIGH' if lesson.weight >= 3 else 'MEDIUM' if lesson.weight >= 2 else 'NORMAL'}):\n"
                lessons_text += f"   - NEVER do this: {lesson.ai_said[:100]}\n"
                lessons_text += f"   - Because: {lesson.customer_reaction[:100]}\n"
                lessons_text += f"   - INSTEAD do this: {lesson.better_alternative[:150]}\n"
                lessons_text += f"   - Remember: {lesson.lesson[:150]}\n\n"

            # Update times_applied
            for lesson in lessons:
                lesson.times_applied += 1
            await session.commit()

            return lessons_text

    except Exception as e:
        print(f"Get lessons error: {e}")
        return ""


async def trigger_learning_on_negative_signal(sender_id: str, signal_type: str, channel: str = ""):
    """Trigger learning when a negative signal is detected.
    signal_type: low_csat, lost_customer, negative_reaction, complaint, archived"""

    try:
        from app.models.conversation_state import ConversationState
        async with async_session() as session:
            result = await session.execute(
                select(ConversationState).where(ConversationState.sender_id == sender_id)
            )
            conv = result.scalar_one_or_none()
            if conv and conv.messages:
                import asyncio
                asyncio.create_task(
                    analyze_conversation_for_lessons(
                        messages=conv.messages,
                        outcome=signal_type,
                        channel=channel or conv.channel,
                        conversation_id=str(conv.id),
                    )
                )
    except Exception as e:
        print(f"Trigger learning error: {e}")
