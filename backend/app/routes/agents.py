from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Agent, Persona
from app.schemas import (
    AgentCreate, AgentUpdate, AgentResponse,
    AssignPersonaRequest, AgentFullConfig, PersonaResponse,
)
from app.prompt_builder import build_system_prompt

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/assign-persona", response_model=AgentResponse)
async def assign_persona(agent_id: str, data: AssignPersonaRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Verify persona exists
    persona_result = await db.execute(select(Persona).where(Persona.id == data.persona_id))
    if not persona_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Persona not found")

    agent.persona_id = data.persona_id
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}/full-config", response_model=AgentFullConfig)
async def get_full_config(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    persona = None
    if agent.persona_id:
        persona_result = await db.execute(select(Persona).where(Persona.id == agent.persona_id))
        persona_obj = persona_result.scalar_one_or_none()
        if persona_obj:
            # Auto-generate prompt if not set
            if not persona_obj.system_prompt:
                persona_obj.system_prompt = build_system_prompt(persona_obj)
                await db.commit()
                await db.refresh(persona_obj)
            persona = PersonaResponse.model_validate(persona_obj)

    agent_data = AgentResponse.model_validate(agent).model_dump()
    agent_data["persona"] = persona
    return AgentFullConfig(**agent_data)
