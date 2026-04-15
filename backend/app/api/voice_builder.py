"""Voice Builder — conversational persona builder that asks questions and extracts fields."""

import os
import uuid
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# In-memory session store
sessions = {}

QUESTIONS = [
    {"id": "q1", "field_group": "identity", "text": "What is the name and role of the persona? For example: 'Ayşe, Customer Success Manager'."},
    {"id": "q2", "field_group": "identity", "text": "What company does this persona work for?"},
    {"id": "q3", "field_group": "identity", "text": "Give a brief description of this persona — who are they and what do they do?"},
    {"id": "q4", "field_group": "identity", "text": "What is their background story? What experience do they have?"},
    {"id": "q5", "field_group": "identity", "text": "What are their areas of expertise? List a few topics they know well."},
    {"id": "q6", "field_group": "personality", "text": "How friendly should this persona be? Very warm, or more reserved?"},
    {"id": "q7", "field_group": "personality", "text": "Should they be formal or casual in conversation?"},
    {"id": "q8", "field_group": "personality", "text": "How empathetic and patient should they be?"},
    {"id": "q9", "field_group": "communication", "text": "What vocabulary level should they use — simple, professional, technical?"},
    {"id": "q10", "field_group": "communication", "text": "Describe their overall speaking style and tone."},
    {"id": "q11", "field_group": "phrases", "text": "Give me some example phrases this persona would typically say."},
    {"id": "q12", "field_group": "phrases", "text": "Are there any phrases or topics the persona should never say or discuss?"},
    {"id": "q13", "field_group": "emotional", "text": "How should the persona respond when a caller is frustrated or angry?"},
    {"id": "q14", "field_group": "safety", "text": "Are there any safety rules? Topics to never discuss, or promises to never make?"},
    {"id": "q15", "field_group": "custom", "text": "Any additional custom instructions for this persona?"},
]

FIELD_EXTRACTION_PROMPT = """You are a persona field extractor. Given a question about a persona and the user's answer, extract structured fields.

Question: {question}
Answer: {answer}
Question field group: {field_group}

Extract relevant persona fields from the answer. Return a JSON object with only the fields you can confidently extract.
Possible fields by group:
- identity: display_name, role_title, company_name, description, background_story, expertise_areas (array), language
- personality: friendliness (0-100), formality (0-100), assertiveness (0-100), empathy (0-100), humor (0-100), patience (0-100), enthusiasm (0-100), directness (0-100)
- communication: vocabulary_level (simple/professional/technical/academic), sentence_length (short/medium/long/varied), speaking_style, tone_description
- phrases: example_phrases (array), forbidden_phrases (array), custom_greetings (array), filler_words (array)
- emotional: emotional_responses (object with keys like frustrated_caller, angry_caller, etc.)
- safety: safety_rules (object with keys: never_discuss (array), never_promise (array), always_disclaim, pii_handling, out_of_scope_response)
- custom: custom_instructions

Return ONLY valid JSON, no explanation."""


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


@router.post("/start")
async def start_session(req: StartRequest):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "persona_id": req.persona_id,
        "language": req.language,
        "current_index": 0,
        "answers": {},
    }
    return {
        "session_id": session_id,
        "first_question": QUESTIONS[0],
        "current_step": 1,
        "total_questions": len(QUESTIONS),
    }


async def extract_fields(question_text: str, answer: str, field_group: str) -> dict:
    if not OPENAI_API_KEY:
        return {}
    prompt = FIELD_EXTRACTION_PROMPT.format(
        question=question_text, answer=answer, field_group=field_group
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
    if resp.status_code != 200:
        return {}
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def get_next(session: dict):
    idx = session["current_index"]
    if idx >= len(QUESTIONS):
        return None, True
    return QUESTIONS[idx], False


@router.post("/answer")
async def process_answer(req: AnswerRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the question
    q = next((q for q in QUESTIONS if q["id"] == req.question_id), None)
    if not q:
        raise HTTPException(status_code=400, detail="Unknown question")

    # Extract fields from answer and flatten any nested group keys
    raw = await extract_fields(q["text"], req.transcript, q["field_group"])
    extracted = {}
    for key, value in raw.items():
        if isinstance(value, dict) and key in ("identity", "personality", "communication", "phrases", "emotional", "safety", "custom"):
            extracted.update(value)
        else:
            extracted[key] = value
    session["answers"][req.question_id] = req.transcript
    session["current_index"] += 1

    next_q, completed = get_next(session)

    result = {
        "extracted_fields": extracted,
        "clarification_needed": False,
        "completed": completed,
        "current_step": session["current_index"] + 1,
    }
    if not completed and next_q:
        result["next_question"] = next_q
    return result


@router.post("/skip")
async def skip_question(req: SkipRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["current_index"] += 1
    next_q, completed = get_next(session)

    result = {
        "completed": completed,
        "current_step": session["current_index"] + 1,
    }
    if not completed and next_q:
        result["next_question"] = next_q
    return result
