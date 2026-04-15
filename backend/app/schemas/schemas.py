"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────

class AgentStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class NodeTypeEnum(str, Enum):
    START = "start"
    END = "end"
    AI_PROMPT = "ai_prompt"
    QUESTION = "question"
    CONDITION = "condition"
    TRANSFER = "transfer"
    WEBHOOK = "webhook"
    KNOWLEDGE_LOOKUP = "knowledge_lookup"
    SET_VARIABLE = "set_variable"
    WAIT = "wait"
    PLAY_AUDIO = "play_audio"
    COLLECT_INPUT = "collect_input"
    API_CALL = "api_call"
    FUNCTION_CALL = "function_call"


# ─── Persona Schemas ──────────────────────────────────────────────────

class PersonaCreate(BaseModel):
    name: str
    description: str = ""
    display_name: str = ""
    role_title: str = ""
    company_name: str = ""
    avatar_url: str = ""
    friendliness: int = Field(70, ge=0, le=100)
    formality: int = Field(50, ge=0, le=100)
    assertiveness: int = Field(50, ge=0, le=100)
    empathy: int = Field(70, ge=0, le=100)
    humor: int = Field(30, ge=0, le=100)
    patience: int = Field(80, ge=0, le=100)
    enthusiasm: int = Field(60, ge=0, le=100)
    directness: int = Field(50, ge=0, le=100)
    speaking_style: str = ""
    vocabulary_level: str = "professional"
    sentence_length: str = "medium"
    tone_description: str = ""
    example_phrases: List[str] = []
    forbidden_phrases: List[str] = []
    custom_greetings: List[str] = []
    expertise_areas: List[str] = []
    background_story: str = ""
    system_prompt: str = ""
    response_guidelines: Dict[str, Any] = {}
    emotional_responses: Dict[str, str] = {}
    escalation_triggers: List[Dict[str, Any]] = []


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    display_name: Optional[str] = None
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None
    friendliness: Optional[int] = None
    formality: Optional[int] = None
    assertiveness: Optional[int] = None
    empathy: Optional[int] = None
    humor: Optional[int] = None
    patience: Optional[int] = None
    enthusiasm: Optional[int] = None
    directness: Optional[int] = None
    speaking_style: Optional[str] = None
    vocabulary_level: Optional[str] = None
    sentence_length: Optional[str] = None
    tone_description: Optional[str] = None
    example_phrases: Optional[List[str]] = None
    forbidden_phrases: Optional[List[str]] = None
    custom_greetings: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    background_story: Optional[str] = None
    system_prompt: Optional[str] = None
    response_guidelines: Optional[Dict[str, Any]] = None
    emotional_responses: Optional[Dict[str, str]] = None
    escalation_triggers: Optional[List[Dict[str, Any]]] = None


class PersonaResponse(PersonaCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Agent Schemas ────────────────────────────────────────────────────

class VoiceSettings(BaseModel):
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.0


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    tags: List[str] = []
    persona_id: Optional[str] = None
    voice_provider: str = "elevenlabs"
    voice_id: str = "rachel"
    voice_model: str = "eleven_turbo_v2"
    voice_settings: VoiceSettings = VoiceSettings()
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    first_message: str = ""
    end_call_message: str = ""
    max_conversation_duration: int = 600
    silence_timeout: int = 10
    interruption_threshold: float = 0.5
    enable_backchannel: bool = True
    backchannel_words: List[str] = ["evet", "anlıyorum", "tabii", "devam edin"]
    language: str = "tr"
    fallback_language: str = "en"


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatusEnum] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    persona_id: Optional[str] = None
    active_workflow_id: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    voice_model: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    first_message: Optional[str] = None
    end_call_message: Optional[str] = None
    max_conversation_duration: Optional[int] = None
    silence_timeout: Optional[int] = None
    interruption_threshold: Optional[float] = None
    enable_backchannel: Optional[bool] = None
    backchannel_words: Optional[List[str]] = None
    language: Optional[str] = None
    fallback_language: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    category: str
    tags: List[str]
    persona_id: Optional[str]
    active_workflow_id: Optional[str]
    voice_provider: str
    voice_id: str
    voice_model: str
    voice_settings: Dict[str, Any]
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    first_message: str
    end_call_message: str
    max_conversation_duration: int
    silence_timeout: int
    interruption_threshold: float
    enable_backchannel: bool
    backchannel_words: List[str]
    language: str
    fallback_language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Workflow Schemas ─────────────────────────────────────────────────

