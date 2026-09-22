"""
Image provider CASCADE tests: ImageMotionProvider's default ("auto") behavior now
tries Gemini -> Hugging Face -> Stable Diffusion 1.5 (local) -> Branded fallback
in order, stopping at the first real success -- confirming the exact scenario
"if Gemini and Hugging Face both fail, does it go to Stable Diffusion?" (yes).

All providers mocked at their real generation boundary (never the public
generate_scene_visual for Gemini/OpenAI, since THAT has its own internal
graceful-degrade which would short-circuit the cascade before it ever reaches
the next tier -- exactly the failure mode these tests exist to catch).
"""
import pytest
from PIL import Image

from app.services.video_providers import (
    ImageMotionProvider,
    GeminiImageProvider,
    HuggingFaceImageProvider,
    LocalSD15ImageProvider,
    BrandedFallbackProvider,
    SOURCE_GEMINI,
    SOURCE_HUGGINGFACE,
    SOURCE_STABLE_DIFFUSION,
    SOURCE_FALLBACK,
)
from tests.test_video_generation import _make_scene


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_image():
    return Image.new("RGB", (16, 16), color=(1, 2, 3))


def test_auto_is_the_default_and_unset_value(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "")
    providers = ImageMotionProvider()._providers
    assert [p.name for p in providers] == [
        "gemini_image", "huggingface_image", "stable_diffusion_1_5", "branded_fallback",
    ]


def test_explicit_auto_selection(monkeypatch):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    providers = ImageMotionProvider()._providers
    assert len(providers) == 4


@pytest.mark.anyio
async def test_gemini_succeeds_cascade_never_touches_other_providers(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")

    async def succeeding_gemini(self, scene, brand, output_path):
        output_path.write_bytes(_png_bytes())

    monkeypatch.setattr(GeminiImageProvider, "_generate_and_save", succeeding_gemini)

    hf_called = {"n": 0}
    monkeypatch.setattr(HuggingFaceImageProvider, "generate_scene_visual", _fail_and_count(hf_called))

    result = await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_GEMINI
    assert hf_called["n"] == 0  # never even attempted


@pytest.mark.anyio
async def test_gemini_fails_falls_through_to_huggingface(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")

    async def failing_gemini(self, scene, brand, output_path):
        raise RuntimeError("simulated Gemini quota exhaustion")

    monkeypatch.setattr(GeminiImageProvider, "_generate_and_save", failing_gemini)

    async def succeeding_hf(self, prompt, output_path):
        output_path.write_bytes(_png_bytes())

    monkeypatch.setattr(HuggingFaceImageProvider, "_generate_and_save", succeeding_hf)

    sd15_called = {"n": 0}
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", _fail_local_and_count(sd15_called))

    result = await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_HUGGINGFACE
    assert sd15_called["n"] == 0  # Stable Diffusion never even attempted


@pytest.mark.anyio
async def test_gemini_and_huggingface_both_fail_falls_through_to_stable_diffusion(monkeypatch, tmp_path):
    """The exact scenario this feature was requested for: Gemini AND Hugging Face
    both fail -> the local Stable Diffusion 1.5 provider is tried next."""
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")

    async def failing_gemini(self, scene, brand, output_path):
        raise RuntimeError("simulated Gemini quota exhaustion")

    monkeypatch.setattr(GeminiImageProvider, "_generate_and_save", failing_gemini)

    async def failing_hf(self, prompt, output_path):
        raise RuntimeError("simulated Hugging Face credit exhaustion")

    monkeypatch.setattr(HuggingFaceImageProvider, "_generate_and_save", failing_hf)
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _fake_image())

    result = await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_STABLE_DIFFUSION
    assert result.source not in (SOURCE_GEMINI, SOURCE_HUGGINGFACE)
    assert result.provider == "stable_diffusion_1_5"


@pytest.mark.anyio
async def test_all_three_real_providers_fail_uses_branded_fallback_honestly(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "fake-token")

    async def failing_gemini(self, scene, brand, output_path):
        raise RuntimeError("simulated Gemini failure")

    async def failing_hf(self, prompt, output_path):
        raise RuntimeError("simulated Hugging Face failure")

    def failing_sd15(self, prompt):
        raise RuntimeError("simulated Stable Diffusion failure")

    monkeypatch.setattr(GeminiImageProvider, "_generate_and_save", failing_gemini)
    monkeypatch.setattr(HuggingFaceImageProvider, "_generate_and_save", failing_hf)
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", failing_sd15)

    result = await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_FALLBACK
    assert result.provider == "branded_fallback"
    assert result.source not in (SOURCE_GEMINI, SOURCE_HUGGINGFACE, SOURCE_STABLE_DIFFUSION)


@pytest.mark.anyio
async def test_no_credentials_at_all_cascades_straight_to_stable_diffusion(monkeypatch, tmp_path):
    """Gemini/HF unconfigured (no API keys) still count as failures for cascade
    purposes -- moves straight to the local, credential-free provider."""
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "")
    monkeypatch.setattr("app.config.settings.HF_TOKEN", "")
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _fake_image())

    result = await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_STABLE_DIFFUSION


@pytest.mark.anyio
async def test_explicit_stable_diffusion_selection_skips_the_cascade(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "stable_diffusion")
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _fake_image())

    provider = ImageMotionProvider()
    assert len(provider._providers) == 1
    assert isinstance(provider._providers[0], LocalSD15ImageProvider)

    result = await provider.generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")
    assert result.source == SOURCE_STABLE_DIFFUSION


def _png_bytes() -> bytes:
    import io
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=(4, 5, 6)).save(buf, format="PNG")
    return buf.getvalue()


def _fail_and_count(counter):
    async def _inner(self, scene, brand, output_path):
        counter["n"] += 1
        raise RuntimeError("should never be called")
    return _inner


def _fail_local_and_count(counter):
    def _inner(self, prompt):
        counter["n"] += 1
        raise RuntimeError("should never be called")
    return _inner
