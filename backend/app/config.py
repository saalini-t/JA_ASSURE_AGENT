import os
from typing import List, Annotated
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode
from pydantic import field_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "JA Assure AI Marketing Agent"
    API_V1_STR: str = "/api/v1"

    # CORS Origins
    # NoDecode: pydantic-settings otherwise tries to JSON-decode List[str] env values
    # before the field_validator below ever runs, which crashes on a plain
    # comma-separated .env value (e.g. "http://a,http://b") -- exactly the format
    # this codebase's .env.example files use. NoDecode defers to the validator instead.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Database URL (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"

    # Supabase Project Credentials
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # LLM Settings (Groq API)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Image Generation (OpenAI Images API) -- optional. Leave empty to use the
    # clearly-labeled branded fallback card instead of real AI-generated visuals.
    OPENAI_API_KEY: str = ""

    # Image Generation (Hugging Face Inference Providers) -- optional second real
    # AI image vendor. Leave HF_TOKEN empty to keep this provider unavailable.
    HF_TOKEN: str = ""
    HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-dev"

    # Real business discovery (Google Places API "New") -- optional. Leave blank
    # to keep lead discovery on its existing Groq-invented-profile / demo-pool
    # path. When set, discover_and_score_leads() tries real Google Places
    # results first (see lead_discovery_providers.discover_real_businesses).
    GOOGLE_MAPS_API_KEY: str = ""

    # Real contact enrichment (Hunter.io) -- optional secondary provider, tried
    # before the SSRF-safe direct-website-scrape fallback in
    # lead_discovery_providers.find_real_contact_email. Leave blank to skip
    # straight to the direct-scrape fallback.
    HUNTER_API_KEY: str = ""

    # Image Generation (Google Gemini) -- PRIMARY AI visual provider for video scene
    # visuals (see video_providers.GeminiImageProvider). Doesn't depend on OpenAI
    # Images API quota or Hugging Face Inference Provider credits. Leave blank to
    # fall through to OpenAI/Hugging Face/branded fallback. Get a key at
    # https://aistudio.google.com/apikey
    GEMINI_API_KEY: str = ""
    GEMINI_IMAGE_MODEL: str = "models/gemini-2.5-flash-image"

    # Stable Diffusion 1.5 (local, third-tier fallback provider -- see README's
    # "Stable Diffusion 1.5 (Local) Setup" section). No API key needed; requires
    # `pip install diffusers torch` (not installed by default -- see README) and,
    # on first real use, downloads model weights from Hugging Face Hub unless
    # SD15_MODEL_PATH already points to a locally-downloaded directory. Never
    # loaded/downloaded at application startup -- only lazily on first real use.
    SD15_MODEL_PATH: str = "runwayml/stable-diffusion-v1-5"
    SD15_DEVICE: str = "auto"  # "auto" | "cuda" | "cpu"
    SD15_LOW_VRAM: bool = False  # attention slicing + sequential CPU offload on CUDA
    SD15_NUM_INFERENCE_STEPS: int = 25
    SD15_GUIDANCE_SCALE: float = 7.5
    SD15_WIDTH: int = 512
    SD15_HEIGHT: int = 768
    SD15_SEED: int = -1  # -1 = a new random seed every generation

    # Which image provider video_generation_service should use for scene visuals:
    # "auto" (default) cascades Gemini -> Hugging Face -> Stable Diffusion 1.5
    # (local) -> branded fallback, stopping at the first real success. Set to one
    # specific value ("gemini" | "openai" | "huggingface" | "stable_diffusion" |
    # "branded_fallback") to force that single provider only (no cascade).
    IMAGE_PROVIDER: str = "auto"

    # LinkedIn publishing (The Hands) -- optional. A long-lived OAuth 2.0 access token
    # obtained externally (no in-app OAuth flow yet); leave blank to keep LinkedIn
    # publishing explicitly unconfigured (publish attempts fail honestly, never fake
    # success). LINKEDIN_ORGANIZATION_ID is optional -- when blank, posts publish under
    # the authenticated member's own profile instead of a company page.
    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_ORGANIZATION_ID: str = ""

    # In-app LinkedIn OAuth flow (member posting, w_member_social scope) -- an
    # alternative to pasting a token in manually above. All three are required to
    # use GET /api/v1/auth/linkedin/login; leave blank to keep using a manually
    # obtained LINKEDIN_ACCESS_TOKEN instead. Get these from a LinkedIn Developer
    # Portal app (https://www.linkedin.com/developers/apps) under Auth settings.
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/linkedin/callback"

    # Automatic background publishing worker (Project 2 / "The Hands"). SAFE
    # DEFAULT IS DISABLED -- starting the app never begins automatic publishing
    # unless this is explicitly set to true. When enabled, polls at
    # PUBLISH_WORKER_INTERVAL_SECONDS and publishes through the exact same gated
    # publishing_service.publish_to_linkedin() the manual trigger endpoint uses --
    # human approval (status=="approved" AND compliance_status=="passed") remains
    # absolute regardless of this setting.
    PUBLISH_WORKER_ENABLED: bool = False
    PUBLISH_WORKER_INTERVAL_SECONDS: int = 60

    # Email outreach sending (optional). "mock" (default) never sends a real email
    # -- it logs and returns a clearly-labeled mock result, safe for demos/tests.
    # Set to "smtp" and configure SMTP_HOST/PORT/USERNAME/PASSWORD/EMAIL_FROM to
    # send real email via any standard SMTP provider (Gmail, SendGrid SMTP relay,
    # Resend SMTP, etc.) -- only ever for LeadOutreach rows with status=="approved".
    EMAIL_PROVIDER: str = "mock"
    EMAIL_FROM: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # Narration-duration budgeting (video pipeline) -- documented average speaking
    # pace assumed for word-count-based narration duration estimates. Typical cited
    # range for a measured, professional voiceover read is ~130-160 wpm.
    NARRATION_WORDS_PER_MINUTE: float = 150.0

    # Logging
    LOG_LEVEL: str = "INFO"

    # Brands Supported by JA Assure
    DEFAULT_BRANDS: Annotated[List[str], NoDecode] = ["jade", "doctorshield", "jaguartransit"]

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
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
