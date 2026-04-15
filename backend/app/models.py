import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Integer, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_id():
    return str(uuid.uuid4())


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="New Persona")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Personality Traits (0-100)
    friendliness: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    formality: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    assertiveness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    empathy: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    humor: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    patience: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    enthusiasm: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    directness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Communication Style
    speaking_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    vocabulary_level: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    sentence_length: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    tone_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="tr")

    # Phrases (JSON lists)
    example_phrases: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    forbidden_phrases: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    custom_greetings: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    filler_words: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Knowledge & Expertise
    expertise_areas: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    background_story: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response Rules (JSON dict)
    response_guidelines: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "max_response_sentences": 3,
        "ask_one_question_at_a_time": True,
        "always_confirm_understanding": True,
        "use_caller_name": True,
        "avoid_jargon": True,
        "end_with_question": True,
        "acknowledge_before_responding": True,
    })

    # Emotional Intelligence (JSON dict)
    emotional_responses: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "frustrated_caller": "",
        "confused_caller": "",
        "happy_caller": "",
        "angry_caller": "",
        "silent_caller": "",
        "impatient_caller": "",
        "sad_caller": "",
    })

    # Escalation Rules (JSON list of dicts)
    escalation_triggers: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Safety & Boundaries (JSON dict)
    safety_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "never_discuss": [],
        "never_promise": [],
        "always_disclaim": "",
        "pii_handling": "",
        "out_of_scope_response": "",
    })

    # Voice Configuration (ElevenLabs)
    voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_preview_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voice_model: Mapped[str] = mapped_column(String(100), nullable=False, default="eleven_turbo_v2")
    voice_stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    voice_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    voice_style: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    voice_speed: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Custom Instructions
    custom_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generated System Prompt
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="New Agent")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    persona_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="tr")

    # Voice settings
    voice_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="elevenlabs")
    voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # LLM settings
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o")
    llm_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    llm_max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=500)

    # Messages
    first_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_call_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
