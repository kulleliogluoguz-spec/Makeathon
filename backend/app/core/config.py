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

    class Config:
        env_file = ".env"


settings = Settings()
