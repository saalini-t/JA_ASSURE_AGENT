"""
Video asset pipeline: turns an existing VideoScript (produced by
media_service.generate_video_script(), unchanged) into a real, playable MP4.

Phase 1 (narrate=False, the default for direct calls to generate_video_mvp): one
still image per scene (via VideoProvider), animated with deterministic FFmpeg
pan/zoom, concatenated into a silent file.

Phase 2 (narrate=True): additionally generates a real voiceover per scene (via
VideoTTSProvider), measures its actual duration (which becomes authoritative for
that scene's rendered length), derives burned-in captions directly from the same
voiceover text, and muxes video+audio+captions per scene before concatenation.

Still OUT of scope: compliance checks, HITL, publishing, background workers,
ComfyUI/Wan2.1, scene-level caching. This module only proves the asset pipeline
end to end; those integrations are later phases.

Synchronous by design (see Phase 1 report): completes well within a normal request/
response cycle. generate_video_mvp() already returns a job_id and a structured
result, so wrapping this same function in a background task + a VideoGenerationJob
table later is a pure addition, not a rewrite.
"""
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from app.schemas.agent_contracts import VideoScript, VideoScene
from app.services.scene_validator import validate_video_script
from app.services.video_providers import (
    ImageMotionProvider, VideoProvider, BrandedFallbackProvider,
    SOURCE_AI_GENERATED, SOURCE_HUGGINGFACE, SOURCE_GEMINI, SOURCE_STABLE_DIFFUSION, SOURCE_FALLBACK,
)
from app.services.tts_providers import VideoTTSProvider, VoiceAgentTTSProvider, TTSGenerationError
from app.services import caption_service
from app.services.narration_budget import enforce_narration_budget
from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe, FFmpegNotFoundError

logger = logging.getLogger("ja_assure.video.generation")

# Target-duration tolerance: media_service's deterministic (offline) video script
# fallback returns fixed, hand-written scene durations that ignore whatever
# target_duration the caller actually requested (confirmed by inspection: the
# jade/doctorshield/jaguartransit branches in
# MediaService._generate_deterministic_video_script hard-code scenes summing to a
# fixed ~45s regardless of the target_duration parameter passed in -- it's accepted
# but never read in that function body). The live Groq path can drift too, since the
# prompt only *asks* the LLM for "approximately" the target. Rather than touching
# media_service.py (untouched, working script generation), this pipeline
# deterministically re-scales scene durations to the caller's actual requested
# target after the fact, before any image/TTS/FFmpeg work is spent.
TARGET_DURATION_TOLERANCE = 0.15

# backend/app/services/video_generation_service.py -> services -> app -> backend -> repo root
MEDIA_ROOT = Path(__file__).resolve().parents[3] / "media" / "generated"

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30

# Deterministic camera-motion rotation. Groq never chooses this -- code does,
# per the brief's explicit instruction not to let the LLM author FFmpeg behavior.
_CAMERA_MOTIONS = ["zoom_in", "pan_left", "pan_right", "zoom_out"]

_COMMAND_TIMEOUT_SECONDS = 120


class VideoGenerationError(Exception):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


@dataclass
class SceneImageReport:
    """
    Per-scene image-provenance record (Phase 3, Step 2): explicit REAL_AI_IMAGE /
    FALLBACK_IMAGE classification, which concrete provider/model actually produced
    the file, and -- when a real AI provider was attempted but failed before a
    graceful fallback covered it (OpenAIImageProvider's degrade-to-fallback design) --
    the underlying provider error, so a caller can never mistake a fallback card for
    a real AI-generated image.
    """
    scene_number: int
    source: str  # SOURCE_AI_GENERATED | SOURCE_HUGGINGFACE | SOURCE_FALLBACK
    is_real_ai: bool
    provider: str
    model: Optional[str] = None
    provider_error: Optional[str] = None


@dataclass
class VideoGenerationResult:
    job_id: str
    success: bool
    video_path: Optional[Path] = None
    video_url: Optional[str] = None
    duration_seconds: float = 0.0
    scenes_generated: int = 0
    image_source_summary: str = ""
    error_stage: Optional[str] = None
    error_message: Optional[str] = None
    # Phase 2 fields -- default to "no narration" so Phase 1 callers are unaffected.
    has_audio: bool = False
    has_captions: bool = False
    audio_source: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    caption_file: Optional[str] = None
    # Narration-budgeting fields (Phase 2) -- default to None for the non-narrated path.
    narration_word_count: Optional[int] = None
    narration_estimated_seconds: Optional[float] = None
    narration_rewritten: bool = False
    # Per-scene image provenance (Phase 3) -- see SceneImageReport.
    scene_image_reports: List[SceneImageReport] = field(default_factory=list)
    ai_generated_scene_count: int = 0
    fallback_scene_count: int = 0


