import os
from pathlib import Path
from typing import List, Annotated, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode
from pydantic import field_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Nexora — JA Assure AI Marketing Intelligence Platform"
    TAGLINE: str = "Ideas to Impact"
    WORKSPACE_NAME: str = "JA ASSURE"
    API_V1_STR: str = "/api/v1"

    # CORS Origins
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Database URL (SQLite default for resilient local persistence, or PostgreSQL / Supabase)
    DATABASE_URL: str = "sqlite:///nexora_ja_assure.db"

    # Supabase Project Credentials
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # LLM Settings (Gemini & Groq API)
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "groq/compound"

    # LinkedIn Publishing Integration
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_ORGANIZATION_ID: str = ""

    # Image Generation (OpenAI Images API / HuggingFace)
    OPENAI_API_KEY: str = ""
    HF_TOKEN: str = ""
    HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-dev"
    IMAGE_PROVIDER: str = "gemini"

    # FFmpeg / ffprobe binary paths
    FFMPEG_PATH: Optional[str] = None
    FFPROBE_PATH: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Brands Supported by JA Assure
    DEFAULT_BRANDS: Annotated[List[str], NoDecode] = ["jade", "doctorshield", "jaguartransit", "jaassure"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return v

    @field_validator("DEFAULT_BRANDS", mode="before")
    @classmethod
    def assemble_brands(cls, v):
        if isinstance(v, str):
            return [i.strip().lower() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Root directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_GENERATED_DIR = MEDIA_DIR / "generated"
MEDIA_VOICEOVERS_DIR = MEDIA_DIR / "voiceovers"
EVIDENCE_DIR = BASE_DIR / "evidence"
DATA_DIR = BASE_DIR / "data"

for d in [MEDIA_DIR, MEDIA_GENERATED_DIR, MEDIA_VOICEOVERS_DIR, EVIDENCE_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)
