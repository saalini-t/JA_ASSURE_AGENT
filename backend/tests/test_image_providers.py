"""
Tests for the multi-provider image generation architecture
(app/services/video_providers.py): provider selection, the new
HuggingFaceImageProvider, and confirmation that OpenAIImageProvider /
BrandedFallbackProvider still behave exactly as before the refactor.
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.video_providers import (
    VideoProvider,
    ImageMotionProvider,
    OpenAIImageProvider,
    HuggingFaceImageProvider,
    BrandedFallbackProvider,
    ImageGenerationError,
    SOURCE_AI_GENERATED,
    SOURCE_HUGGINGFACE,
    SOURCE_FALLBACK,
    build_scene_image_prompt,
)

from tests.test_video_generation import _make_scene


def _valid_png_bytes(size=(16, 16)) -> bytes:
    """A genuinely decodable minimal PNG -- Phase 3's Pillow-based image validation
    (_validate_image_file) rejects fake header-only bytes as corrupt, so test fixtures
    that simulate a successful provider response need real, openable image data."""
    buf = io.BytesIO()
    Image.new("RGB", size, color=(10, 40, 34)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# HuggingFace provider initialization
# ---------------------------------------------------------------------------

def test_huggingface_provider_implements_the_common_interface():
    assert issubclass(HuggingFaceImageProvider, VideoProvider)
    provider = HuggingFaceImageProvider()
    assert provider.name == "huggingface_image"


def test_huggingface_provider_default_model(monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_IMAGE_MODEL", "")
    provider = HuggingFaceImageProvider()
    assert provider.model == "black-forest-labs/FLUX.1-dev"


def test_huggingface_provider_uses_configured_model(monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_IMAGE_MODEL", "some-org/some-other-model")
    provider = HuggingFaceImageProvider()
    assert provider.model == "some-org/some-other-model"


# ---------------------------------------------------------------------------
# Missing HF_TOKEN
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_missing_hf_token_raises_explicit_error(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "")
    provider = HuggingFaceImageProvider()
    assert provider.is_configured is False

    with pytest.raises(ImageGenerationError, match="HF_TOKEN is not configured"):
        await provider.generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")


# ---------------------------------------------------------------------------
# Mocked successful image generation
# ---------------------------------------------------------------------------

class _FakePILImage:
    """Stands in for a real PIL.Image.Image returned by InferenceClient.text_to_image."""
    def __init__(self):
        self.saved_to = None

    def save(self, path):
        Path(path).write_bytes(_valid_png_bytes())
        self.saved_to = path


@pytest.mark.anyio
async def test_mocked_successful_huggingface_generation_writes_a_real_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-hf-token-for-test")
    provider = HuggingFaceImageProvider()

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", lambda self, prompt: _FakePILImage())

    output_path = tmp_path / "scene_001.png"
    result = await provider.generate_scene_visual(_make_scene(), "jade", output_path)

    assert result.source == SOURCE_HUGGINGFACE
    assert output_path.exists()
    assert output_path.stat().st_size > 0


@pytest.mark.anyio
async def test_prompt_sent_to_huggingface_excludes_voiceover_and_includes_brand_style(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-hf-token-for-test")
    provider = HuggingFaceImageProvider()

    captured_prompts = []

    def fake_call(self, prompt):
        captured_prompts.append(prompt)
        return _FakePILImage()

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", fake_call)

    scene = _make_scene(voiceover="This exact sentence must never reach the image model.")
    await provider.generate_scene_visual(scene, "jade", tmp_path / "scene.png")

    assert len(captured_prompts) == 1
    assert scene.visual_description in captured_prompts[0]
    assert "9:16" in captured_prompts[0]
    assert "This exact sentence must never reach the image model." not in captured_prompts[0]


# ---------------------------------------------------------------------------
# Mocked Hugging Face API failure -> explicit error, never a fake success
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_mocked_huggingface_failure_raises_explicitly_not_a_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-hf-token-for-test")
    provider = HuggingFaceImageProvider()

    def failing_call(self, prompt):
        raise RuntimeError("simulated Hugging Face API failure (e.g. 503 model loading)")

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", failing_call)

    output_path = tmp_path / "scene_001.png"
    # Phase 3: error classification is now specific (this message pattern is
    # recognized as a transient "model unavailable/loading" condition) rather than
    # the old generic wrapper text -- still an ImageGenerationError, never a fallback.
    with pytest.raises(ImageGenerationError, match="Hugging Face model unavailable/loading"):
        await provider.generate_scene_visual(_make_scene(), "jade", output_path)

    # Critically: no branded card was silently written and mislabeled as AI-generated.
    assert not output_path.exists()


@pytest.mark.anyio
async def test_huggingface_empty_result_file_is_treated_as_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-hf-token-for-test")
    provider = HuggingFaceImageProvider()

    class _EmptyImage:
        def save(self, path):
            Path(path).touch()  # zero-byte file

    monkeypatch.setattr(HuggingFaceImageProvider, "_call_inference_client", lambda self, prompt: _EmptyImage())

    with pytest.raises(ImageGenerationError, match="empty file"):
        await provider.generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")


# ---------------------------------------------------------------------------
# Provider selection (ImageMotionProvider delegates based on settings.IMAGE_PROVIDER)
# ---------------------------------------------------------------------------

def test_selects_openai_by_default(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "openai")
    assert isinstance(ImageMotionProvider()._delegate, OpenAIImageProvider)


def test_selects_huggingface_when_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "huggingface")
    assert isinstance(ImageMotionProvider()._delegate, HuggingFaceImageProvider)


def test_selects_branded_fallback_when_explicitly_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "branded_fallback")
    assert isinstance(ImageMotionProvider()._delegate, BrandedFallbackProvider)


def test_selection_is_case_insensitive_and_defaults_on_unknown_value(monkeypatch):
    from app.services.video_providers import GeminiImageProvider

    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "HuggingFace")
    assert isinstance(ImageMotionProvider()._delegate, HuggingFaceImageProvider)

    # Phase: Gemini is now the default/fallback for an unrecognized value -- it
    # became the PRIMARY AI visual provider, superseding OpenAI as the default.
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "something_unrecognized")
    assert isinstance(ImageMotionProvider()._delegate, GeminiImageProvider)


@pytest.mark.anyio
async def test_image_motion_provider_delegates_generate_scene_visual(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "branded_fallback")
    provider = ImageMotionProvider()

    result = await provider.generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert provider.name == "branded_fallback"


# ---------------------------------------------------------------------------
# Existing OpenAI provider still works (post-refactor)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_openai_provider_still_generates_real_image_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key-for-test")

    async def fake_generate_ai_image(self, scene, brand, output_path):
        output_path.write_bytes(_valid_png_bytes())

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", fake_generate_ai_image)

    output_path = tmp_path / "scene.png"
    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert result.source == SOURCE_AI_GENERATED
    assert output_path.exists() and output_path.stat().st_size > 0


@pytest.mark.anyio
async def test_openai_provider_still_gracefully_falls_back_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key-for-test")

    async def failing_generate_ai_image(self, scene, brand, output_path):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(OpenAIImageProvider, "_generate_ai_image", failing_generate_ai_image)

    output_path = tmp_path / "scene.png"
    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert result.source == SOURCE_FALLBACK  # unchanged Phase 1 graceful-degradation behavior
    assert output_path.exists()


@pytest.mark.anyio
async def test_openai_provider_uses_fallback_without_credential(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    result = await OpenAIImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")
    assert result.source == SOURCE_FALLBACK


# ---------------------------------------------------------------------------
# Existing branded fallback still works (post-refactor, and as an explicit choice)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_branded_fallback_provider_produces_a_labeled_image(tmp_path):
    output_path = tmp_path / "scene.png"
    result = await BrandedFallbackProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert result.source == SOURCE_FALLBACK
    assert output_path.exists() and output_path.stat().st_size > 0


def test_build_scene_image_prompt_includes_style_and_composition_not_voiceover():
    scene = _make_scene(voiceover="Never include this narration line in the prompt.")
    prompt = build_scene_image_prompt(scene, "doctorshield")

    assert scene.visual_description in prompt
    assert "9:16" in prompt
    assert "Never include this narration line in the prompt." not in prompt


@pytest.fixture
def anyio_backend():
    return "asyncio"