def normalize_scene_durations(
    scenes: List[VideoScene], target_duration: int, tolerance: float = TARGET_DURATION_TOLERANCE
) -> bool:
    """
    Deterministically rescale scene.duration_seconds (in place) so the total matches
    the caller's requested target_duration within `tolerance`. No-op (returns False)
    if the scenes already sum within tolerance -- deterministic means the same input
    always produces the same output, including "leave it alone" when it's already fine.
    Returns True if scenes were rescaled.
    """
    total = sum(s.duration_seconds for s in scenes)
    if total <= 0 or target_duration <= 0:
        return False

    lower = target_duration * (1 - tolerance)
    upper = target_duration * (1 + tolerance)
    if lower <= total <= upper:
        return False

    scale = target_duration / total
    remaining = target_duration
    for idx, scene in enumerate(scenes):
        if idx == len(scenes) - 1:
            scene.duration_seconds = max(1, remaining)
        else:
            new_duration = max(1, round(scene.duration_seconds * scale))
            scene.duration_seconds = new_duration
            remaining -= new_duration
    return True


def _ffmpeg_binary() -> str:
    """
    Resolved, absolute path to ffmpeg -- never a bare "ffmpeg" string left for
    subprocess to hope PATH resolves later (see ffmpeg_locator.py for why that broke
    on Windows even with FFmpeg genuinely installed). Raises VideoGenerationError
    immediately with an actionable message if it can't be found; every call site of
    this function already sits inside a try/except VideoGenerationError block
    (generate_video_mvp's per-scene loop), so this propagates through the exact same
    error-handling path as any other rendering failure -- no new exception handling
    needed anywhere else.
    """
    try:
        return resolve_ffmpeg()
    except FFmpegNotFoundError as e:
        raise VideoGenerationError("ffmpeg_discovery", str(e))


def _ffprobe_binary() -> Optional[str]:
    """
    Resolved, absolute path to ffprobe, or None if it can't be found anywhere.
    ffprobe is used for post-hoc validation of an already-rendered file, not to
    create it -- callers that treat it as optional (skip validation, log a warning)
    keep doing so; callers that require it for a specific check already raise their
    own clear error when this returns None (unchanged).
    """
    try:
        return resolve_ffprobe()
    except FFmpegNotFoundError:
        return None


