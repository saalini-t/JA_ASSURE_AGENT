"""
Phase 1 video pipeline tests: scene validation (deterministic), the visual provider's
AI/fallback resilience contract, FFmpeg scene animation + assembly, and final-output
validation. No TTS/captions/compliance/HITL/publishing -- out of scope for this phase.
"""
import uuid
from pathlib import Path

import pytest

from app.schemas.agent_contracts import VideoScript, VideoScene
from app.services.scene_validator import validate_video_script
from app.services.video_providers import ImageMotionProvider, SOURCE_AI_GENERATED, SOURCE_FALLBACK
from app.services import video_generation_service as vgs
from app.services.video_generation_service import (
    VideoGenerationError,
    _render_scene_clip,
    _concat_clips,
    _probe_final_output,
    generate_video_mvp,
    normalize_scene_durations,
)

def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


# Use the app's own robust resolver (PATH, then *_PATH env vars, then the Windows
# install-location fallback) -- not a bare shutil.which() -- so these tests reflect
# whether the app can ACTUALLY find FFmpeg, not just whether it's on this shell's PATH.
from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe

FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)
FFPROBE_AVAILABLE = _binary_available(resolve_ffprobe)


def _make_scene(**overrides) -> VideoScene:
    defaults = dict(
        scene_number=1,
        duration_seconds=5,
        visual_description="A diamond ring on velvet.",
        voiceover="Protect what matters most.",
        onscreen_text="Agreed-Value Protection",
        transition="Cut",
    )
    defaults.update(overrides)
    return VideoScene(**defaults)


def _make_script(scenes=None, **overrides) -> VideoScript:
    defaults = dict(
        title="Test Video",
        brand="jade",
        target_platform="reel",
        disclaimer="*Terms and conditions apply.*",
        scenes=scenes if scenes is not None else [_make_scene()],
    )
    defaults.update(overrides)
    return VideoScript(**defaults)


# ---------------------------------------------------------------------------
# A/B/C/D. Scene validator
# ---------------------------------------------------------------------------

def test_a_valid_video_script_passes_validation():
    script = _make_script(scenes=[
        _make_scene(scene_number=1),
        _make_scene(scene_number=2, duration_seconds=6),
    ])
    result = validate_video_script(script)
    assert result.valid is True
    assert result.errors == []


def test_b_empty_scenes_fails_validation():
    script = _make_script(scenes=[])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("scenes list is empty" in e for e in result.errors)


def test_c_missing_scene_fields_fails_validation():
    script = _make_script(scenes=[_make_scene(voiceover="", onscreen_text="")])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("voiceover is missing or empty" in e for e in result.errors)
    assert any("onscreen_text is missing or empty" in e for e in result.errors)


def test_d_zero_or_negative_duration_fails_validation():
    script = _make_script(scenes=[_make_scene(duration_seconds=0)])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("duration_seconds must be positive" in e for e in result.errors)

    script_negative = _make_script(scenes=[_make_scene(duration_seconds=-3)])
    result_negative = validate_video_script(script_negative)
    assert result_negative.valid is False


def test_scene_count_over_max_fails_validation():
    scenes = [_make_scene(scene_number=i, duration_seconds=5) for i in range(1, 8)]  # 7 scenes
    script = _make_script(scenes=scenes)
    result = validate_video_script(script)
    assert result.valid is False
    assert any("outside the allowed range" in e for e in result.errors)


def test_missing_disclaimer_fails_validation():
    script = _make_script(disclaimer=None)
    result = validate_video_script(script)
    assert result.valid is False
    assert any("disclaimer is missing or empty" in e for e in result.errors)


