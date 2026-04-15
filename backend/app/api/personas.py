"""Persona CRUD API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import Persona
from app.schemas.schemas import PersonaCreate, PersonaUpdate, PersonaResponse

router = APIRouter()


@router.get("/", response_model=List[PersonaResponse])
async def list_personas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).order_by(Persona.updated_at.desc()))
    return result.scalars().all()


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.post("/", response_model=PersonaResponse, status_code=201)
async def create_persona(data: PersonaCreate, db: AsyncSession = Depends(get_db)):
    persona = Persona(**data.model_dump())
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
async def update_persona(persona_id: str, data: PersonaUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)

    await db.flush()
    await db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    await db.delete(persona)


@router.post("/{persona_id}/generate-system-prompt")
async def generate_system_prompt(persona_id: str, db: AsyncSession = Depends(get_db)):
    """Generate an optimized system prompt from persona traits."""
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Build system prompt from persona attributes
    prompt_parts = []

    if persona.display_name:
        prompt_parts.append(f"You are {persona.display_name}.")
    if persona.role_title:
        prompt_parts.append(f"Your role is {persona.role_title}.")
    if persona.company_name:
        prompt_parts.append(f"You work at {persona.company_name}.")
    if persona.background_story:
        prompt_parts.append(f"\nBackground: {persona.background_story}")

    # Personality
    traits = []
    if persona.friendliness > 70:
        traits.append("very friendly and warm")
    elif persona.friendliness < 30:
        traits.append("businesslike and reserved")
    if persona.formality > 70:
        traits.append("highly formal")
    elif persona.formality < 30:
        traits.append("casual and relaxed")
    if persona.empathy > 70:
        traits.append("deeply empathetic")
    if persona.humor > 60:
        traits.append("with a good sense of humor")
    if persona.patience > 80:
        traits.append("extremely patient")
    if persona.directness > 70:
        traits.append("direct and to-the-point")
    elif persona.directness < 30:
        traits.append("diplomatic and tactful")

    if traits:
        prompt_parts.append(f"\nPersonality: You are {', '.join(traits)}.")

    if persona.speaking_style:
        prompt_parts.append(f"\nSpeaking style: {persona.speaking_style}")
    if persona.tone_description:
        prompt_parts.append(f"Tone: {persona.tone_description}")

    # Communication rules
    if persona.response_guidelines:
        rules = persona.response_guidelines
        prompt_parts.append("\nCommunication rules:")
        if rules.get("max_response_sentences"):
            prompt_parts.append(f"- Keep responses to {rules['max_response_sentences']} sentences or fewer")
        if rules.get("ask_one_question_at_a_time"):
            prompt_parts.append("- Ask only one question at a time")
        if rules.get("always_confirm_understanding"):
            prompt_parts.append("- Always confirm you understood the caller before moving on")
        if rules.get("use_caller_name"):
            prompt_parts.append("- Use the caller's name when known")
        if rules.get("avoid_jargon"):
            prompt_parts.append("- Avoid technical jargon, use simple language")

    # Forbidden phrases
    if persona.forbidden_phrases:
        prompt_parts.append(f"\nNever say: {', '.join(persona.forbidden_phrases)}")

    # Expertise
    if persona.expertise_areas:
        prompt_parts.append(f"\nYour areas of expertise: {', '.join(persona.expertise_areas)}")

    # Emotional intelligence
    if persona.emotional_responses:
        prompt_parts.append("\nEmotional response guidelines:")
        for situation, response in persona.emotional_responses.items():
            prompt_parts.append(f"- When caller is {situation}: {response}")

    generated_prompt = "\n".join(prompt_parts)

    # Save it
    persona.system_prompt = generated_prompt
    await db.flush()

    return {"system_prompt": generated_prompt}
