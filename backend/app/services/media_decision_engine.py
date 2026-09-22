"""
Unified media generation entrypoint -- one call decides whether a campaign
needs a real generated video or a real generated image and produces it,
instead of a caller separately hitting /content/video and then
/content/video/enqueue. Concept adapted from a reference project's
"MediaDecisionEngine", rebuilt against this codebase's own 4-tier image
cascade and video pipeline.

Deliberately NOT ported from that reference: its auto-approval step. This
module only ever produces a media file -- it never touches ContentQueue,
HITL status, or compliance. Every item this feeds into still lands in
human_review like anything else in this codebase.
"""
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.schemas.agent_contracts import VideoScene
from app.services.media_service import media_service
from app.services.video_generation_service import generate_video_mvp, MEDIA_ROOT
from app.services.video_providers import ImageMotionProvider, SOURCE_FALLBACK

logger = logging.getLogger("ja_assure.media_decision")


@dataclass
class MediaDecisionResult:
    media_type: str  # "video" | "image"
    media_path: Optional[Path]
    media_url: Optional[str]
    source: str  # e.g. "stable_diffusion_1_5", "gemini", "branded_fallback_demo", "none"
    is_real_ai: bool
    duration_seconds: float = 0.0
    scenes_generated: int = 0
    ai_generated_scene_count: int = 0
    fallback_scene_count: int = 0
    error: Optional[str] = None


async def decide_and_generate_media(
    brand: str,
    topic: str,
    format_type: str = "auto",  # "video" | "image" | "auto"
    target_duration: int = 45,
    platform: str = "reel",
    language: str = "en",
) -> MediaDecisionResult:
    """Never raises -- a failure comes back as a MediaDecisionResult with
    media_path=None and `error` set, so the caller (the sequential campaign
    pipeline) can still create the text-only content item rather than losing
    the whole request over a media failure."""
    fmt = (format_type or "auto").lower().strip()

    if fmt == "image":
        return await _generate_image_only(brand, topic)

    # "video" or "auto" both attempt a real video first.
    try:
        script = await media_service.generate_video_script(
            brand=brand, topic=topic, target_duration=target_duration,
            platform=platform, language=language,
        )
        result = await generate_video_mvp(script, target_duration_seconds=target_duration, narrate=True)
        if result.success and result.video_path and result.video_path.exists():
            return MediaDecisionResult(
                media_type="video",
                media_path=result.video_path,
                media_url=result.video_url,
                source=result.image_source_summary,
                is_real_ai=result.ai_generated_scene_count > 0,
                duration_seconds=result.duration_seconds,
                scenes_generated=result.scenes_generated,
                ai_generated_scene_count=result.ai_generated_scene_count,
                fallback_scene_count=result.fallback_scene_count,
            )
        logger.warning(f"[media_decision] video generation did not succeed: {result.error_message}")
        if fmt == "video":
            return MediaDecisionResult(
                media_type="video", media_path=None, media_url=None,
                source="none", is_real_ai=False, error=result.error_message,
            )
    except Exception as e:
        logger.warning(f"[media_decision] video generation raised: {e}")
        if fmt == "video":
            return MediaDecisionResult(
                media_type="video", media_path=None, media_url=None,
                source="none", is_real_ai=False, error=str(e),
            )

    # "auto" falls through to a single real image when video didn't pan out.
    return await _generate_image_only(brand, topic)


async def _generate_image_only(brand: str, topic: str) -> MediaDecisionResult:
    job_id = f"campaign_{uuid.uuid4().hex[:8]}"
    out_dir = MEDIA_ROOT / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / "creative_image.png"

    scene = VideoScene(
        scene_number=1, duration_seconds=10,
        visual_description=f"Professional marketing photograph for {brand.title()}: {topic}",
        voiceover="", onscreen_text=topic[:60],
    )
    try:
        provider = ImageMotionProvider()
        visual = await provider.generate_scene_visual(scene, brand, img_path)
        return MediaDecisionResult(
            media_type="image", media_path=img_path,
            media_url=f"/media/generated/{job_id}/creative_image.png",
            source=visual.source, is_real_ai=visual.source != SOURCE_FALLBACK,
        )
    except Exception as e:
        logger.error(f"[media_decision] image generation failed: {e}")
        return MediaDecisionResult(
            media_type="image", media_path=None, media_url=None,
            source="none", is_real_ai=False, error=str(e),
        )
