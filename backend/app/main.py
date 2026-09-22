import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.v1.api import api_router
from app.database.session import engine
from app.models.entities import Base

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ja_assure.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe automatic table initialization on startup
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")

    # Surface which FFmpeg/ffprobe binaries this process will actually use, up
    # front, rather than only discovering a discovery problem on the first render.
    from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe, FFmpegNotFoundError
    try:
        resolve_ffmpeg()
        resolve_ffprobe()
    except FFmpegNotFoundError as e:
        logger.warning(f"Video generation will fail until this is resolved: {e}")

    # Automatic publishing worker (Project 2) -- SAFE DEFAULT IS DISABLED.
    # Starting the app never begins automatic LinkedIn publishing unless this is
    # explicitly enabled; see app.services.publishing_worker's module docstring.
    worker_task = None
    if settings.PUBLISH_WORKER_ENABLED:
        from app.services.publishing_worker import run_forever
        worker_task = asyncio.create_task(run_forever())
        logger.info(
            f"Automatic LinkedIn publishing worker ENABLED "
            f"(interval={settings.PUBLISH_WORKER_INTERVAL_SECONDS}s)."
        )
    else:
        logger.info("Automatic LinkedIn publishing worker is DISABLED (PUBLISH_WORKER_ENABLED=false).")

    yield

    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down JA Assure AI Marketing Agent backend.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic AI Marketing System for JA Assure (Jade, DoctorShield, Jaguar Transit)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve generated video/image/audio assets (repo_root/media/...). Single shared
# media root for both the video pipeline (media/generated/{job_id}/...) and the
# Voice Agent (media/voiceovers/...) -- see voice_service.py's media_root anchor,
# which was adjusted to point here so its returned audio_url is actually servable
# through this same mount instead of a second, unmounted backend/media tree.
# Phase 1: read-only static files, no auth -- fine for local/demo use; revisit if this
# is ever deployed somewhere public before Project 2 publishing work begins.
_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "media"
(_MEDIA_ROOT / "generated").mkdir(parents=True, exist_ok=True)
(_MEDIA_ROOT / "voiceovers").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_MEDIA_ROOT)), name="media")

@app.get("/", tags=["Root"])
def root_endpoint():
    return {
        "message": "Welcome to JA Assure AI Marketing Agent API",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "brands": settings.DEFAULT_BRANDS
    }
