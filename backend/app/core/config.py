"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str = "CHANGE_ME"
    allowed_origins: str = "http://localhost:3000"

    # Postgres
    database_url: str = "postgresql+asyncpg://salespilot:salespilot_secret@localhost:5432/salespilot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Voice
    stt_provider: str = "openai_whisper"
    tts_provider: str = "openai"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"

    # RAG
    embedding_model: str = "all-MiniLM-L6-v2"
    faiss_index_path: str = "/app/data/faiss_index"
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Google Calendar
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/integrations/google/callback"
    google_calendar_id: str = "primary"

    # HubSpot
    hubspot_api_key: str = ""
    hubspot_portal_id: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "salespilot@yourcompany.com"

    # Appointment
    appointment_duration_minutes: int = 30
    appointment_timezone: str = "UTC"

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