# ---------------------------------------------------------------------------
# E/F. Image provider resilience contract
#
# NOTE: ImageMotionProvider is now a provider-SELECTOR facade (see
# video_providers.py) that delegates to OpenAIImageProvider by default -- the real
# OpenAI-calling logic and its is_configured/_generate_ai_image internals moved to
# OpenAIImageProvider when HuggingFaceImageProvider was added alongside it. These
# tests were updated to patch/inspect the delegate directly; the BEHAVIOR they
# verify (ImageMotionProvider() end to end, defaulting to OpenAI) is unchanged.
# Equivalent, more granular provider-level tests also live in test_image_providers.py.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_e_image_provider_success_uses_ai_path(tmp_path, monkeypatch):
    from app.services.video_providers import OpenAIImageProvider

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key-for-test")
    provider = ImageMotionProvider()

    async def fake_generate_ai_image(self, scene, brand, output_path):
        # A genuinely decodable minimal PNG -- Phase 3's Pillow-based image
        # validation rejects fake header-only bytes as corrupt.
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (16, 16), color=(10, 40, 34)).save(buf, format="PNG")
        output_path.write_bytes(buf.getvalue())

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", fake_generate_ai_image)

    scene = _make_scene()
    out_path = tmp_path / "scene_001.png"
    result = await provider.generate_scene_visual(scene, "jade", out_path)

    assert result.source == SOURCE_AI_GENERATED
    assert out_path.exists()
    assert out_path.stat().st_size > 0


@pytest.mark.anyio
async def test_f_image_provider_failure_falls_back_and_is_labeled(tmp_path, monkeypatch):
    from app.services.video_providers import OpenAIImageProvider

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key-for-test")
    provider = ImageMotionProvider()

    async def failing_generate_ai_image(self, scene, brand, output_path):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", failing_generate_ai_image)

    scene = _make_scene()
    out_path = tmp_path / "scene_001.png"
    result = await provider.generate_scene_visual(scene, "jade", out_path)

    assert result.source == SOURCE_FALLBACK
    assert out_path.exists()
    assert out_path.stat().st_size > 0


@pytest.mark.anyio
async def test_no_credential_uses_fallback_directly(tmp_path, monkeypatch):
    from app.services.video_providers import OpenAIImageProvider

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    provider = ImageMotionProvider()
    assert isinstance(provider._delegate, OpenAIImageProvider)
    assert provider._delegate.is_configured is False

    scene = _make_scene()
    out_path = tmp_path / "scene_001.png"
    result = await provider.generate_scene_visual(scene, "jade", out_path)

    assert result.source == SOURCE_FALLBACK
    assert out_path.exists()


# ---------------------------------------------------------------------------
# G/H. FFmpeg scene animation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_g_ffmpeg_scene_animation_success(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    provider = ImageMotionProvider()
    image_path = tmp_path / "scene_001.png"
    await provider.generate_scene_visual(_make_scene(), "jade", image_path)

    clip_path = tmp_path / "scene_001.mp4"
    _render_scene_clip(image_path, clip_path, duration_seconds=1, motion="zoom_in")

    assert clip_path.exists()
    assert clip_path.stat().st_size > 0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
def test_h_ffmpeg_failure_on_missing_input(tmp_path):
    missing_image = tmp_path / "does_not_exist.png"
    clip_path = tmp_path / "out.mp4"
    with pytest.raises(VideoGenerationError) as exc_info:
        _render_scene_clip(missing_image, clip_path, duration_seconds=1, motion="zoom_in")
    assert exc_info.value.stage == "scene_animation"


def test_h_ffmpeg_binary_not_found_reports_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(vgs, "_ffmpeg_binary", lambda: "ffmpeg_binary_that_does_not_exist_anywhere")
    with pytest.raises(VideoGenerationError) as exc_info:
        _render_scene_clip(tmp_path / "img.png", tmp_path / "out.mp4", 1, "zoom_in")
    assert exc_info.value.stage == "scene_animation"
    assert "not found on PATH" in exc_info.value.message