class WorkflowNodeCreate(BaseModel):
    id: Optional[str] = None
    node_type: NodeTypeEnum
    label: str = ""
    description: str = ""
    position_x: float = 0
    position_y: float = 0
    config: Dict[str, Any] = {}


class WorkflowNodeUpdate(BaseModel):
    node_type: Optional[NodeTypeEnum] = None
    label: Optional[str] = None
    description: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowNodeResponse(BaseModel):
    id: str
    workflow_id: str
    node_type: str
    label: str
    description: str
    position_x: float
    position_y: float
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowEdgeCreate(BaseModel):
    id: Optional[str] = None
    source_node_id: str
    target_node_id: str
    label: str = ""
    condition: Dict[str, Any] = {}
    edge_type: str = "default"
    animated: bool = False


class WorkflowEdgeResponse(BaseModel):
    id: str
    workflow_id: str
    source_node_id: str
    target_node_id: str
    label: str
    condition: Dict[str, Any]
    edge_type: str
    animated: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    agent_id: str
    name: str
    description: str = ""
    variables: Dict[str, Any] = {}
    nodes: List[WorkflowNodeCreate] = []
    edges: List[WorkflowEdgeCreate] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    variables: Optional[Dict[str, Any]] = None
    viewport: Optional[Dict[str, Any]] = None
    nodes: Optional[List[WorkflowNodeCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None


class WorkflowResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    description: str
    is_active: bool
    version: int
    viewport: Dict[str, Any]
    variables: Dict[str, Any]
    nodes: List[WorkflowNodeResponse] = []
    edges: List[WorkflowEdgeResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Conversation Schemas ─────────────────────────────────────────────

class ConversationCreate(BaseModel):
    agent_id: str
    caller_phone: str = ""
    caller_name: str = ""
    caller_email: str = ""


class ConversationMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    audio_url: str
    node_id: Optional[str]
    intent_detected: str
    entities_extracted: Dict[str, Any]
    confidence: Optional[float]
    latency_ms: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    agent_id: str
    caller_phone: str
    caller_name: str
    caller_email: str
    status: str
    current_node_id: Optional[str]
    variables: Dict[str, Any]
    duration_seconds: int
    total_messages: int
    sentiment_score: Optional[float]
    summary: str
    resolution: str
    company_profile: Dict[str, Any]
    started_at: datetime
    ended_at: Optional[datetime]
    messages: List[ConversationMessageResponse] = []

    class Config:
        from_attributes = True


# ─── Company Schemas ──────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    country: str = ""
    city: str = ""
    sector: str = ""
    sub_sector: str = ""
    description: str = ""
    website: str = ""
    phone: str = ""
    email: str = ""
    employee_count_range: str = ""
    annual_revenue_range: str = ""
    founded_year: Optional[int] = None
    business_type: str = ""
    services: List[str] = []
    products: List[str] = []
    target_customers: List[str] = []
    competitive_advantages: List[str] = []
    pain_points: List[str] = []
    goals: List[str] = []
    current_tools: List[str] = []
    source_conversation_id: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_count_range: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    founded_year: Optional[int] = None
    business_type: Optional[str] = None
    services: Optional[List[str]] = None
    products: Optional[List[str]] = None
    target_customers: Optional[List[str]] = None
    competitive_advantages: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    current_tools: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[List[str]] = None


class CompanyResponse(CompanyCreate):
    id: str
    ai_summary: str
    ai_recommendations: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Knowledge Base Schemas ───────────────────────────────────────────

class KnowledgeEntryCreate(BaseModel):
    agent_id: str
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []
    extra_metadata: Dict[str, Any] = {}


class KnowledgeEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeEntryResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    extra_metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
