from datetime import datetime
from pydantic import BaseModel, Field


# --- Persona ---

class PersonaCreate(BaseModel):
    name: str = "New Persona"
    display_name: str | None = None
    role_title: str | None = None
    company_name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    friendliness: int = 70
    formality: int = 50
    assertiveness: int = 50
    empathy: int = 70
    humor: int = 30
    patience: int = 80
    enthusiasm: int = 60
    directness: int = 50
    speaking_style: str | None = None
    vocabulary_level: str = "professional"
    sentence_length: str = "medium"
    tone_description: str | None = None
    language: str = "tr"
    example_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    custom_greetings: list[str] = Field(default_factory=list)
    filler_words: list[str] = Field(default_factory=list)
    expertise_areas: list[str] = Field(default_factory=list)
    background_story: str | None = None
    response_guidelines: dict | None = None
    emotional_responses: dict | None = None
    escalation_triggers: list = Field(default_factory=list)
    safety_rules: dict | None = None
    custom_instructions: str | None = None
    system_prompt: str | None = None


class PersonaUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    role_title: str | None = None
    company_name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    friendliness: int | None = None
    formality: int | None = None
    assertiveness: int | None = None
    empathy: int | None = None
    humor: int | None = None
    patience: int | None = None
    enthusiasm: int | None = None
    directness: int | None = None
    speaking_style: str | None = None
    vocabulary_level: str | None = None
    sentence_length: str | None = None
    tone_description: str | None = None
    language: str | None = None
    example_phrases: list[str] | None = None
    forbidden_phrases: list[str] | None = None
    custom_greetings: list[str] | None = None
    filler_words: list[str] | None = None
    expertise_areas: list[str] | None = None
    background_story: str | None = None
    response_guidelines: dict | None = None
    emotional_responses: dict | None = None
    escalation_triggers: list | None = None
    safety_rules: dict | None = None
    custom_instructions: str | None = None
    system_prompt: str | None = None


class PersonaResponse(BaseModel):
    id: str
    name: str
    display_name: str | None = None
    role_title: str | None = None
    company_name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    friendliness: int
    formality: int
    assertiveness: int
    empathy: int
    humor: int
    patience: int
    enthusiasm: int
    directness: int
    speaking_style: str | None = None
    vocabulary_level: str
    sentence_length: str
    tone_description: str | None = None
    language: str
    example_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    custom_greetings: list[str] = Field(default_factory=list)
    filler_words: list[str] = Field(default_factory=list)
    expertise_areas: list[str] = Field(default_factory=list)
    background_story: str | None = None
    response_guidelines: dict | None = None
    emotional_responses: dict | None = None
    escalation_triggers: list = Field(default_factory=list)
    safety_rules: dict | None = None
    custom_instructions: str | None = None
    system_prompt: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Agent ---

class AgentCreate(BaseModel):
    name: str = "New Agent"
    description: str | None = None
    status: str = "draft"
    persona_id: str | None = None
    language: str = "tr"
    voice_provider: str = "elevenlabs"
    voice_id: str | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    first_message: str | None = None
    end_call_message: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    persona_id: str | None = None
    language: str | None = None
    voice_provider: str | None = None
    voice_id: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    llm_max_tokens: int | None = None
    first_message: str | None = None
    end_call_message: str | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str
    persona_id: str | None = None
    language: str
    voice_provider: str
    voice_id: str | None = None
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    first_message: str | None = None
    end_call_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignPersonaRequest(BaseModel):
    persona_id: str


class AgentFullConfig(AgentResponse):
    persona: PersonaResponse | None = None
