"""
Phase 3 image-provider hardening tests: explicit REAL_AI_IMAGE/FALLBACK_IMAGE/
PROVIDER_FAILURE classification, transient-vs-permanent error handling with bounded
retry, Pillow-based image validation, per-scene image provenance reporting, the
disclaimer-scene-never-uses-AI rule, and 9:16 cover-crop (not stretch) rendering.

All external APIs are mocked (httpx.AsyncClient for OpenAI, HuggingFaceImageProvider.
_call_inference_client for Hugging Face) -- no real network calls, no credentials
required to run this file.
"""
import io
import json
import subprocess
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.services.video_providers import (
    OpenAIImageProvider,
    HuggingFaceImageProvider,
    BrandedFallbackProvider,
    ImageGenerationError,
    ImagePermanentError,
    ImageTransientError,
    SOURCE_AI_GENERATED,
    SOURCE_HUGGINGFACE,
    SOURCE_FALLBACK,
)
from app.services.video_generation_service import (
    _zoompan_filter,
    _render_scene_clip,
    _probe_final_output,
    generate_video_mvp,
)
from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe
from tests.test_video_generation import _make_scene, _make_script


def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)
FFPROBE_AVAILABLE = _binary_available(resolve_ffprobe)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _valid_png_bytes(size=(16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(10, 40, 34)).save(buf, format="PNG")
    return buf.getvalue()


def _openai_response(status_code: int, body_json: dict = None, body_text: str = None) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    if body_json is not None:
        return httpx.Response(status_code=status_code, json=body_json, request=request)
    return httpx.Response(status_code=status_code, content=(body_text or "").encode(), request=request)


# ---------------------------------------------------------------------------
# 1/2. Successful OpenAI / Hugging Face responses report provider + model
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_success_reports_source_provider_and_model(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")

    async def fake_generate_ai_image(self, scene, brand, output_path):
        output_path.write_bytes(_valid_png_bytes())

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", fake_generate_ai_image)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_AI_GENERATED
    assert result.provider == "openai_image"
    assert result.model == "gpt-image-1"
    assert result.provider_error is None


@pytest.mark.anyio
async def test_huggingface_success_reports_source_provider_and_model(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")
    monkeypatch.setattr("app.config.settings.HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")

    class _FakeImage:
        def save(self, path):
            Path(path).write_bytes(_valid_png_bytes())

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", lambda self, prompt: _FakeImage())

    result = await HuggingFaceImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_HUGGINGFACE
    assert result.provider == "huggingface_image"
    assert result.model == "black-forest-labs/FLUX.1-dev"


def test_huggingface_requests_explicit_916_dimensions(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")
    captured = {}

    class _FakeInferenceClient:
        def __init__(self, token):
            pass

        def text_to_image(self, prompt, model=None, width=None, height=None):
            captured["width"] = width
            captured["height"] = height

            class _Img:
                def save(self, path):
                    Path(path).write_bytes(_valid_png_bytes())
            return _Img()

    monkeypatch.setattr("huggingface_hub.InferenceClient", _FakeInferenceClient)

    provider = HuggingFaceImageProvider()
    provider._call_inference_client("a prompt")

    assert captured["width"] == 720
    assert captured["height"] == 1280


# ---------------------------------------------------------------------------
# 3. Invalid image bytes -- transient, retried once, then fallback/raise
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_invalid_image_bytes_retries_then_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        import base64
        garbage_b64 = base64.b64encode(b"not a real image, just garbage bytes").decode()
        return _openai_response(200, body_json={"data": [{"b64_json": garbage_b64}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2  # one retry attempted for corrupt bytes
    assert "corrupt" in result.provider_error.lower()


@pytest.mark.anyio
async def test_huggingface_invalid_image_bytes_is_never_returned_as_success(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")

    class _CorruptImage:
        def save(self, path):
            Path(path).write_bytes(b"not a real image at all")

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", lambda self, prompt: _CorruptImage())

    with pytest.raises(ImageTransientError, match="corrupt"):
        await HuggingFaceImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")


# ---------------------------------------------------------------------------
# 4. Empty/malformed image response -- OpenAI side (HF's empty-file case already
#    covered by test_image_providers.py::test_huggingface_empty_result_file_is_treated_as_failure)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_empty_data_array_is_permanent_malformed_response(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        return _openai_response(200, body_json={"data": []})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 1  # malformed response is permanent -- never retried
    assert "malformed" in result.provider_error.lower()


# ---------------------------------------------------------------------------
# 5. Authentication failure -- permanent, no retry
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_auth_failure_401_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "invalid-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        return _openai_response(401, body_text="Incorrect API key provided")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 1
    assert "authentication" in result.provider_error.lower()


@pytest.mark.anyio
async def test_huggingface_auth_failure_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "invalid-token")
    call_count = {"n": 0}

    class _FakeHttpResponse:
        status_code = 401
        text = "Invalid user token"

    def failing_call(self, prompt):
        call_count["n"] += 1
        err = RuntimeError("401 Client Error: Unauthorized")
        err.response = _FakeHttpResponse()
        raise err

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", failing_call)

    with pytest.raises(ImagePermanentError, match="authentication failed"):
        await HuggingFaceImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")
    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# 6. Quota failure -- mirrors the REAL failures observed in live verification
#    (OpenAI 429 "insufficient_quota"; HF 402 "depleted your monthly included credits")
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_insufficient_quota_429_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        return _openai_response(429, body_json={"error": {"code": "insufficient_quota", "message": "You exceeded your quota"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 1  # quota exhaustion is permanent, unlike true rate limiting
    assert "quota" in result.provider_error.lower()


@pytest.mark.anyio
async def test_openai_true_rate_limit_429_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        return _openai_response(429, body_json={"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2  # genuine rate limiting is retried once before falling back


@pytest.mark.anyio
async def test_huggingface_quota_exhausted_402_is_permanent_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")
    call_count = {"n": 0}

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise RuntimeError(
            "402 Payment Required: You have depleted your monthly included credits. "
            "Purchase pre-paid credits to continue using Inference Providers."
        )

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", failing_call)

    with pytest.raises(ImagePermanentError, match="quota/credits exhausted"):
        await HuggingFaceImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")
    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# 7. Timeout -- transient, retried
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_timeout_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        raise httpx.ConnectTimeout("connection timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2


@pytest.mark.anyio
async def test_huggingface_timeout_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")
    call_count = {"n": 0}

    def failing_call(self, prompt):
        call_count["n"] += 1
        raise TimeoutError("request timed out after 60s")

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", failing_call)

    with pytest.raises(ImageTransientError, match="timed out"):
        await HuggingFaceImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")
    assert call_count["n"] == 2  # retried once before giving up


# ---------------------------------------------------------------------------
# 8. Provider unavailable (5xx) -- transient, retried
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_server_error_503_is_transient_and_retried(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        return _openai_response(503, body_text="Service temporarily unavailable")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# 9/10. Fallback behavior + correct image_source metadata across a real multi-
#       scene pipeline run (one scene succeeds via AI, the next fails permanently)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_scene_image_reports_distinguish_real_ai_from_fallback(monkeypatch, tmp_path):
    from app.services import video_generation_service as vgs

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    call_count = {"n": 0}

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            import base64
            png_b64 = base64.b64encode(_valid_png_bytes()).decode()
            return _openai_response(200, body_json={"data": [{"b64_json": png_b64}]})
        return _openai_response(401, body_text="Incorrect API key provided")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    scenes = [_make_scene(scene_number=1), _make_scene(scene_number=2)]
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(script, job_id="scene-report-test", narrate=False)

    assert result.success is True, result.error_message
    assert result.ai_generated_scene_count == 1
    assert result.fallback_scene_count == 1

    reports = {r.scene_number: r for r in result.scene_image_reports}
    assert reports[1].is_real_ai is True
    assert reports[1].source == SOURCE_AI_GENERATED
    assert reports[1].provider_error is None

    assert reports[2].is_real_ai is False
    assert reports[2].source == SOURCE_FALLBACK
    assert reports[2].provider_error is not None
    assert "authentication" in reports[2].provider_error.lower()


# ---------------------------------------------------------------------------
# 11/12. Per-scene generation, and a silent/disclaimer scene never touches the
#        configured AI provider (Step 8)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_disclaimer_scene_never_calls_configured_ai_provider(monkeypatch, tmp_path):
    from app.services import video_generation_service as vgs

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    call_count = {"n": 0}

    async def fake_generate_ai_image(self, scene, brand, output_path):
        call_count["n"] += 1
        output_path.write_bytes(_valid_png_bytes())

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", fake_generate_ai_image)

    scenes = [
        _make_scene(scene_number=1),
        _make_scene(
            scene_number=2, voiceover="",
            compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*",
        ),
    ]
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(script, job_id="disclaimer-no-ai-test", narrate=False)

    assert result.success is True, result.error_message
    assert call_count["n"] == 1  # the AI provider ran only for scene 1, never scene 2

    reports = {r.scene_number: r for r in result.scene_image_reports}
    assert reports[2].source == SOURCE_FALLBACK
    assert reports[2].provider == "branded_fallback"
    assert reports[2].provider_error is None  # never even attempted a real provider


# ---------------------------------------------------------------------------
# 13. 9:16 rendering compatibility -- cover-crop, not a stretch
# ---------------------------------------------------------------------------

def test_zoompan_filter_uses_cover_crop_not_a_stretch():
    filter_str = _zoompan_filter("zoom_in", 5, 30)
    assert "force_original_aspect_ratio=increase" in filter_str
    assert "crop=2160:3840" in filter_str


@pytest.mark.skipif(not FFMPEG_AVAILABLE or not FFPROBE_AVAILABLE, reason="ffmpeg/ffprobe not installed")
def test_mismatched_aspect_ratio_source_still_renders_to_exact_target_dimensions(tmp_path):
    # A deliberately square source image, like a text-to-image model's default
    # output (e.g. FLUX.1-dev without explicit width/height) -- the pipeline must
    # still produce exactly 1080x1920 without distorting/stretching it.
    image_path = tmp_path / "scene_001.png"
    Image.new("RGB", (1024, 1024), color=(50, 100, 150)).save(image_path)
    clip_path = tmp_path / "scene_001.mp4"

    _render_scene_clip(image_path, clip_path, 3, "zoom_in")
    duration, _ = _probe_final_output(clip_path, require_audio=False)
    assert duration > 0

    proc = subprocess.run(
        [resolve_ffprobe(), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(clip_path)],
        capture_output=True, text=True, timeout=30,
    )
    info = json.loads(proc.stdout)
    assert info["streams"][0]["width"] == 1080
    assert info["streams"][0]["height"] == 1920
