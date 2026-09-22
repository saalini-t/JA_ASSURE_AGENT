import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings, MEDIA_DIR, EVIDENCE_DIR
from app.api.v1.api import api_router
from app.database.session import engine
from app.models.entities import Base
from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe, FFmpegNotFoundError

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nexora.main")

# Auto-initialize tables immediately so test clients and background tasks always have tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.warning(f"Initial table creation note: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables for Nexora JA Assure Platform...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

    try:
        ffmpeg_bin = resolve_ffmpeg()
        logger.info(f"FFmpeg binary resolved: {ffmpeg_bin}")
    except FFmpegNotFoundError as e:
        logger.warning(f"FFmpeg locator note: {e}")

    yield
    logger.info("Shutting down Nexora Backend.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Nexora — JA Assure AI Marketing Intelligence & Autonomous LinkedIn Publishing Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount media static files
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Mount evidence static files
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")

@app.get("/", tags=["Root"])
def root_endpoint():
    return {
        "message": "Welcome to JA Assure AI Marketing Agent API",
        "application": "NEXORA",
        "workspace": settings.WORKSPACE_NAME,
        "tagline": settings.TAGLINE,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "brands": settings.DEFAULT_BRANDS
    }

# Backward compatibility route
@app.get("/api/health")
def root_health():
    return {"status": "healthy", "service": settings.APP_NAME, "workspace": settings.WORKSPACE_NAME}
