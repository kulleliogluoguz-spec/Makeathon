from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Persona
from app.schemas import PersonaCreate, PersonaUpdate, PersonaResponse
from app.prompt_builder import build_system_prompt

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("/", response_model=list[PersonaResponse])
async def list_personas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).order_by(Persona.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=PersonaResponse, status_code=201)
async def create_persona(data: PersonaCreate, db: AsyncSession = Depends(get_db)):
    persona = Persona(**data.model_dump())
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return persona


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
async def update_persona(persona_id: str, data: PersonaUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)

    await db.commit()
    await db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=200)
async def delete_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    from app.models import Agent

    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Nullify any agents referencing this persona
    agents_result = await db.execute(select(Agent).where(Agent.persona_id == persona_id))
    for agent in agents_result.scalars().all():
        agent.persona_id = None

    await db.delete(persona)
    await db.commit()
    return {"detail": "Persona deleted", "agents_unlinked": True}


@router.post("/{persona_id}/generate-prompt")
async def generate_prompt(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    prompt = build_system_prompt(persona)
    persona.system_prompt = prompt
    await db.commit()
    await db.refresh(persona)
    return {"system_prompt": prompt, "word_count": len(prompt.split())}


@router.post("/{persona_id}/preview-prompt")
async def preview_prompt(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    prompt = build_system_prompt(persona)
    # Preview only — do NOT save
    return {"system_prompt": prompt, "word_count": len(prompt.split())}


@router.post("/{persona_id}/duplicate", response_model=PersonaResponse, status_code=201)
async def duplicate_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    new_persona = Persona(
        name=f"{persona.name} (Copy)",
        display_name=persona.display_name,
        role_title=persona.role_title,
        company_name=persona.company_name,
        description=persona.description,
        avatar_url=persona.avatar_url,
        friendliness=persona.friendliness,
        formality=persona.formality,
        assertiveness=persona.assertiveness,
        empathy=persona.empathy,
        humor=persona.humor,
        patience=persona.patience,
        enthusiasm=persona.enthusiasm,
        directness=persona.directness,
        speaking_style=persona.speaking_style,
        vocabulary_level=persona.vocabulary_level,
        sentence_length=persona.sentence_length,
        tone_description=persona.tone_description,
        language=persona.language,
        example_phrases=deepcopy(persona.example_phrases) if persona.example_phrases else [],
        forbidden_phrases=deepcopy(persona.forbidden_phrases) if persona.forbidden_phrases else [],
        custom_greetings=deepcopy(persona.custom_greetings) if persona.custom_greetings else [],
        filler_words=deepcopy(persona.filler_words) if persona.filler_words else [],
        expertise_areas=deepcopy(persona.expertise_areas) if persona.expertise_areas else [],
        background_story=persona.background_story,
        response_guidelines=deepcopy(persona.response_guidelines) if persona.response_guidelines else {},
        emotional_responses=deepcopy(persona.emotional_responses) if persona.emotional_responses else {},
        escalation_triggers=deepcopy(persona.escalation_triggers) if persona.escalation_triggers else [],
        safety_rules=deepcopy(persona.safety_rules) if persona.safety_rules else {},
        custom_instructions=persona.custom_instructions,
        system_prompt=persona.system_prompt,
    )
    db.add(new_persona)
    await db.commit()
    await db.refresh(new_persona)
    return new_persona