def _run(cmd: List[str], stage: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_COMMAND_TIMEOUT_SECONDS,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError:
        raise VideoGenerationError(
            stage,
            "FFmpeg/ffprobe binary not found on PATH. Install FFmpeg and ensure the backend "
            "process's PATH includes it (see README setup instructions).",
        )
    except subprocess.TimeoutExpired:
        raise VideoGenerationError(stage, f"Command timed out after {_COMMAND_TIMEOUT_SECONDS}s.")
    if proc.returncode != 0:
        raise VideoGenerationError(stage, f"Command failed (exit {proc.returncode}): {proc.stderr[-2000:]}")
    return proc


def _camera_motion_for(index: int) -> str:
    return _CAMERA_MOTIONS[index % len(_CAMERA_MOTIONS)]


def _zoompan_filter(motion: str, duration_seconds: float, fps: int) -> str:
    frames = max(1, int(round(duration_seconds * fps)))
    # Cover-crop, not a stretch: scale up so the image fully covers the 2x-supersampled
    # canvas while preserving its own aspect ratio (force_original_aspect_ratio=increase),
    # then center-crop the overflow. A naive scale=W:H (fixed both dimensions) would
    # non-uniformly stretch/distort any source image whose aspect ratio isn't already
    # exactly 9:16 -- true for OpenAI's 1024x1536 (2:3) and Hugging Face's default
    # output. This is a no-op crop for BrandedFallbackProvider's images, which are
    # already generated at the exact target aspect ratio.
    scale = (
        f"scale={OUTPUT_WIDTH * 2}:{OUTPUT_HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH * 2}:{OUTPUT_HEIGHT * 2}"
    )

    if motion == "zoom_in":
        z, x, y = "min(zoom+0.0015,1.3)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z, x, y = "if(eq(on,1),1.3,max(zoom-0.0015,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z, x, y = "1.15", f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
    else:  # pan_right
        z, x, y = "1.15", f"(iw-iw/zoom)*(on/{frames})", "ih/2-(ih/zoom/2)"

    zoompan = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:fps={fps}"
    return f"{scale},{zoompan},format=yuv420p"


def _render_scene_clip(image_path: Path, clip_path: Path, duration_seconds: int, motion: str) -> None:
    vf = _zoompan_filter(motion, duration_seconds, OUTPUT_FPS)
    cmd = [
        _ffmpeg_binary(), "-y",
        "-loop", "1", "-i", str(image_path),
        "-t", str(duration_seconds),
        "-vf", vf,
        "-r", str(OUTPUT_FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(clip_path),
    ]
    _run(cmd, "scene_animation")


def _probe_audio_duration(audio_path: Path) -> float:
    """Measures the ACTUAL duration of a generated voiceover file. Never assume the
    requested/planned scene duration equals the real audio duration -- TTS speech
    length depends on the text and voice, not on what we asked for."""
    ffprobe_bin = _ffprobe_binary()
    if not ffprobe_bin:
        raise VideoGenerationError("tts", "ffprobe not found on PATH; cannot measure generated audio duration.")

    proc = subprocess.run(
        [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_path)],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        raise VideoGenerationError("tts", f"ffprobe failed to read generated audio: {proc.stderr[-500:]}")

    info = json.loads(proc.stdout)
    duration = float(info.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        raise VideoGenerationError("tts", "Generated audio file reports zero duration.")
    return duration


# Common system font locations, checked in order. drawtext's fontfile= needs a real
# resolvable path (unlike Pillow's ImageFont.truetype, which searches OS font dirs
# on its own) -- this mirrors that same "Arial or a sane default" intent for burned
# captions. If none exist, captions still burn using FFmpeg's compiled-in default.
_CAPTION_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _find_caption_font() -> Optional[str]:
    for candidate in _CAPTION_FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def _escape_ffmpeg_filter_path(path: str) -> str:
    """Escapes a path for safe use INSIDE an ffmpeg filtergraph string (e.g.
    fontfile=). Forward-slash the path and escape the drive-letter colon, which
    would otherwise be parsed as a filter-option separator on Windows."""
    return path.replace("\\", "/").replace(":", r"\:")


def _drawtext_filter(caption_textfile_name: str) -> str:
    """
    Builds a drawtext clause that burns a scene's caption in from a plain text file
    (referenced by bare relative filename -- see cwd handling in
    _render_narrated_scene_clip, which sidesteps ALL path-escaping issues for files
    we control; only the external font file needs colon/backslash escaping).
    """
    font = _find_caption_font()
    font_clause = f"fontfile='{_escape_ffmpeg_filter_path(font)}':" if font else ""
    return (
        f"drawtext={font_clause}textfile={caption_textfile_name}:"
        f"fontsize=54:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:"
        f"x=(w-text_w)/2:y=h-th-140"
    )


def _render_narrated_scene_clip(
    job_dir: Path, image_name: str, audio_name: Optional[str], caption_name: Optional[str],
    clip_name: str, duration_seconds: float, motion: str,
) -> None:
    """
    Same visual treatment as _render_scene_clip (image + deterministic pan/zoom),
    plus a muxed audio track and (when captioned) a burned-in caption. Runs with
    cwd=job_dir and bare filenames so none of OUR files need path escaping in the
    filter graph -- only the external caption font (handled by _drawtext_filter) does.

    audio_name=None renders a silent scene: genuine digital silence (FFmpeg's own
    anullsrc, not a TTS call on empty text) for exactly this scene's duration. This
    exists for the disclaimer/end-card scene, which intentionally has no voiceover
    but must still get a real audio stream -- every scene clip needs one so the later
    `-f concat -c copy` step sees a uniform video+audio layout across all segments.
    caption_name=None skips the drawtext burn-in entirely (nothing to caption).
    """
    vf_base = _zoompan_filter(motion, duration_seconds, OUTPUT_FPS)
    vf = f"{vf_base},{_drawtext_filter(caption_name)}" if caption_name else vf_base

    if audio_name:
        audio_input = ["-i", audio_name]
    else:
        audio_input = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

    cmd = [
        _ffmpeg_binary(), "-y",
        "-loop", "1", "-i", image_name,
        *audio_input,
        "-t", str(duration_seconds),
        "-vf", vf,
        "-r", str(OUTPUT_FPS),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        clip_name,
    ]
    _run(cmd, "scene_animation", cwd=job_dir)


def _concat_clips(clip_paths: List[Path], job_dir: Path, final_path: Path) -> None:
    concat_list_path = job_dir / "concat_list.txt"
    concat_list_path.write_text(
        "\n".join(f"file '{p.name}'" for p in clip_paths), encoding="utf-8"
    )
    cmd = [
        _ffmpeg_binary(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        str(final_path),
    ]
    _run(cmd, "assembly")


def _probe_final_output(final_path: Path, require_audio: bool = False) -> Tuple[float, bool]:
    """
    Returns (duration_seconds, has_audio_stream). Raises VideoGenerationError if the
    file is missing/empty, has no video stream, reports zero duration, or (when
    require_audio=True -- i.e. narration was requested) has no audio stream. A
    "successful" narrated render must never be reported without a real audio track.
    """
    if not final_path.exists() or final_path.stat().st_size == 0:
        raise VideoGenerationError("output_validation", "final.mp4 was not created or is empty.")

    ffprobe_bin = _ffprobe_binary()
    if not ffprobe_bin:
        if require_audio:
            raise VideoGenerationError(
                "output_validation", "ffprobe not found on PATH; cannot verify the required audio stream."
            )
        logger.warning("ffprobe not found on PATH; skipping stream/duration validation.")
        return 0.0, False

    proc = subprocess.run(
        [
            ffprobe_bin, "-v", "error",
            "-show_entries", "format=duration:stream=codec_type",
            "-of", "json", str(final_path),
        ],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        raise VideoGenerationError("output_validation", f"ffprobe failed: {proc.stderr[-500:]}")

    info = json.loads(proc.stdout)
    streams = info.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise VideoGenerationError("output_validation", "final.mp4 has no video stream.")

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if require_audio and not has_audio:
        raise VideoGenerationError(
            "output_validation", "final.mp4 has no audio stream (narration was requested)."
        )

    duration = float(info.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        raise VideoGenerationError("output_validation", "final.mp4 reports zero duration.")
    return duration, has_audio


async def generate_video_mvp(
    script: VideoScript,
    job_id: Optional[str] = None,
    target_duration_seconds: Optional[int] = None,
    narrate: bool = False,
    tts_provider: Optional[VideoTTSProvider] = None,
) -> VideoGenerationResult:
    """
    narrate=False (default) reproduces Phase 1 exactly: silent, image-motion only.
    narrate=True additionally generates real voiceover + burned captions per scene,
    via the team's Voice Agent (VoiceAgentTTSProvider, wrapping voice_service.py's
    gTTS engine) unless a tts_provider is explicitly passed (e.g. SilentTestTTSProvider
    in tests) -- swappable without touching this function's logic.

    A scene with no voiceover (scene.voiceover blank) is treated as an intentional
    silent disclaimer/end-card -- see scene_validator, which only allows this when
    compliance_disclaimer is set. That scene skips the TTS call entirely (never
    synthesizes speech from empty text) but still gets a real, silent audio track
    (FFmpeg anullsrc) so every clip has a uniform stream layout for concatenation,
    and it stays on screen for its full planned duration.
    """
    job_id = job_id or uuid.uuid4().hex[:12]
    job_dir = MEDIA_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    result = VideoGenerationResult(job_id=job_id, success=False)

    # Stage: deterministic target-duration correction (no LLM). See module-level
    # comment on TARGET_DURATION_TOLERANCE for why this is necessary at all.
    if target_duration_seconds:
        rescaled = normalize_scene_durations(script.scenes, target_duration_seconds)
        if rescaled:
            script.target_duration_seconds = target_duration_seconds
            logger.info(
                f"[{job_id}] Rescaled scene durations to match requested "
                f"target_duration={target_duration_seconds}s (was outside tolerance)."
            )

    # Stage: deterministic scene validation (no LLM involved)
    validation = validate_video_script(script)
    if not validation.valid:
        result.error_stage = "validation"
        result.error_message = "; ".join(validation.errors)
        logger.error(f"[{job_id}] Scene validation failed: {result.error_message}")
        return result

    # Stage: narration-duration budgeting (no TTS call yet). Estimates each narrated
    # scene's spoken length from word count and rewrites any scene whose narration
    # would overrun its own on-screen time -- see narration_budget.py. Only relevant
    # when TTS will actually run; the silent Phase 1 path never reads voiceover text.
    narration_report = None
    if narrate:
        narration_report = enforce_narration_budget(script)
        if narration_report.any_rewritten:
            # Requirement: revalidate after rewriting -- a rewrite should never
            # produce an empty/invalid voiceover, but this is the explicit safety net.
            revalidation = validate_video_script(script)
            if not revalidation.valid:
                result.error_stage = "narration_budget"
                result.error_message = (
                    "Narration rewrite produced an invalid script: " + "; ".join(revalidation.errors)
                )
                logger.error(f"[{job_id}] {result.error_message}")
                return result
            logger.info(
                f"[{job_id}] Narration budgeting rewrote "
                f"{sum(1 for s in narration_report.scenes if s.was_rewritten)} scene(s) to fit "
                f"target_duration={target_duration_seconds or script.target_duration_seconds}s."
            )

    if narrate and tts_provider is None:
        tts_provider = VoiceAgentTTSProvider(language=script.language or "en")

    image_provider: VideoProvider = ImageMotionProvider()
    sources: List[str] = []
    clip_paths: List[Path] = []
    audio_sources: List[str] = []
    scene_texts_and_durations: List[Tuple[str, float]] = []  # for the global caption track

    for idx, scene in enumerate(script.scenes):
        image_path = job_dir / f"scene_{scene.scene_number:03d}.png"
        # Step 8: a disclaimer/legal end-card scene is a deterministic branded card,
        # never a real AI image -- it never touches the configured AI provider (never
        # spends an API call/cost on a scene whose visual is a fixed compliance card).
        is_disclaimer_scene = bool((scene.compliance_disclaimer or "").strip())
        try:
            if is_disclaimer_scene:
                visual = await BrandedFallbackProvider().generate_scene_visual(scene, script.brand or "jade", image_path)
            else:
                visual = await image_provider.generate_scene_visual(scene, script.brand or "jade", image_path)
        except Exception as e:
            result.error_stage = "image_generation"
            result.error_message = f"scene {scene.scene_number}: {e}"
            logger.error(f"[{job_id}] {result.error_message}")
            return result
        sources.append(visual.source)
        result.scene_image_reports.append(SceneImageReport(
            scene_number=scene.scene_number,
            source=visual.source,
            is_real_ai=visual.source in (SOURCE_AI_GENERATED, SOURCE_HUGGINGFACE, SOURCE_GEMINI, SOURCE_STABLE_DIFFUSION),
            provider=visual.provider,
            model=visual.model,
            provider_error=visual.provider_error,
        ))

        clip_path = job_dir / f"scene_{scene.scene_number:03d}.mp4"

        if not narrate:
            # --- Phase 1 path, byte-for-byte unchanged ---
            try:
                _render_scene_clip(image_path, clip_path, scene.duration_seconds, _camera_motion_for(idx))
            except VideoGenerationError as e:
                result.error_stage = e.stage
                result.error_message = f"scene {scene.scene_number}: {e.message}"
                logger.error(f"[{job_id}] {result.error_message}")
                return result
            clip_paths.append(clip_path)
            continue

        # --- Silent disclaimer/end-card scene: no TTS call on empty text. Validated
        # upstream (scene_validator) to only be allowed when compliance_disclaimer is
        # set. Still gets a real (silent) audio track so concat sees a uniform
        # video+audio layout across every clip, and keeps its full planned duration. ---
        voiceover_text = (scene.voiceover or "").strip()
        if not voiceover_text:
            try:
                _render_narrated_scene_clip(
                    job_dir, image_path.name, None, None,
                    clip_path.name, scene.duration_seconds, _camera_motion_for(idx),
                )
            except VideoGenerationError as e:
                result.error_stage = e.stage
                result.error_message = f"scene {scene.scene_number}: {e.message}"
                logger.error(f"[{job_id}] {result.error_message}")
                return result
            clip_paths.append(clip_path)
            logger.info(f"[{job_id}] Scene {scene.scene_number} is a silent disclaimer/end-card -- skipped TTS.")
            continue

        # --- Phase 2 path: voiceover, measured duration, burned caption ---
        audio_path = job_dir / f"scene_{scene.scene_number:03d}.mp3"
        try:
            await tts_provider.generate_voiceover(voiceover_text, audio_path)
            audio_duration = _probe_audio_duration(audio_path)
        except (TTSGenerationError, VideoGenerationError) as e:
            message = e.message if hasattr(e, "message") else str(e)
            result.error_stage = "tts"
            result.error_message = f"scene {scene.scene_number}: {message}"
            logger.error(f"[{job_id}] {result.error_message}")
            return result
        except Exception as e:
            result.error_stage = "tts"
            result.error_message = f"scene {scene.scene_number}: unexpected TTS error: {e}"
            logger.error(f"[{job_id}] {result.error_message}")
            return result

        audio_sources.append(tts_provider.name)
        # Measured audio duration is authoritative for narrated scenes -- never the
        # originally-planned duration_seconds. Keep the precise float for rendering/
        # captions; store a rounded int back on the scene for a sane reported value.
        scene.duration_seconds = max(1, round(audio_duration))
        scene_texts_and_durations.append((voiceover_text, audio_duration))

        local_cue = caption_service.build_local_cue(voiceover_text, audio_duration)
        local_srt_validation = caption_service.validate_srt([local_cue], total_duration_seconds=audio_duration)
        if not local_srt_validation.valid:
            result.error_stage = "captions"
            result.error_message = f"scene {scene.scene_number}: {'; '.join(local_srt_validation.errors)}"
            logger.error(f"[{job_id}] {result.error_message}")
            return result

        caption_path = job_dir / f"scene_{scene.scene_number:03d}.srt"
        # drawtext's textfile= renders raw text, not the numbered/timestamped SRT
        # format -- write just the caption line for burn-in; the real .srt (with
        # index + timestamps) is the separate global captions.srt artifact below.
        caption_path.write_text(voiceover_text, encoding="utf-8")

        try:
            _render_narrated_scene_clip(
                job_dir, image_path.name, audio_path.name, caption_path.name,
                clip_path.name, audio_duration, _camera_motion_for(idx),
            )
        except VideoGenerationError as e:
            result.error_stage = e.stage
            result.error_message = f"scene {scene.scene_number}: {e.message}"
            logger.error(f"[{job_id}] {result.error_message}")
            return result
        clip_paths.append(clip_path)

    final_path = job_dir / "final.mp4"
    try:
        _concat_clips(clip_paths, job_dir, final_path)
        duration, has_audio = _probe_final_output(final_path, require_audio=narrate)
    except VideoGenerationError as e:
        result.error_stage = e.stage
        result.error_message = e.message
        logger.error(f"[{job_id}] {result.error_message}")
        return result

    caption_file_url = None
    if narrate:
        global_cues = caption_service.build_scene_cues(scene_texts_and_durations)
        global_validation = caption_service.validate_srt(global_cues, total_duration_seconds=duration)
        if not global_validation.valid:
            result.error_stage = "captions"
            result.error_message = "; ".join(global_validation.errors)
            logger.error(f"[{job_id}] {result.error_message}")
            return result
        captions_path = job_dir / "captions.srt"
        captions_path.write_text(caption_service.render_srt(global_cues), encoding="utf-8")
        caption_file_url = f"/media/generated/{job_id}/captions.srt"

    result.success = True
    result.video_path = final_path
    result.video_url = f"/media/generated/{job_id}/final.mp4"
    result.duration_seconds = round(duration, 2)
    result.scenes_generated = len(clip_paths)
    result.has_audio = has_audio
    result.has_captions = bool(caption_file_url)
    result.caption_file = caption_file_url
    if narrate:
        result.audio_source = audio_sources[0] if audio_sources else None
        result.audio_duration_seconds = round(duration, 2)
    if narration_report is not None:
        result.narration_word_count = sum(s.final_word_count for s in narration_report.scenes)
        result.narration_estimated_seconds = round(narration_report.total_estimated_seconds, 2)
        result.narration_rewritten = narration_report.any_rewritten

    result.ai_generated_scene_count = sum(1 for r in result.scene_image_reports if r.is_real_ai)
    result.fallback_scene_count = sum(1 for r in result.scene_image_reports if not r.is_real_ai)

    # Generalized over however many distinct provider sources actually appear across
    # scenes (SOURCE_AI_GENERATED, SOURCE_HUGGINGFACE, SOURCE_FALLBACK, or any future
    # provider's source string) -- not hard-coded to the OpenAI/fallback pair, so
    # adding another real image provider never silently mislabels its result.
    distinct_sources = list(dict.fromkeys(sources))
    if len(distinct_sources) == 1:
        result.image_source_summary = distinct_sources[0]
    else:
        breakdown = ", ".join(f"{sources.count(src)}x {src}" for src in distinct_sources)
        result.image_source_summary = f"mixed ({breakdown})"

    logger.info(
        f"[{job_id}] Video generation completed: {final_path} "
        f"({result.duration_seconds}s, {result.scenes_generated} scenes, source={result.image_source_summary}, "
        f"narrated={narrate}, has_audio={result.has_audio}, has_captions={result.has_captions})"
    )
    return result
