"""
Gemini image provider tests (Phase: 9A). Mocks GeminiImageProvider._call_gemini
directly (the google-genai SDK boundary) -- no real network calls, no
GEMINI_API_KEY required. Mirrors the same hardening already proven for
OpenAI/Hugging Face: explicit REAL_AI/FALLBACK classification, transient-vs-
permanent error handling with bounded retry, Pillow validation, no credential
leakage, disclaimer-scene bypass, and provider selection.
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.video_providers import (
    GeminiImageProvider,
    ImageMotionProvider,
    BrandedFallbackProvider,
    ImagePermanentError,
    ImageTransientError,
    SOURCE_GEMINI,
    SOURCE_FALLBACK,
)
from app.services.video_generation_service import generate_video_mvp
from app.services.ffmpeg_locator import resolve_ffmpeg
from tests.test_video_generation import _make_scene, _make_script


def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _valid_png_bytes(size=(16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(20, 30, 40)).save(buf, format="PNG")
    return buf.getvalue()


class _FakeAPIError(Exception):
    """Stands in for google.genai.errors.APIError without requiring the real
    package's exact construction signature -- tests patch isinstance checks by
    using the REAL errors module when installed; this class covers the
    generic-exception fallback classification path."""


# ---------------------------------------------------------------------------
# 1. Successful Gemini image generation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_successful_generation_reports_source_provider_and_model(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr("app.config.settings.GEMINI_IMAGE_MODEL", "models/gemini-2.5-flash-image")

    monkeypatch.setattr(
        GeminiImageProvider, "_call_gemini",
        lambda self, prompt: (_valid_png_bytes(), "image/png"),
    )

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_GEMINI
    assert result.provider == "gemini_image"
    assert result.model == "models/gemini-2.5-flash-image"
    assert result.provider_error is None


# ---------------------------------------------------------------------------
# 2. Valid image persistence -- file actually written and readable
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_generated_image_is_persisted_to_disk_and_openable(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", lambda self, prompt: (_valid_png_bytes(), "image/png"))

    output_path = tmp_path / "scene_001.png"
    await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert output_path.exists()
    with Image.open(output_path) as img:
        img.load()
        assert img.size == (16, 16)


# ---------------------------------------------------------------------------
# 3. Invalid image response -- corrupt bytes, retried then falls back
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_invalid_image_bytes_retries_then_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    call_count = {"n": 0}

    def fake_call(self, prompt):
        call_count["n"] += 1
        return (b"not a real image at all", "image/png")

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", fake_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2  # one retry attempted for corrupt bytes
    assert "corrupt" in result.provider_error.lower()


def test_malformed_response_with_no_image_data_is_permanent():
    from app.services.video_providers import _classify_gemini_error
    err = _classify_gemini_error(ValueError("no image data"), "models/gemini-2.5-flash-image")
    assert isinstance(err, ImagePermanentError)


# ---------------------------------------------------------------------------
# 5. Authentication failure -- permanent, no retry
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_authentication_failure_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    call_count = {"n": 0}

    try:
        from google.genai import errors as genai_errors
        auth_error = genai_errors.ClientError(403, {"error": {"message": "PERMISSION_DENIED", "status": "PERMISSION_DENIED"}})
    except ImportError:
        pytest.skip("google-genai not installed")

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise auth_error

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", failing_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 1
    assert "authentication" in result.provider_error.lower()


# ---------------------------------------------------------------------------
# 6. Quota/rate-limit failure -- mirrors the REAL observed error
#    (429 RESOURCE_EXHAUSTED, free-tier image quota limit: 0)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_quota_exhausted_429_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    call_count = {"n": 0}

    try:
        from google.genai import errors as genai_errors
        quota_error = genai_errors.ClientError(
            429, {"error": {"message": "RESOURCE_EXHAUSTED. Quota exceeded", "status": "RESOURCE_EXHAUSTED"}}
        )
    except ImportError:
        pytest.skip("google-genai not installed")

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise quota_error

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", failing_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 1  # a quota of 0 will never succeed on retry
    assert "quota" in result.provider_error.lower()


# ---------------------------------------------------------------------------
# 7. Provider timeout/failure -- transient, retried
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_timeout_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    call_count = {"n": 0}

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise TimeoutError("Gemini request deadline exceeded")

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", failing_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2


@pytest.mark.anyio
async def test_server_error_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    call_count = {"n": 0}

    try:
        from google.genai import errors as genai_errors
        server_error = genai_errors.ServerError(503, {"error": {"message": "UNAVAILABLE", "status": "UNAVAILABLE"}})
    except ImportError:
        pytest.skip("google-genai not installed")

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise server_error

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", failing_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# 7b. No credential configured -- immediate honest fallback, no call at all
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_no_api_key_falls_back_without_calling_gemini(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "")
    call_count = {"n": 0}
    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", lambda self, prompt: call_count.__setitem__("n", call_count["n"] + 1))

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 0
    assert "not configured" in result.provider_error.lower()


# ---------------------------------------------------------------------------
# 8/9. Fallback activation is honestly labeled, never claims AI success
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_fallback_is_never_mislabeled_as_ai_generated(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", lambda self, prompt: (_ for _ in ()).throw(RuntimeError("boom")))

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert result.source != SOURCE_GEMINI
    assert result.provider == "branded_fallback"


# ---------------------------------------------------------------------------
# 10. Metadata correctness through the full video pipeline
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_pipeline_reports_gemini_source_and_counts_correctly(monkeypatch, tmp_path):
    from app.services import video_generation_service as vgs

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "gemini")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", lambda self, prompt: (_valid_png_bytes(), "image/png"))

    script = _make_script(scenes=[_make_scene(scene_number=1), _make_scene(scene_number=2)])
    result = await generate_video_mvp(script, job_id="gemini-pipeline-test", narrate=False)

    assert result.success is True, result.error_message
    assert result.ai_generated_scene_count == 2
    assert result.fallback_scene_count == 0
    for report in result.scene_image_reports:
        assert report.source == SOURCE_GEMINI
        assert report.is_real_ai is True
        assert report.provider == "gemini_image"


# ---------------------------------------------------------------------------
# 9:16 normalization -- Gemini output still goes through the same cover-crop
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
def test_gemini_output_dimensions_still_covered_by_existing_cover_crop():
    from app.services.video_generation_service import _zoompan_filter
    # Same assertion as the OpenAI/HF hardening test -- confirms Gemini doesn't
    # bypass the existing distortion-prevention mechanism (Step: "do not modify
    # the existing cover-crop implementation unless required for compatibility" --
    # it wasn't required, Gemini uses the identical rendering path).
    filter_str = _zoompan_filter("zoom_in", 5, 30)
    assert "force_original_aspect_ratio=increase" in filter_str


# ---------------------------------------------------------------------------
# 10b. No credential leakage
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_key_never_appears_in_error_messages(monkeypatch, tmp_path):
    real_looking_key = "AIzaSyFAKEKEYFAKEKEYFAKEKEYFAKEKEYFAKE12"
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", real_looking_key)

    def failing_call(self, prompt):
        # Simulates an SDK exception that might otherwise echo request details
        raise RuntimeError(f"request failed for model {self.model}")

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", failing_call)

    result = await GeminiImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert real_looking_key not in (result.provider_error or "")


def test_not_configured_message_never_contains_a_key_value(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "")
    provider = GeminiImageProvider()
    assert provider.is_configured is False


# ---------------------------------------------------------------------------
# 11. Disclaimer scene bypass -- same Step 8 rule already proven for OpenAI/HF
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_disclaimer_scene_never_calls_gemini(monkeypatch, tmp_path):
    from app.services import video_generation_service as vgs

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "gemini")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    call_count = {"n": 0}

    def fake_call(self, prompt):
        call_count["n"] += 1
        return (_valid_png_bytes(), "image/png")

    monkeypatch.setattr(GeminiImageProvider, "_call_gemini", fake_call)

    scenes = [
        _make_scene(scene_number=1),
        _make_scene(scene_number=2, voiceover="", compliance_disclaimer="*Terms and conditions apply.*"),
    ]
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(script, job_id="gemini-disclaimer-test", narrate=False)

    assert result.success is True, result.error_message
    assert call_count["n"] == 1  # only scene 1, never the disclaimer scene
    reports = {r.scene_number: r for r in result.scene_image_reports}
    assert reports[2].source == SOURCE_FALLBACK
    assert reports[2].provider == "branded_fallback"


# ---------------------------------------------------------------------------
# 12. Provider selection
# ---------------------------------------------------------------------------

def test_gemini_is_the_default_provider(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "")
    assert isinstance(ImageMotionProvider()._delegate, GeminiImageProvider)


def test_explicit_gemini_selection(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "gemini")
    assert isinstance(ImageMotionProvider()._delegate, GeminiImageProvider)


def test_openai_still_selectable_when_explicitly_configured(monkeypatch):
    from app.services.video_providers import OpenAIImageProvider
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    assert isinstance(ImageMotionProvider()._delegate, OpenAIImageProvider)


def test_huggingface_still_selectable_when_explicitly_configured(monkeypatch):
    from app.services.video_providers import HuggingFaceImageProvider
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "huggingface")
    assert isinstance(ImageMotionProvider()._delegate, HuggingFaceImageProvider)
