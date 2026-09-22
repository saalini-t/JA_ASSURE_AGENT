"""
Stable Diffusion 1.5 (local) image provider tests. Mocks
LocalSD15ImageProvider._generate_image_local directly -- the real method lazily
imports torch/diffusers and loads model weights, none of which this test suite
requires (torch/diffusers are confirmed NOT installed in this environment; the
missing-dependency test below relies on that real absence rather than mocking
ImportError). No GPU and no model download are ever needed to run these tests.
"""
import io

import pytest
from PIL import Image

from app.services.video_providers import (
    LocalSD15ImageProvider,
    ImagePermanentError,
    ImageTransientError,
    SOURCE_STABLE_DIFFUSION,
    SOURCE_GEMINI,
    SOURCE_HUGGINGFACE,
)
from tests.test_video_generation import _make_scene


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_pil_image(size=(512, 768)) -> Image.Image:
    return Image.new("RGB", size, color=(30, 20, 10))


# ---------------------------------------------------------------------------
# Successful generation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_successful_generation_reports_source_provider_and_model(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.SD15_MODEL_PATH", "runwayml/stable-diffusion-v1-5")
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _fake_pil_image())

    result = await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert result.source == SOURCE_STABLE_DIFFUSION
    assert result.source not in (SOURCE_GEMINI, SOURCE_HUGGINGFACE)  # never claims a cloud provider
    assert result.provider == "stable_diffusion_1_5"
    assert result.model == "runwayml/stable-diffusion-v1-5"
    assert result.provider_error is None


@pytest.mark.anyio
async def test_generated_image_is_persisted_and_openable(monkeypatch, tmp_path):
    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _fake_pil_image((512, 768)))

    output_path = tmp_path / "scene_001.png"
    await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert output_path.exists()
    with Image.open(output_path) as img:
        img.load()
        assert img.size == (512, 768)


def test_uses_configured_model_path(monkeypatch):
    monkeypatch.setattr("app.config.settings.SD15_MODEL_PATH", "/local/models/my-sd15-checkpoint")
    assert LocalSD15ImageProvider().model_path == "/local/models/my-sd15-checkpoint"


def test_default_model_path_when_unconfigured(monkeypatch):
    monkeypatch.setattr("app.config.settings.SD15_MODEL_PATH", "")
    assert LocalSD15ImageProvider().model_path == LocalSD15ImageProvider.DEFAULT_MODEL_PATH


# ---------------------------------------------------------------------------
# Configurable generation parameters actually reach the pipeline call
# ---------------------------------------------------------------------------

def test_generation_parameters_are_read_from_settings(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.SD15_NUM_INFERENCE_STEPS", 42)
    monkeypatch.setattr("app.config.settings.SD15_GUIDANCE_SCALE", 9.5)
    monkeypatch.setattr("app.config.settings.SD15_WIDTH", 576)
    monkeypatch.setattr("app.config.settings.SD15_HEIGHT", 1024)
    monkeypatch.setattr("app.config.settings.SD15_SEED", -1)

    captured = {}

    class _FakePipeline:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            class _Result:
                images = [_fake_pil_image()]
            return _Result()

    monkeypatch.setattr(LocalSD15ImageProvider, "_get_or_load_pipeline", classmethod(lambda cls: _FakePipeline()))

    provider = LocalSD15ImageProvider()
    provider._generate_image_local("a test prompt")

    assert captured["num_inference_steps"] == 42
    assert captured["guidance_scale"] == 9.5
    assert captured["width"] == 576
    assert captured["height"] == 1024
    assert captured["prompt"] == "a test prompt"
    assert "generator" not in captured  # seed=-1 means no fixed generator


# ---------------------------------------------------------------------------
# Missing dependencies -- typed PERMANENT failure (uses the real absence of
# torch/diffusers in this environment, not a mocked ImportError)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_missing_dependencies_raise_typed_permanent_error(tmp_path, monkeypatch):
    # Forces the ImportError regardless of whether torch/diffusers are actually
    # installed in this environment (they now are, for the real local-GPU path) --
    # same technique the CUDA-unavailable test below uses, so this test's outcome
    # never depends on ambient machine state.
    import sys
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "diffusers", None)
    LocalSD15ImageProvider._pipeline = None  # ensure no cached pipeline from another test
    with pytest.raises(ImagePermanentError, match="diffusers/torch are not installed"):
        await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")


# ---------------------------------------------------------------------------
# CUDA requested but unavailable -- typed PERMANENT failure
# ---------------------------------------------------------------------------

def test_cuda_requested_but_unavailable_is_permanent(monkeypatch):
    # The CUDA-availability check runs only after torch AND diffusers both import
    # successfully, so both need faking here -- otherwise this would (correctly)
    # hit the missing-dependency path instead, since diffusers genuinely isn't
    # installed in this environment.
    import sys
    import types

    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: False), float16="f16", float32="f32",
    )
    fake_diffusers = types.SimpleNamespace(StableDiffusionPipeline=object())
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "diffusers", fake_diffusers)
    monkeypatch.setattr("app.config.settings.SD15_DEVICE", "cuda")
    LocalSD15ImageProvider._pipeline = None

    with pytest.raises(ImagePermanentError, match="no CUDA device is available"):
        LocalSD15ImageProvider._get_or_load_pipeline()


# ---------------------------------------------------------------------------
# CUDA out of memory -- typed TRANSIENT failure (worth one retry)
# ---------------------------------------------------------------------------

def test_out_of_memory_is_classified_transient():
    from app.services.video_providers import _classify_sd15_error
    err = _classify_sd15_error(RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB"))
    assert isinstance(err, ImageTransientError)


def test_model_load_failure_is_classified_permanent():
    from app.services.video_providers import _classify_sd15_error
    err = _classify_sd15_error(OSError("model.safetensors not found at path"))
    assert isinstance(err, ImagePermanentError)


@pytest.mark.anyio
async def test_generation_failure_retries_then_raises(monkeypatch, tmp_path):
    call_count = {"n": 0}

    def failing_generate(self, prompt):
        call_count["n"] += 1
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", failing_generate)

    with pytest.raises(ImageTransientError):
        await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")

    assert call_count["n"] == 2  # one bounded retry for a transient OOM


# ---------------------------------------------------------------------------
# Invalid/corrupt image bytes never accepted as success
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_corrupt_output_is_never_accepted_as_success(monkeypatch, tmp_path):
    class _FakeCorruptImage:
        def save(self, path):
            from pathlib import Path
            Path(path).write_bytes(b"not a real image")

    monkeypatch.setattr(LocalSD15ImageProvider, "_generate_image_local", lambda self, prompt: _FakeCorruptImage())

    with pytest.raises(ImageTransientError, match="corrupt"):
        await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", tmp_path / "scene.png")


# ---------------------------------------------------------------------------
# Never silently degrades to a fake success -- raises like Hugging Face, no
# internal fallback-to-branded of its own (the cascade decides that, not this
# provider)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_failure_raises_explicitly_never_a_silent_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(
        LocalSD15ImageProvider, "_generate_image_local",
        lambda self, prompt: (_ for _ in ()).throw(RuntimeError("simulated generation failure")),
    )
    output_path = tmp_path / "scene.png"

    with pytest.raises(ImagePermanentError):
        await LocalSD15ImageProvider().generate_scene_visual(_make_scene(), "jade", output_path)

    assert not output_path.exists()  # no placeholder file written by this provider itself
