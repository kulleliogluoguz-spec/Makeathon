"""Database models for the VoiceAgent platform."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


def generate_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────

class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class NodeType(str, enum.Enum):
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


class VoiceProvider(str, enum.Enum):
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    LOCAL = "local"


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


# ─── Agent ────────────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.DRAFT)
    category = Column(String(100), default="general")
    tags = Column(JSON, default=list)

    # Persona reference
    persona_id = Column(String, ForeignKey("personas.id"), nullable=True)

    # Active workflow
    active_workflow_id = Column(String, nullable=True)

    # Voice settings
    voice_provider = Column(SQLEnum(VoiceProvider), default=VoiceProvider.ELEVENLABS)
    voice_id = Column(String(255), default="rachel")
    voice_model = Column(String(255), default="eleven_turbo_v2")
    voice_settings = Column(JSON, default=lambda: {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
        "speed": 1.0,
    })

    # LLM settings
    llm_provider = Column(SQLEnum(LLMProvider), default=LLMProvider.OPENAI)
    llm_model = Column(String(255), default="gpt-4o")
    llm_temperature = Column(Float, default=0.7)
    llm_max_tokens = Column(Integer, default=500)

    # Behavior settings
    first_message = Column(Text, default="")
    end_call_message = Column(Text, default="")
    max_conversation_duration = Column(Integer, default=600)  # seconds
    silence_timeout = Column(Integer, default=10)  # seconds
    interruption_threshold = Column(Float, default=0.5)
    enable_backchannel = Column(Boolean, default=True)
    backchannel_words = Column(JSON, default=lambda: ["evet", "anlıyorum", "tabii", "devam edin"])

    # Language
    language = Column(String(10), default="tr")
    fallback_language = Column(String(10), default="en")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    persona = relationship("Persona", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="agent", cascade="all, delete-orphan")
    knowledge_entries = relationship("KnowledgeEntry", back_populates="agent", cascade="all, delete-orphan")


# ─── Persona ──────────────────────────────────────────────────────────

class Persona(Base):
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")

    # Identity
    display_name = Column(String(255), default="")
    role_title = Column(String(255), default="")
    company_name = Column(String(255), default="")
    avatar_url = Column(String(500), default="")

    # Personality traits (0-100 scale)
    friendliness = Column(Integer, default=70)
    formality = Column(Integer, default=50)
    assertiveness = Column(Integer, default=50)
    empathy = Column(Integer, default=70)
    humor = Column(Integer, default=30)
    patience = Column(Integer, default=80)
    enthusiasm = Column(Integer, default=60)
    directness = Column(Integer, default=50)

    # Communication style
    speaking_style = Column(Text, default="")  # e.g., "Professional yet warm, uses Turkish business etiquette"
    vocabulary_level = Column(String(50), default="professional")  # simple | professional | technical | academic
    sentence_length = Column(String(50), default="medium")  # short | medium | long | varied
    tone_description = Column(Text, default="")
    example_phrases = Column(JSON, default=list)  # ["Nasıl yardımcı olabilirim?", ...]
    forbidden_phrases = Column(JSON, default=list)  # phrases to never use
    custom_greetings = Column(JSON, default=list)

    # Knowledge & expertise
    expertise_areas = Column(JSON, default=list)
    background_story = Column(Text, default="")

    # Behavioral rules
    system_prompt = Column(Text, default="")
    response_guidelines = Column(JSON, default=lambda: {
        "max_response_sentences": 3,
        "ask_one_question_at_a_time": True,
        "always_confirm_understanding": True,
        "use_caller_name": True,
        "avoid_jargon": True,
    })

    # Emotional intelligence
    emotional_responses = Column(JSON, default=lambda: {
        "frustrated_caller": "Acknowledge frustration, apologize, focus on solution",
        "confused_caller": "Simplify language, repeat key points, offer examples",
        "happy_caller": "Match positive energy, reinforce good experience",
        "angry_caller": "Stay calm, validate feelings, offer immediate escalation",
        "silent_caller": "Gently prompt, offer to rephrase, check if still there",
    })

    # Escalation rules
    escalation_triggers = Column(JSON, default=lambda: [
        {"trigger": "repeated_confusion", "threshold": 3, "action": "transfer_to_human"},
        {"trigger": "explicit_request", "action": "transfer_to_human"},
        {"trigger": "sensitive_topic", "keywords": ["complaint", "legal", "refund"], "action": "transfer_to_supervisor"},
    ])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agents = relationship("Agent", back_populates="persona")


# ─── Workflow ─────────────────────────────────────────────────────────

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=False)
    version = Column(Integer, default=1)

    # Visual editor state (React Flow compatible)
    viewport = Column(JSON, default=lambda: {"x": 0, "y": 0, "zoom": 1})

    # Workflow variables (global context)
    variables = Column(JSON, default=lambda: {
        "company_name": "",
        "caller_name": "",
        "caller_phone": "",
        "caller_email": "",
        "issue_type": "",
        "resolution_status": "",
    })

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)

    # Node identity
    node_type = Column(SQLEnum(NodeType), nullable=False)
    label = Column(String(255), default="")
    description = Column(Text, default="")

    # Visual position (React Flow)
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)

    # Node-specific config (varies by type)
    config = Column(JSON, default=dict)
    """
    Config examples by node_type:

    AI_PROMPT:
        {"prompt": "Greet the caller and ask their name",
         "save_response_to": "caller_name",
         "max_retries": 2}

    QUESTION:
        {"question_text": "Hangi sektörde faaliyet gösteriyorsunuz?",
         "expected_type": "text",  # text | number | yes_no | choice
         "choices": ["Teknoloji", "Sağlık", "Eğitim", ...],
         "save_to_variable": "sector",
         "retry_prompt": "Anlayamadım, tekrar eder misiniz?",
         "max_retries": 3}

    CONDITION:
        {"conditions": [
            {"variable": "sector", "operator": "equals", "value": "Teknoloji", "next_node": "tech_branch"},
            {"variable": "sector", "operator": "equals", "value": "Sağlık", "next_node": "health_branch"},
         ],
         "default_next": "general_branch"}

    TRANSFER:
        {"transfer_to": "human_agent",
         "transfer_message": "Sizi bir uzmanımıza bağlıyorum",
         "department": "sales",
         "priority": "high"}

    WEBHOOK:
        {"url": "https://api.example.com/webhook",
         "method": "POST",
         "headers": {},
         "body_template": {"caller": "{{caller_name}}", "issue": "{{issue_type}}"},
         "save_response_to": "webhook_result",
         "timeout": 5}

    KNOWLEDGE_LOOKUP:
        {"query_variable": "caller_question",
         "knowledge_base_ids": ["kb_1"],
         "max_results": 3,
         "save_to_variable": "answer"}

    SET_VARIABLE:
        {"variable": "issue_resolved",
         "value": "true",
         "value_type": "static"}  # static | from_variable | expression

    COLLECT_INPUT:
        {"prompt": "Lütfen telefon numaranızı söyleyin",
         "input_type": "phone",  # phone | email | number | date | free_text
         "validation_regex": "^\\+?[0-9]{10,14}$",
         "save_to_variable": "caller_phone",
         "error_message": "Geçersiz telefon numarası"}

    API_CALL:
        {"url": "https://api.example.com/data",
         "method": "GET",
         "auth_type": "bearer",  # none | bearer | api_key | basic
         "auth_token_variable": "api_token",
         "save_to_variable": "api_data"}

    FUNCTION_CALL:
        {"function_name": "calculate_price",
         "parameters": {"product": "{{product_name}}", "quantity": "{{quantity}}"},
         "save_to_variable": "price_result"}

    PLAY_AUDIO:
        {"audio_url": "https://example.com/audio.mp3",
         "wait_for_completion": true}

    WAIT:
        {"duration_seconds": 2,
         "message": "Bir saniye lütfen, bilgilerinizi kontrol ediyorum..."}
    """

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)

    source_node_id = Column(String, ForeignKey("workflow_nodes.id"), nullable=False)
    target_node_id = Column(String, ForeignKey("workflow_nodes.id"), nullable=False)

    # Edge label (for conditional branches)
    label = Column(String(255), default="")
    condition = Column(JSON, default=dict)
    """
    Condition example:
    {"variable": "issue_type", "operator": "equals", "value": "technical"}
    Operators: equals, not_equals, contains, greater_than, less_than, is_empty, is_not_empty, matches_regex
    """

    # Edge style
    edge_type = Column(String(50), default="default")  # default | conditional | fallback
    animated = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="edges")
    source_node = relationship("WorkflowNode", foreign_keys=[source_node_id])
    target_node = relationship("WorkflowNode", foreign_keys=[target_node_id])


# ─── Conversation ─────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)

    # Caller info
    caller_phone = Column(String(50), default="")
    caller_name = Column(String(255), default="")
    caller_email = Column(String(255), default="")

    # State
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    current_node_id = Column(String, nullable=True)
    variables = Column(JSON, default=dict)  # Runtime variable store

    # Metadata
    duration_seconds = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    summary = Column(Text, default="")
    resolution = Column(String(255), default="")

    # Company recognition results
    company_profile = Column(JSON, default=dict)
    """
    {
        "company_name": "ABC Ltd",
        "country": "Turkey",
        "city": "Istanbul",
        "sector": "Technology",
        "sub_sector": "SaaS",
        "employee_count": "10-50",
        "annual_revenue": "1M-5M",
        "services": ["Web Development", "Mobile Apps"],
        "target_customers": "SMBs",
        "pain_points": ["Customer acquisition", "Retention"],
        "current_tools": ["Slack", "Jira"],
    }
    """

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)

    role = Column(String(20), nullable=False)  # agent | caller | system
    content = Column(Text, nullable=False)
    audio_url = Column(String(500), default="")

    # Processing metadata
    node_id = Column(String, nullable=True)  # Which workflow node generated this
    intent_detected = Column(String(255), default="")
    entities_extracted = Column(JSON, default=dict)
    confidence = Column(Float, nullable=True)
    latency_ms = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


# ─── Company ──────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    country = Column(String(100), default="")
    city = Column(String(100), default="")
    sector = Column(String(100), default="")
    sub_sector = Column(String(100), default="")
    description = Column(Text, default="")
    website = Column(String(500), default="")
    phone = Column(String(50), default="")
    email = Column(String(255), default="")

    # Business details
    employee_count_range = Column(String(50), default="")
    annual_revenue_range = Column(String(50), default="")
    founded_year = Column(Integer, nullable=True)
    business_type = Column(String(100), default="")  # B2B, B2C, B2B2C

    # Products & services
    services = Column(JSON, default=list)
    products = Column(JSON, default=list)
    target_customers = Column(JSON, default=list)
    competitive_advantages = Column(JSON, default=list)

    # Pain points & goals
    pain_points = Column(JSON, default=list)
    goals = Column(JSON, default=list)
    current_tools = Column(JSON, default=list)

    # AI-generated profile
    ai_summary = Column(Text, default="")
    ai_recommendations = Column(JSON, default=list)

    # Source
    source_conversation_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Knowledge Base ───────────────────────────────────────────────────

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    tags = Column(JSON, default=list)

    # For retrieval
    embedding = Column(JSON, nullable=True)  # Vector embedding for semantic search
    extra_metadata = Column(JSON, default=dict)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="knowledge_entries")
