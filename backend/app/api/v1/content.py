from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.agent_contracts import (
    ContentBrief,
    GeneratedVariation,
    ContentSuiteRequest,
    VideoScript,
    VoiceGenerationResult,
)
from app.schemas.dtos import ContentQueueResponse
from app.services.content_service import content_service
from app.services.media_service import media_service
from app.services.pipeline_service import pipeline_service
from app.services.voice_service import (
    voice_service,
    VoiceEmptyError,
    VoiceLanguageError,
    VoiceSynthesisError
)

router = APIRouter(prefix="/content", tags=["Content Generation"])

class SingleContentRequest(BaseModel):
    brand: str
    platform: str
    topic: str
    content_type: str = "post"
    language: str = "en"
    key_benefits: Optional[List[str]] = None
    target_persona: Optional[str] = None
    cta: Optional[str] = None

class VideoRequest(BaseModel):
    brand: str = "jade"
    topic: str = "Protecting bespoke jewellery collections"
    target_duration: int = 45
    platform: Optional[str] = "reel"
    language: Optional[str] = "en"
    target_audience: Optional[str] = None
    render: bool = True # Assembles a real MP4 with motion graphics
    narrate: bool = True # Live Voice Agent narration + burned-in captions

@router.post("/generate", response_model=List[GeneratedVariation])
async def generate_content_variations(req: SingleContentRequest):
    """
    Generate A/B marketing copy variations for a single brief adhering to brand voice & active lessons.
    """
    brief = ContentBrief(
        brand=req.brand,
        platform=req.platform,
        content_type=req.content_type,
        topic=req.topic,
        language=req.language,
        key_benefits=req.key_benefits or [],
        target_persona=req.target_persona,
        cta=req.cta
    )
    try:
        variations = await content_service.generate_variations(brief)
        return variations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

@router.post("/suite", response_model=List[ContentQueueResponse])
async def generate_content_suite(suite_req: ContentSuiteRequest):
    """
    Execute full 'Brain' pipeline across multiple platforms, formats, and languages.
    Automatically applies research context, injects lessons, runs compliance gate,
    and stages items in ContentQueue with status='human_review' (MANDATORY human sign-off).
    """
    try:
        created_items = await pipeline_service.generate_content_suite(suite_req)
        return created_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content suite pipeline failed: {str(e)}")

@router.post("/video", response_model=VideoScript)
async def generate_video_script(req: VideoRequest):
    """
    Generate a 30-60 second structured video storyboard with scene breakdowns and voiceover
    (unchanged, existing media_service.generate_video_script()).

    Phase 1 (default): when render=True and narrate=False (both defaults), assembles
    a real MP4 from the generated scenes -- one still image per scene via
    ImageMotionProvider, animated with deterministic FFmpeg pan/zoom, concatenated
    together. This path never depends on TTS at all.

    Phase 2 (opt-in): pass narrate=true to additionally generate a real voiceover per
    scene (measured duration becomes authoritative for that scene) and a burned-in
    caption derived from the same voiceover text; the final MP4 then carries both a
    video and an audio stream. A TTS failure fails the render explicitly
    (render_status="failed", error stage "tts") -- it never falls back to a silent
    or fake-audio "success". All TTS/caption code is unchanged; only the default that
    decides whether the endpoint exercises it has moved.

    Either way, rendering failures do not fail the HTTP request -- the storyboard is
    still returned with render_status="failed" and render_error set, so the planner
    output is never lost just because assembly had a problem.
    """
    try:
        script = await media_service.generate_video_script(
            brand=req.brand,
            topic=req.topic,
            target_duration=req.target_duration,
            platform=req.platform or "reel",
            language=req.language or "en",
            target_audience=req.target_audience
        )

        if req.render:
            from app.services.video_generation_service import generate_video_mvp

            render_result = await generate_video_mvp(
                script,
                target_duration_seconds=req.target_duration,
                narrate=req.narrate,
            )
            script.job_id = render_result.job_id
            script.scenes_generated = render_result.scenes_generated
            script.image_source = render_result.image_source_summary
            script.has_audio = render_result.has_audio
            script.has_captions = render_result.has_captions
            script.audio_source = render_result.audio_source
            script.audio_duration_seconds = render_result.audio_duration_seconds
            script.caption_file = render_result.caption_file
            if render_result.success:
                script.video_url = render_result.video_url
                script.video_duration_seconds = render_result.duration_seconds
                script.render_status = "completed"
            else:
                script.render_status = "failed"
                script.render_error = f"[{render_result.error_stage}] {render_result.error_message}"
        else:
            script.render_status = "skipped"

        return script
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video script generation failed: {str(e)}")

@router.post("/voice", response_model=VoiceGenerationResult)
async def generate_voiceover(
    script: VideoScript,
    language_override: Optional[str] = None
):
    """
    Synthesize high-fidelity MP3 speech audio from VideoScript scene voiceover text.
    Uses dedicated VoiceService with clean multi-language mapping (en, ms, id, th, zh).
    Saves persistent MP3 to /media/voiceovers/ and returns audio URL and duration.
    """
    try:
        result = voice_service.synthesize_from_script(
            script=script,
            language_override=language_override
        )
        return result
    except VoiceEmptyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VoiceLanguageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VoiceSynthesisError as e:
        raise HTTPException(status_code=502, detail=f"Voice synthesis failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")
