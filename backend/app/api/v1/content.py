import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import ContentQueue
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
from app.services.compliance_service import compliance_service
from app.services import video_generation_service
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
    render: bool = True # Phase 1: also assemble a real MP4, not just the storyboard JSON
    # Phase 2: also generate voiceover + burned captions (requires render=True).
    # Temporarily defaulted to False so /content/video's default behavior is the
    # Phase 1 visual-only pipeline (VideoScript -> Scene Validator -> OpenAI Images ->
    # FFmpeg -> MP4) without depending on OpenAI TTS being available/unrate-limited.
    # All TTS/caption code is fully intact -- pass narrate=true explicitly to exercise
    # the complete Phase 2 pipeline; nothing about it changed.
    narrate: bool = False

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

class SequentialCampaignRequest(BaseModel):
    brand: str = "jade"
    topic: str = "Protecting bespoke jewellery collections"
    platform: str = "linkedin"
    content_type: str = "post"
    language: str = "en"
    key_benefits: Optional[List[str]] = None
    target_persona: Optional[str] = None
    cta: Optional[str] = None
    include_media: bool = False
    media_format: str = "auto"  # "video" | "image" | "auto"
    target_duration: int = 45

@router.post("/campaign", response_model=ContentQueueResponse, status_code=201)
async def run_sequential_campaign(req: SequentialCampaignRequest):
    """
    One call, one sequential pipeline: content generation -> (optionally) real
    image/video generation -> compliance -> ContentQueue -- instead of
    separately calling /content/generate (or /suite), /content/video, and
    /content/video/enqueue by hand. Always lands in human_review (or
    'pending' if compliance flagged it) -- never auto-approved, never
    auto-published, exactly like every other path into the queue.
    """
    try:
        item = await pipeline_service.run_sequential_campaign(
            brand=req.brand, topic=req.topic, platform=req.platform,
            content_type=req.content_type, language=req.language,
            key_benefits=req.key_benefits, target_persona=req.target_persona, cta=req.cta,
            include_media=req.include_media, media_format=req.media_format,
            target_duration=req.target_duration,
        )
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sequential campaign failed: {str(e)}")

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
            script.narration_word_count = render_result.narration_word_count
            script.narration_estimated_seconds = render_result.narration_estimated_seconds
            script.narration_rewritten = render_result.narration_rewritten
            script.scene_image_sources = [
                {
                    "scene_number": r.scene_number,
                    "source": r.source,
                    "is_real_ai": r.is_real_ai,
                    "provider": r.provider,
                    "model": r.model,
                    "provider_error": r.provider_error,
                }
                for r in render_result.scene_image_reports
            ]
            script.ai_generated_scene_count = render_result.ai_generated_scene_count
            script.fallback_scene_count = render_result.fallback_scene_count
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

@router.post("/video/enqueue", response_model=ContentQueueResponse, status_code=201)
async def enqueue_rendered_video(script: VideoScript, db: Session = Depends(get_db)):
    """
    Closes the media-to-publishing gap: takes an ALREADY-RENDERED VideoScript (the
    exact object POST /content/video returns, with render_status="completed") and
    enters it into the governed ContentQueue -- the only path a video can reach
    LinkedIn video publishing through (see publishing_service._extract_media,
    which reads video_path from ContentQueue.metadata_json). A separate, explicit
    step rather than folding into POST /content/video itself, so that endpoint's
    existing behavior/tests are entirely undisturbed.

    Never enqueues a failed or unrendered script -- there is no video file to
    publish. Runs compliance on the accompanying post caption (hook + CTA +
    disclaimer) exactly like any other content type; this is NOT auto-approved,
    it enters 'human_review' (or 'pending' if compliance flags it), same as
    everything else in ContentQueue.
    """
    if script.render_status != "completed" or not script.job_id:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot enqueue a video that hasn't completed rendering (render_status='{script.render_status}').",
        )

    video_path = video_generation_service.MEDIA_ROOT / script.job_id / "final.mp4"
    if not video_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Rendered video file not found on disk for job_id={script.job_id}: {video_path}",
        )

    caption_parts = [p for p in [script.hook, script.cta, script.disclaimer] if p]
    content_raw = "\n\n".join(caption_parts) or (script.title or "New Reel")

    brand_clean = (script.brand or "jade").lower()
    comp = await compliance_service.evaluate_content(
        brand=brand_clean, content_text=content_raw, content_type="reel", language=script.language or "en",
    )
    compliance_status = "passed" if comp.passed else "flagged"
    queue_status = "human_review" if comp.passed else "pending"

    metadata = {
        "video_path": str(video_path),
        "video_url": script.video_url,
        "video_duration_seconds": script.video_duration_seconds,
        "caption_file": script.caption_file,
        "has_audio": script.has_audio,
        "has_captions": script.has_captions,
        "audio_source": script.audio_source,
        "image_source": script.image_source,
        "scene_image_sources": script.scene_image_sources,
        "ai_generated_scene_count": script.ai_generated_scene_count,
        "fallback_scene_count": script.fallback_scene_count,
        "narration_word_count": script.narration_word_count,
        "narration_estimated_seconds": script.narration_estimated_seconds,
        "narration_rewritten": script.narration_rewritten,
        "compliance_violations": [v.model_dump() for v in comp.violations],
        "compliance_warnings": [w.model_dump() for w in comp.warnings],
    }

    item = ContentQueue(
        brand=brand_clean,
        platform="linkedin",
        content_type="reel",
        topic=script.title or script.concept or "Reel",
        content_raw=content_raw,
        original_content_raw=content_raw,
        variation="A",
        language=script.language or "en",
        compliance_status=compliance_status,
        status=queue_status,
        compliance_score=comp.score,
        reason_tag=comp.violations[0].rule_id if comp.violations else None,
        notes=comp.overall_feedback,
        metadata_json=json.dumps(metadata),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

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