# ---------------------------------------------------------------------------
# I. Final MP4 validation + full pipeline
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_i_full_pipeline_produces_valid_final_mp4(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # exercise fallback path, no network needed
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[
        _make_scene(scene_number=1, duration_seconds=3),
        _make_scene(scene_number=2, duration_seconds=3, visual_description="A vault door closing."),
    ])

    job_id = uuid.uuid4().hex[:8]
    result = await generate_video_mvp(script, job_id=job_id)

    assert result.success is True, result.error_message
    assert result.video_path is not None
    assert result.video_path.exists()
    assert result.video_path.stat().st_size > 0
    assert result.duration_seconds > 0
    assert result.scenes_generated == 2
    assert result.image_source_summary == "branded_fallback_demo"
    assert result.video_url == f"/media/generated/{job_id}/final.mp4"


def test_i_probe_rejects_missing_file(tmp_path):
    with pytest.raises(VideoGenerationError) as exc_info:
        _probe_final_output(tmp_path / "does_not_exist.mp4")
    assert exc_info.value.stage == "output_validation"


@pytest.mark.anyio
async def test_invalid_script_fails_before_any_generation_work(tmp_path, monkeypatch):
    """Validation must short-circuit before touching the image provider or FFmpeg at all."""
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)
    script = _make_script(scenes=[])  # invalid: no scenes

    result = await generate_video_mvp(script, job_id="invalid-test")

    assert result.success is False
    assert result.error_stage == "validation"
    assert result.scenes_generated == 0


# ---------------------------------------------------------------------------
# Regression: target_duration was silently ignored (media_service's deterministic
# fallback hard-codes scene durations summing to ~45s regardless of the requested
# target_duration parameter -- confirmed by inspection of
# MediaService._generate_deterministic_video_script, which accepts target_duration
# but never reads it). normalize_scene_durations() is the deterministic fix.
# ---------------------------------------------------------------------------

def test_k_normalize_scene_durations_rescales_when_outside_tolerance():
    scenes = [
        _make_scene(scene_number=1, duration_seconds=10),
        _make_scene(scene_number=2, duration_seconds=12),
        _make_scene(scene_number=3, duration_seconds=13),
        _make_scene(scene_number=4, duration_seconds=10),
    ]  # sums to 45s, matching the real reported bug

    rescaled = normalize_scene_durations(scenes, target_duration=30)

    assert rescaled is True
    total = sum(s.duration_seconds for s in scenes)
    assert 30 * 0.85 <= total <= 30 * 1.15  # within the 15% tolerance
    assert all(s.duration_seconds >= 1 for s in scenes)  # never collapses a scene to 0


def test_k_normalize_scene_durations_is_a_noop_within_tolerance():
    """Deterministic means: already-acceptable durations are left exactly alone."""
    scenes = [_make_scene(scene_number=1, duration_seconds=14), _make_scene(scene_number=2, duration_seconds=15)]
    original = [s.duration_seconds for s in scenes]

    rescaled = normalize_scene_durations(scenes, target_duration=30)  # 29s is within 15% of 30s

    assert rescaled is False
    assert [s.duration_seconds for s in scenes] == original


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_k_target_duration_regression_end_to_end(tmp_path, monkeypatch):
    """
    Reproduces the exact reported bug: request target_duration=30 against scenes
    that (like the real deterministic fallback) sum to 45s, and confirm the
    rendered video's actual duration lands within tolerance of 30s, not 45s.
    """
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[
        _make_scene(scene_number=1, duration_seconds=10),
        _make_scene(scene_number=2, duration_seconds=12),
        _make_scene(scene_number=3, duration_seconds=13),
        _make_scene(scene_number=4, duration_seconds=10),
    ])  # 45s total, exactly like the reported bug

    result = await generate_video_mvp(script, job_id="target-duration-regression", target_duration_seconds=30)

    assert result.success is True, result.error_message
    assert 30 * 0.85 <= result.duration_seconds <= 30 * 1.15


@pytest.fixture
def anyio_backend():
    return "asyncio"
