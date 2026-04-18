"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "VoiceAgent Platform"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-to-a-secure-secret-key"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./voiceagent.db"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Voice Provider Settings
    ELEVENLABS_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # TTS Settings
    DEFAULT_TTS_PROVIDER: str = "elevenlabs"  # elevenlabs | openai | local
    DEFAULT_TTS_VOICE: str = "rachel"
    DEFAULT_TTS_MODEL: str = "eleven_turbo_v2"

    # STT Settings
    DEFAULT_STT_PROVIDER: str = "openai"  # openai | deepgram | local
    DEFAULT_STT_MODEL: str = "whisper-1"

    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "openai"  # openai | anthropic | ollama
    DEFAULT_LLM_MODEL: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    ANTHROPIC_API_KEY: str = ""

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    INSTAGRAM_ACCESS_TOKEN: str = "IGAANzFMVq5xtBZAFpkcVJqdEtCSmhpM080N2dJME9Xa1FENmdCb0ltQlFjSFhOdm1kN3BFejFxcHNHclZASUjVlWlR0RnlXeVkyRnktQ1c5eW9uMHM5a3VFeF91dWtmUXFHVWRObzA4M0RyNlhZAcm5KVzZAkODMyQklTUVRIV2EyWQZDZD"
    INSTAGRAM_VERIFY_TOKEN: str = "bigm_verify_123"

    # Catalogs
    PUBLIC_BASE_URL: str = ""

    # Messenger
    MESSENGER_PAGE_ACCESS_TOKEN: str = ""
    MESSENGER_VERIFY_TOKEN: str = "bigm_verify_123"

    # CSAT
    CSAT_ENABLED: str = "true"
    CSAT_DELAY_MINUTES: str = "30"

    # Auth
    JWT_SECRET: str = "change-this-to-a-long-random-string-abc123xyz789"

    # Broadcast
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"
    TELEGRAM_BOT_TOKEN: str = ""

    # FASHN.ai Virtual Try-On
    FASHN_API_KEY: str = ""

    # Unipile LinkedIn
    UNIPILE_API_KEY: str = ""
    UNIPILE_DSN: str = ""
    UNIPILE_ACCOUNT_ID: str = ""

    # HappyRobot AI Calls
    HAPPYROBOT_API_KEY: str = ""
    HAPPYROBOT_USE_CASE_ID: str = ""
    HAPPYROBOT_NUMBER_ID: str = ""
    HAPPYROBOT_API_URL: str = "https://app.happyrobot.ai/api/v1"
    HAPPYROBOT_WEBHOOK_URL: str = "https://workflows.platform.eu.happyrobot.ai/hooks/fhiyxhmghaqj"
    HAPPYROBOT_WEBHOOK_SECRET: str = ""

    # Netlify
    NETLIFY_ACCESS_TOKEN: str = ""

    # Apollo (legacy)
    APOLLO_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
