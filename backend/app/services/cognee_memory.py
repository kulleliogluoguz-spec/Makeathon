"""Cognee integration — persistent AI memory using knowledge graph."""

import os
import asyncio
import cognee
from dotenv import load_dotenv

load_dotenv()

# Set Cognee's LLM key from our OpenAI key
os.environ["LLM_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

COGNEE_INITIALIZED = False


async def init_cognee():
    """Initialize Cognee (call once on startup)."""
    global COGNEE_INITIALIZED
    if COGNEE_INITIALIZED:
        return
    try:
        COGNEE_INITIALIZED = True
        print("Cognee memory initialized")
    except Exception as e:
        print(f"Cognee init error: {e}")


async def remember_lesson(lesson_text: str, session_id: str = "sales_lessons"):
    """Store a lesson learned from a conversation in Cognee's knowledge graph."""
    try:
        await init_cognee()
        await cognee.remember(lesson_text, session_id=session_id)
        print(f"Cognee: Lesson remembered: {lesson_text[:80]}...")
    except Exception as e:
        print(f"Cognee remember error: {e}")


async def remember_conversation(conversation_summary: str, customer_name: str, outcome: str, session_id: str = "conversations"):
    """Store a conversation summary in Cognee's knowledge graph."""
    try:
        await init_cognee()
        memory_text = f"Conversation with {customer_name}. Outcome: {outcome}. Summary: {conversation_summary}"
        await cognee.remember(memory_text, session_id=session_id)
        print(f"Cognee: Conversation remembered: {customer_name}")
    except Exception as e:
        print(f"Cognee remember conversation error: {e}")


async def remember_customer(customer_info: str, session_id: str = "customers"):
    """Store customer information in Cognee's knowledge graph."""
    try:
        await init_cognee()
        await cognee.remember(customer_info, session_id=session_id)
    except Exception as e:
        print(f"Cognee remember customer error: {e}")


async def recall_lessons(query: str = "What mistakes should the AI avoid in sales conversations?", max_results: int = 10) -> str:
    """Recall relevant lessons from Cognee's knowledge graph to inject into AI prompt."""
    try:
        await init_cognee()
        results = await cognee.recall(query)

        if not results:
            return ""

        lessons_text = "\n\n## AI MEMORY — LESSONS FROM PAST CONVERSATIONS (from Cognee Knowledge Graph)\n"
        lessons_text += "You have persistent memory of past interactions. Apply these lessons:\n\n"

        for i, result in enumerate(results[:max_results], 1):
            if hasattr(result, 'text'):
                text = result.text
            elif isinstance(result, dict):
                text = result.get('text', result.get('content', str(result)))
            else:
                text = str(result)

            if text and len(text) > 10:
                lessons_text += f"{i}. {text}\n"

        return lessons_text

    except Exception as e:
        print(f"Cognee recall error: {e}")
        return ""


async def recall_customer_context(customer_name: str) -> str:
    """Recall any past interactions with this customer."""
    try:
        await init_cognee()
        results = await cognee.recall(f"What do we know about {customer_name}?", session_id="customers")

        if not results:
            return ""

        context = "\n## CUSTOMER HISTORY (from Cognee Memory)\n"
        for result in results[:5]:
            if hasattr(result, 'text'):
                context += f"- {result.text}\n"
            elif isinstance(result, dict):
                context += f"- {result.get('text', str(result))}\n"
            else:
                context += f"- {str(result)}\n"

        return context

    except Exception as e:
        print(f"Cognee recall customer error: {e}")
        return ""


async def forget_all():
    """Clear all Cognee memory (for testing)."""
    try:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        print("Cognee: All memory cleared")
    except Exception as e:
        print(f"Cognee forget error: {e}")
