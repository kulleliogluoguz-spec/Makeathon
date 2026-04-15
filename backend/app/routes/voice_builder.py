import json
import os
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.voice_interview import INTERVIEW_QUESTIONS, get_question

router = APIRouter(prefix="/voice-builder", tags=["voice-builder"])

# In-memory session store
_sessions: dict[str, dict] = {}

# LLM config from env
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1-nano")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

SYSTEM_PROMPT = (
    "You are a data extraction assistant. The user is describing an AI agent's persona "
    "through a voice conversation. Extract the requested fields from their answer. "
    "Always respond with valid JSON only, no other text, no markdown fences. "
    "If a field cannot be determined from the answer, omit it from the JSON. "
    "For personality traits, use 0-100 scale where 0=not at all, 50=moderate, 100=extremely."
)


async def _call_llm(user_message: str) -> str:
    """Call LLM to extract fields. Uses OpenAI (gpt-4.1-nano) by default, Ollama as fallback."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if OPENAI_API_KEY:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        else:
            # Ollama fallback
            ollama_model = os.environ.get("VOICE_BUILDER_LLM_MODEL", "qwen3:8b")
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": f"[SYSTEM]{SYSTEM_PROMPT}[/SYSTEM]\n\n{user_message}",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")


async def extract_fields_from_answer(transcript: str, extraction_prompt: str, context: dict) -> dict:
    """Call LLM to extract structured persona fields from the user's answer."""
    context_str = json.dumps(context, ensure_ascii=False) if context else "{}"
    user_message = (
        f"Context - fields already collected: {context_str}\n\n"
        f'User said: "{transcript}"\n\n'
        f"{extraction_prompt}"
    )

    try:
        raw = await _call_llm(user_message)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)
    except (json.JSONDecodeError, httpx.HTTPError, KeyError):
        return {}


def _find_next_unanswered(current_index: int, completed_fields: set) -> int | None:
    """Find next question whose target fields haven't all been answered."""
    for i in range(current_index, len(INTERVIEW_QUESTIONS)):
        q = INTERVIEW_QUESTIONS[i]
        if not all(f in completed_fields for f in q["target_fields"]):
            return i
    return None


# --- Schemas ---

class StartRequest(BaseModel):
    persona_id: str
    language: str = "en"


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    transcript: str


class SkipRequest(BaseModel):
    session_id: str
    question_id: str


# --- Endpoints ---

@router.post("/start")
async def start_session(data: StartRequest):
    session_id = str(uuid.uuid4())
    context = {}
    first_q = get_question(0, context, data.language)

    _sessions[session_id] = {
        "persona_id": data.persona_id,
        "language": data.language,
        "current_index": 0,
        "context": context,
        "completed_fields": set(),
    }

    return {
        "session_id": session_id,
        "first_question": {
            "id": first_q["id"],
            "text": first_q["text"],
            "field_group": first_q["field_group"],
            "target_fields": first_q["target_fields"],
        },
        "total_questions": len(INTERVIEW_QUESTIONS),
        "current_step": 1,
    }


@router.post("/answer")
async def process_answer(data: AnswerRequest):
    session = _sessions.get(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the question
    question = None
    for q in INTERVIEW_QUESTIONS:
        if q["id"] == data.question_id:
            question = q
            break
    if not question:
        raise HTTPException(status_code=400, detail="Invalid question_id")

    # Extract fields via LLM
    extracted = await extract_fields_from_answer(
        data.transcript, question["extraction_prompt"], session["context"]
    )

    confidence = 0.9 if extracted else 0.3
    clarification_needed = len(extracted) == 0

    if clarification_needed:
        display_name = session["context"].get("display_name", "your agent")
        return {
            "extracted_fields": {},
            "confidence": confidence,
            "clarification_needed": True,
            "clarification_question": {
                "id": f"{data.question_id}_retry",
                "text": "I didn't quite catch that. Could you rephrase your answer?",
                "field_group": question["field_group"],
                "target_fields": question["target_fields"],
            },
            "current_step": session["current_index"] + 1,
            "total_questions": len(INTERVIEW_QUESTIONS),
        }

    # Update context with extracted fields (flatten nested dicts for context)
    for key, val in extracted.items():
        if isinstance(val, dict):
            session["context"][key] = val
        elif isinstance(val, list):
            session["context"][key] = val
        else:
            session["context"][key] = val
        session["completed_fields"].add(key)

    # Also mark individual target fields as completed
    for f in question["target_fields"]:
        if f in extracted:
            session["completed_fields"].add(f)

    # Advance to next unanswered question
    next_index = _find_next_unanswered(session["current_index"] + 1, session["completed_fields"])

    if next_index is not None:
        session["current_index"] = next_index
        next_q = get_question(next_index, session["context"], session["language"])
        return {
            "extracted_fields": extracted,
            "confidence": confidence,
            "clarification_needed": False,
            "next_question": {
                "id": next_q["id"],
                "text": next_q["text"],
                "field_group": next_q["field_group"],
                "target_fields": next_q["target_fields"],
            },
            "current_step": next_index + 1,
            "total_questions": len(INTERVIEW_QUESTIONS),
        }
    else:
        # All done
        return {
            "extracted_fields": extracted,
            "confidence": confidence,
            "clarification_needed": False,
            "next_question": None,
            "current_step": len(INTERVIEW_QUESTIONS),
            "total_questions": len(INTERVIEW_QUESTIONS),
            "completed": True,
        }


@router.post("/skip")
async def skip_question(data: SkipRequest):
    session = _sessions.get(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    next_index = _find_next_unanswered(session["current_index"] + 1, session["completed_fields"])

    if next_index is not None:
        session["current_index"] = next_index
        next_q = get_question(next_index, session["context"], session["language"])
        return {
            "next_question": {
                "id": next_q["id"],
                "text": next_q["text"],
                "field_group": next_q["field_group"],
                "target_fields": next_q["target_fields"],
            },
            "current_step": next_index + 1,
            "total_questions": len(INTERVIEW_QUESTIONS),
        }
    else:
        return {
            "next_question": None,
            "current_step": len(INTERVIEW_QUESTIONS),
            "total_questions": len(INTERVIEW_QUESTIONS),
            "completed": True,
        }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "persona_id": session["persona_id"],
        "current_step": session["current_index"] + 1,
        "total_questions": len(INTERVIEW_QUESTIONS),
        "completed_fields": list(session["completed_fields"]),
        "remaining_questions": len(INTERVIEW_QUESTIONS) - session["current_index"],
    }
