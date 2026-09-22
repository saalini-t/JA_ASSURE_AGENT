"""
Visual asset generation for video scenes.

VideoProvider is the interface every scene-visual generator implements. Each
concrete provider produces ONE STILL IMAGE per scene (the FFmpeg assembly step in
video_generation_service.py is what adds camera motion). A future ComfyUIWanProvider
(native video-clip generation, not stills) could implement the same interface --
video_generation_service.py only needs a valid image file path back, never cares how
the pixels were produced.

Concrete providers:
  - OpenAIImageProvider: OpenAI Images API (unchanged from Phase 1). On failure,
    gracefully degrades to BrandedFallbackProvider -- this existing behavior is
    preserved exactly as-is.
  - HuggingFaceImageProvider: Hugging Face Inference Providers via huggingface_hub's
    InferenceClient (new). On failure, raises explicitly -- it never pretends a
    branded card is an AI-generated result.
  - BrandedFallbackProvider: deterministic, clearly-labeled placeholder card. Used
    automatically by OpenAIImageProvider on failure/no-credential, and available as
    an explicitly-selected provider (IMAGE_PROVIDER=branded_fallback) for fast,
    credential-free testing/demos.

ImageMotionProvider is a thin provider-SELECTOR: it's what video_generation_service.py
actually instantiates (unchanged call site), and it picks the concrete provider above
based on settings.IMAGE_PROVIDER. This is what let the video pipeline itself require
zero changes to gain a second real AI image vendor.
"""
import asyncio
import base64
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import httpx
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app.config import settings
from app.schemas.agent_contracts import VideoScene

logger = logging.getLogger("ja_assure.video.providers")

FALLBACK_CANVAS_SIZE = (1080, 1920)

# Exact 9:16 resolution requested from Hugging Face (both dimensions multiples of 16,
# a common diffusion-model constraint) -- lets FLUX generate a true 9:16 image
# directly instead of relying entirely on the FFmpeg cover-crop fit. OpenAI's
# Images API has no exact-9:16 size option (see OpenAIImageProvider._generate_ai_image);
# the FFmpeg cover-crop is what protects against distortion for that provider.
HF_TARGET_WIDTH = 720
HF_TARGET_HEIGHT = 1280

SOURCE_AI_GENERATED = "ai_generated_openai"
SOURCE_HUGGINGFACE = "huggingface"
SOURCE_GEMINI = "gemini"
SOURCE_STABLE_DIFFUSION = "stable_diffusion_1_5"
SOURCE_FALLBACK = "branded_fallback_demo"

# Bounded retry policy for TRANSIENT provider/validation failures only (timeout,
# connection error, 5xx, rate limiting, corrupt/invalid image bytes). Permanent
# failures (missing/invalid credential, quota/billing exhausted, malformed request)
# are never retried -- see ImagePermanentError vs ImageTransientError below.
_MAX_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = 0.3

# Per-brand visual style, layered onto scene.visual_description for image prompts.
# Deliberately excludes the scene's voiceover text -- that's narration copy, not a
# visual instruction, and stuffing it into the prompt produces worse, more literal
# (and sometimes text-in-image) results from diffusion/photo models.
_BRAND_VISUAL_STYLE = {
    "jade": "luxury editorial photography, warm gold and deep emerald tones, quiet opulence, shallow depth of field",
    "doctorshield": "clean clinical editorial photography, calm and trustworthy, soft blue and white palette",
    "jaguartransit": "cinematic industrial photography, secure and commanding, dark amber and steel tones",
}


class ImageGenerationError(Exception):
    """Raised by a provider when it fails and must NOT be silently treated as success."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ImagePermanentError(ImageGenerationError):
    """Not worth retrying: missing/invalid credential, quota/billing exhausted,
    authorization failure, or a malformed request/response."""


class ImageTransientError(ImageGenerationError):
    """Safe to retry a bounded number of times: timeout, connection error, 5xx,
    rate limiting, or a corrupt/invalid image file from an otherwise-successful call."""


async def _retry_transient(async_fn, max_attempts: int = _MAX_ATTEMPTS, backoff_seconds: float = _RETRY_BACKOFF_SECONDS):
    """
    Calls async_fn() up to max_attempts times, retrying only ImageTransientError with
    a short backoff. ImagePermanentError (and anything else) propagates immediately --
    never retry an authentication/quota failure or an unclassified error.
    """
    last_error: Optional[ImageTransientError] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await async_fn()
        except ImageTransientError as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning(f"Transient image generation error (attempt {attempt}/{max_attempts}): {e.message}. Retrying...")
                await asyncio.sleep(backoff_seconds * attempt)
                continue
    raise last_error


def _validate_image_file(path: Path) -> None:
    """
    Step 5 image validation: exists, non-zero size, genuinely decodable by Pillow
    (catches truncated/corrupt bytes), and has sane non-zero dimensions. Raises
    ImageTransientError -- a fresh generation attempt is a reasonable mitigation for
    corrupt bytes, unlike a genuinely permanent credential/quota failure.
    """
    if not path.exists() or path.stat().st_size == 0:
        raise ImageTransientError(f"Generated image file is missing or empty: {path.name}")
    try:
        with Image.open(path) as img:
            img.load()  # fully decodes pixel data; raises on truncated/corrupt files
            width, height = img.size
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ImageTransientError(f"Generated image file is corrupt or not a valid image: {e}")
    if width <= 0 or height <= 0:
        raise ImageTransientError(f"Generated image has invalid dimensions: {width}x{height}")


def build_scene_image_prompt(scene: VideoScene, brand: str) -> str:
    """
    Combines the scene's visual description with brand style, vertical composition,
    and photography direction -- NOT the scene's full voiceover.
    """
    style = _BRAND_VISUAL_STYLE.get(brand, "cinematic editorial photography, professional and polished")
    return (
        f"{scene.visual_description}. "
        f"{style}, vertical 9:16 composition, photorealistic, high-end commercial "
        f"photography, no on-image text, no watermarks, no logos."
    )


class SceneVisualResult:
    def __init__(
        self, path: Path, source: str, provider: str = "", model: Optional[str] = None,
        provider_error: Optional[str] = None,
    ):
        self.path = path
        self.source = source  # SOURCE_AI_GENERATED | SOURCE_HUGGINGFACE | SOURCE_FALLBACK
        self.provider = provider  # concrete provider that actually produced this image
        self.model = model  # model name/id, when the provider used a specific one
        # Set when a DIFFERENT provider was originally attempted and failed before
        # falling back (e.g. OpenAIImageProvider's graceful degradation) -- None
        # when the provider that ran is the one that succeeded outright.
        self.provider_error = provider_error


class VideoProvider(ABC):
    """Interface every scene-visual generator (real or future) must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        """Write a still image to output_path and return where it came from."""
        ...


class BrandedFallbackProvider(VideoProvider):
    """
    Deterministic, clearly-labeled placeholder card -- explicitly NOT AI-generated.
    Used automatically when OpenAIImageProvider has no credential or fails, and
    available as an explicit, credential-free provider choice
    (IMAGE_PROVIDER=branded_fallback) for fast testing/demos.
    """

    @property
    def name(self) -> str:
        return "branded_fallback"

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._generate_fallback_card(scene, brand, output_path)
        return SceneVisualResult(path=output_path, source=SOURCE_FALLBACK, provider=self.name)

    def _generate_fallback_card(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        from app.services.content_service import BRAND_PERSONAS

        persona = BRAND_PERSONAS.get(brand, BRAND_PERSONAS["jade"])
        brand_colors = {
            "jade": (10, 40, 34),
            "doctorshield": (10, 26, 46),
            "jaguartransit": (36, 20, 10),
        }
        bg = brand_colors.get(brand, (20, 20, 20))

        w, h = FALLBACK_CANVAS_SIZE
        img = Image.new("RGB", (w, h), color=bg)
        draw = ImageDraw.Draw(img)

        title_font, body_font, label_font = self._load_fonts()

        draw.text((60, int(h * 0.08)), persona["title"].upper(), font=title_font, fill=(230, 200, 120))
        draw.text((60, int(h * 0.18)), f"Scene {scene.scene_number}", font=body_font, fill=(255, 255, 255))

        wrapped = self._wrap_text(scene.visual_description, body_font, w - 120)
        y = int(h * 0.35)
        for line in wrapped:
            draw.text((60, y), line, font=body_font, fill=(220, 220, 220))
            y += 44

        label = "FALLBACK VISUAL -- NOT AI-GENERATED (DEMO MODE)"
        draw.rectangle([(0, h - 90), (w, h)], fill=(120, 20, 20))
        draw.text((30, h - 68), label, font=label_font, fill=(255, 255, 255))

        img.save(output_path, "PNG")

    @staticmethod
    def _load_fonts():
        try:
            title_font = ImageFont.truetype("arial.ttf", 54)
            body_font = ImageFont.truetype("arial.ttf", 36)
            label_font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        return title_font, body_font, label_font

    @staticmethod
    def _wrap_text(text: str, font: "ImageFont.ImageFont", max_width: int) -> List[str]:
        words = text.split()
        lines: List[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            bbox = font.getbbox(trial)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        return lines[:8]


def _classify_gemini_error(e: Exception, model: str) -> ImageGenerationError:
    try:
        from google.genai import errors as genai_errors
    except ImportError:
        genai_errors = None

    if genai_errors is not None and isinstance(e, genai_errors.APIError):
        code = e.code
        status = (e.status or "").upper()
        message = str(e)[:300]
        if code in (401, 403) or status in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
            return ImagePermanentError(f"Gemini authentication failed ({code} {status}, model={model}): {message}")
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            return ImagePermanentError(f"Gemini quota exhausted ({code} {status}, model={model}): {message}")
        if status == "INVALID_ARGUMENT":
            return ImagePermanentError(f"Gemini invalid request ({code} {status}, model={model}): {message}")
        if code and code >= 500:
            return ImageTransientError(f"Gemini server error ({code} {status}, model={model}): {message}")
        if status in ("UNAVAILABLE", "DEADLINE_EXCEEDED"):
            return ImageTransientError(f"Gemini temporarily unavailable ({code} {status}, model={model}): {message}")
        return ImagePermanentError(f"Gemini request error ({code} {status}, model={model}): {message}")

    message = str(e)
    message_lower = message.lower()
    if "timeout" in message_lower or "deadline" in message_lower:
        return ImageTransientError(f"Gemini request timed out (model={model}): {message[:300]}")
    if "connection" in message_lower:
        return ImageTransientError(f"Gemini connection failed (model={model}): {message[:300]}")
    return ImagePermanentError(f"Gemini image generation failed (model={model}): {message[:300]}")


class GeminiImageProvider(VideoProvider):
    """
    Real AI image generation via Google's Gemini image-generation models
    (google-genai SDK) -- the PRIMARY AI visual provider (see
    ImageMotionProvider._select_provider's default), chosen specifically because it
    doesn't depend on OpenAI Images API quota or Hugging Face Inference Provider
    credits. Same transient/permanent error classification and bounded retry as
    OpenAI/Hugging Face. On failure it gracefully degrades to BrandedFallbackProvider
    -- the same design as OpenAIImageProvider (not Hugging Face's hard-fail design)
    since Gemini is now the default most callers will hit with no credential
    configured at all; the fallback is never reported as AI-generated regardless.
    """

    DEFAULT_MODEL = "models/gemini-2.5-flash-image"

    @property
    def name(self) -> str:
        return "gemini_image"

    @property
    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    @property
    def model(self) -> str:
        configured = settings.GEMINI_IMAGE_MODEL or self.DEFAULT_MODEL
        return configured if configured.startswith("models/") else f"models/{configured}"

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        error_message: Optional[str] = None

        if self.is_configured:
            try:
                await _retry_transient(lambda: self._generate_and_save(scene, brand, output_path))
                return SceneVisualResult(path=output_path, source=SOURCE_GEMINI, provider=self.name, model=self.model)
            except ImageGenerationError as e:
                error_message = e.message
                logger.warning(
                    f"Gemini image generation failed for scene {scene.scene_number}: {error_message}. "
                    f"Using branded fallback card instead."
                )
            except Exception as e:
                error_message = str(e)
                logger.warning(
                    f"Gemini image generation failed unexpectedly for scene {scene.scene_number}: {error_message}. "
                    f"Using branded fallback card instead."
                )
        else:
            error_message = "GEMINI_API_KEY is not configured."
            logger.info(
                f"No GEMINI_API_KEY configured; scene {scene.scene_number} will use the "
                f"branded fallback card (demo mode), not a real AI-generated image."
            )

        fallback = await BrandedFallbackProvider().generate_scene_visual(scene, brand, output_path)
        fallback.provider_error = error_message
        return fallback

    async def _generate_and_save(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        prompt = build_scene_image_prompt(scene, brand)
        try:
            image_bytes, _mime_type = await asyncio.to_thread(self._call_gemini, prompt)
        except ImageGenerationError:
            raise
        except Exception as e:
            raise _classify_gemini_error(e, self.model)

        if not image_bytes:
            raise ImageTransientError("Gemini image generation returned no image data.")

        output_path.write_bytes(image_bytes)
        _validate_image_file(output_path)

    def _call_gemini(self, prompt: str):
        # Imported lazily so the rest of this module never depends on google-genai
        # being installed unless this provider is actually used.
        try:
            from google import genai
        except ImportError as e:
            raise ImagePermanentError(
                "google-genai is not installed. Run `pip install -r requirements.txt`."
            ) from e

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(model=self.model, contents=prompt)

        if not response.candidates:
            raise ImagePermanentError("Gemini returned no candidates in the response.")

        for part in response.candidates[0].content.parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None and getattr(inline_data, "data", None):
                return inline_data.data, inline_data.mime_type or "image/png"

        raise ImagePermanentError("Gemini response contained no image data (text-only response).")


def _classify_openai_error(e: Exception) -> ImageGenerationError:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        body = e.response.text[:200]
        body_lower = body.lower()
        if status in (401, 403):
            return ImagePermanentError(f"OpenAI authentication failed ({status}): {body}")
        if status == 402 or "insufficient_quota" in body_lower or "billing" in body_lower:
            return ImagePermanentError(f"OpenAI quota/billing error ({status}): {body}")
        if status == 429:
            if "insufficient_quota" in body_lower:
                return ImagePermanentError(f"OpenAI quota exhausted ({status}): {body}")
            return ImageTransientError(f"OpenAI rate limited ({status}): {body}")
        if status >= 500:
            return ImageTransientError(f"OpenAI server error ({status}): {body}")
        return ImagePermanentError(f"OpenAI request error ({status}): {body}")
    if isinstance(e, httpx.TransportError):
        return ImageTransientError(f"OpenAI request failed: {e}")
    if isinstance(e, (KeyError, IndexError, ValueError)):
        return ImagePermanentError(f"OpenAI returned a malformed response: {e}")
    return ImagePermanentError(f"OpenAI image generation failed: {e}")


class OpenAIImageProvider(VideoProvider):
    """
    Real AI image generation via OpenAI's Images API. On missing credential, this
    still gracefully degrades to BrandedFallbackProvider -- unchanged Phase 1
    behavior, preserved exactly. Transient failures (timeout, 5xx, rate limiting,
    corrupt response bytes) get one bounded retry before falling back; permanent
    failures (auth, quota/billing, malformed response) fall back immediately without
    retrying. Either way, the fallback is never reported as AI-generated, and the
    underlying provider error is carried through on the result for the caller to
    surface (see SceneVisualResult.provider_error).
    """

    MODEL = "gpt-image-1"
    # OpenAI's Images API only accepts specific enumerated sizes -- there is no
    # exact 9:16 (1080x1920) option. "1024x1536" (2:3) is the closest portrait size
    # available; video_generation_service's FFmpeg cover-crop (not a stretch) is what
    # protects the final render from distortion against this mismatch.
    SIZE = "1024x1536"

    @property
    def name(self) -> str:
        return "openai_image"

    @property
    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        error_message: Optional[str] = None

        if self.is_configured:
            try:
                await _retry_transient(lambda: self._generate_and_validate(scene, brand, output_path))
                return SceneVisualResult(path=output_path, source=SOURCE_AI_GENERATED, provider=self.name, model=self.MODEL)
            except ImageGenerationError as e:
                error_message = e.message
                logger.warning(
                    f"OpenAI image generation failed for scene {scene.scene_number}: {error_message}. "
                    f"Using branded fallback card instead."
                )
            except Exception as e:
                error_message = str(e)
                logger.warning(
                    f"OpenAI image generation failed unexpectedly for scene {scene.scene_number}: {error_message}. "
                    f"Using branded fallback card instead."
                )
        else:
            error_message = "OPENAI_API_KEY is not configured."
            logger.info(
                f"No OPENAI_API_KEY configured; scene {scene.scene_number} will use the "
                f"branded fallback card (demo mode), not a real AI-generated image."
            )

        fallback = await BrandedFallbackProvider().generate_scene_visual(scene, brand, output_path)
        fallback.provider_error = error_message
        return fallback

    async def _generate_and_validate(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        await self._generate_ai_image(scene, brand, output_path)
        _validate_image_file(output_path)

    async def _generate_ai_image(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        prompt = build_scene_image_prompt(scene, brand)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.MODEL,
                        "prompt": prompt,
                        "size": self.SIZE,
                        "n": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                b64 = data["data"][0]["b64_json"]
                output_path.write_bytes(base64.b64decode(b64))
        except ImageGenerationError:
            raise
        except Exception as e:
            raise _classify_openai_error(e)


def _classify_hf_error(e: Exception, model: str) -> ImageGenerationError:
    response = getattr(e, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        try:
            body = response.text[:200]
        except Exception:
            body = ""
        if status in (401, 403):
            return ImagePermanentError(f"Hugging Face authentication failed ({status}, model={model}): {body}")
        if status == 402:
            return ImagePermanentError(f"Hugging Face quota/credits exhausted ({status}, model={model}): {body}")
        if status == 429:
            return ImageTransientError(f"Hugging Face rate limited ({status}, model={model}): {body}")
        if status and status >= 500:
            return ImageTransientError(f"Hugging Face server error ({status}, model={model}): {body}")
        if status:
            return ImagePermanentError(f"Hugging Face request error ({status}, model={model}): {body}")

    message = str(e).lower()
    if "timeout" in message or "timed out" in message:
        return ImageTransientError(f"Hugging Face request timed out (model={model}): {e}")
    if "connection" in message:
        return ImageTransientError(f"Hugging Face connection failed (model={model}): {e}")
    if "402" in message or "payment required" in message or "credit" in message:
        return ImagePermanentError(f"Hugging Face quota/credits exhausted (model={model}): {e}")
    if "401" in message or "unauthorized" in message or "invalid token" in message:
        return ImagePermanentError(f"Hugging Face authentication failed (model={model}): {e}")
    if "429" in message or "rate limit" in message:
        return ImageTransientError(f"Hugging Face rate limited (model={model}): {e}")
    if "503" in message or "unavailable" in message or "loading" in message:
        return ImageTransientError(f"Hugging Face model unavailable/loading (model={model}): {e}")
    return ImagePermanentError(f"Hugging Face image generation failed (model={model}): {e}")


class HuggingFaceImageProvider(VideoProvider):
    """
    Real AI image generation via Hugging Face Inference Providers
    (huggingface_hub.InferenceClient.text_to_image). Unlike OpenAIImageProvider, this
    provider does NOT silently degrade to the branded card on failure -- it raises
    ImageGenerationError explicitly, per the requirement that a Hugging Face failure
    must never be reported as a successful AI-generated result. Transient failures
    (timeout, 5xx, rate limiting, corrupt image bytes) get one bounded retry;
    permanent failures (auth, quota/credits, malformed request) raise immediately.
    """

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-dev"

    @property
    def name(self) -> str:
        return "huggingface_image"

    @property
    def is_configured(self) -> bool:
        return bool(settings.HF_TOKEN)

    @property
    def model(self) -> str:
        return settings.HF_IMAGE_MODEL or self.DEFAULT_MODEL

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        if not self.is_configured:
            raise ImagePermanentError(
                "HF_TOKEN is not configured. Set it in backend/.env to use the Hugging Face image provider."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = build_scene_image_prompt(scene, brand)

        await _retry_transient(lambda: self._generate_and_save(prompt, output_path))

        return SceneVisualResult(path=output_path, source=SOURCE_HUGGINGFACE, provider=self.name, model=self.model)

    async def _generate_and_save(self, prompt: str, output_path: Path) -> None:
        try:
            image = await asyncio.to_thread(self._call_inference_client, prompt)
            image.save(output_path)
        except ImageGenerationError:
            raise
        except Exception as e:
            raise _classify_hf_error(e, self.model)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ImageTransientError("Hugging Face image generation produced an empty file.")

        _validate_image_file(output_path)

    def _call_inference_client(self, prompt: str) -> "Image.Image":
        # Imported lazily so the rest of this module (OpenAI/branded providers) never
        # depends on huggingface_hub being installed unless this provider is actually used.
        try:
            from huggingface_hub import InferenceClient
        except ImportError as e:
            raise ImagePermanentError(
                "huggingface_hub is not installed. Run `pip install -r requirements.txt`."
            ) from e

        client = InferenceClient(token=settings.HF_TOKEN)
        # Explicit 9:16 target (both dims multiples of 16) so FLUX generates a true
        # vertical composition directly, rather than relying solely on the FFmpeg
        # cover-crop to fix up a mismatched aspect ratio (e.g. FLUX's 1024x1024 default).
        return client.text_to_image(prompt, model=self.model, width=HF_TARGET_WIDTH, height=HF_TARGET_HEIGHT)


def _classify_sd15_error(e: Exception) -> ImageGenerationError:
    message = str(e)
    message_lower = message.lower()
    if "out of memory" in message_lower:
        return ImageTransientError(f"Stable Diffusion CUDA out of memory: {message[:300]}")
    if "cuda" in message_lower and ("not available" in message_lower or "no kernel image" in message_lower):
        return ImagePermanentError(f"Stable Diffusion CUDA error: {message[:300]}")
    if "connection" in message_lower or "timeout" in message_lower or "timed out" in message_lower:
        # Most likely a model-weights download from the Hub (first run, no local
        # cache) hitting a network blip -- worth one retry, unlike a genuinely
        # missing/incompatible local model path.
        return ImageTransientError(f"Stable Diffusion model download/network error: {message[:300]}")
    return ImagePermanentError(f"Stable Diffusion generation failed: {message[:300]}")


class LocalSD15ImageProvider(VideoProvider):
    """
    Local, offline Stable Diffusion 1.5 image generation via the `diffusers`
    library -- third priority tier (after Gemini, Hugging Face): a real AI image
    with zero cloud API dependency or per-call cost when both cloud providers are
    unavailable, before finally settling for the deterministic branded card.

    Heavy dependencies (torch, diffusers) and the model weights are NEVER
    imported/downloaded at module import time or application startup -- only
    lazily, inside the first real generation call. Automated tests mock
    _generate_image_local directly and never trigger this import or any model
    download; no GPU or model download is required to run the test suite. See
    README's "Stable Diffusion 1.5 (Local) Setup" section for the one-time
    install/download instructions this provider deliberately does NOT automate.

    Raises explicitly on any failure (missing deps, CUDA unavailable, model load
    failure, generation error) -- like Hugging Face, never silently degrades to a
    branded card itself; ImageMotionProvider's cascade is what decides to try the
    next configured provider or finally fall back.
    """

    DEFAULT_MODEL_PATH = "runwayml/stable-diffusion-v1-5"

    # Class-level cache: the model is loaded into memory at most once per process,
    # never per-request/per-scene.
    _pipeline = None
    _pipeline_device = None

    @property
    def name(self) -> str:
        return "stable_diffusion_1_5"

    @property
    def model_path(self) -> str:
        return settings.SD15_MODEL_PATH or self.DEFAULT_MODEL_PATH

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = build_scene_image_prompt(scene, brand)

        await _retry_transient(lambda: self._generate_and_save(prompt, output_path))

        return SceneVisualResult(
            path=output_path, source=SOURCE_STABLE_DIFFUSION, provider=self.name, model=self.model_path,
        )

    async def _generate_and_save(self, prompt: str, output_path: Path) -> None:
        try:
            image = await asyncio.to_thread(self._generate_image_local, prompt)
            image.save(output_path)
        except ImageGenerationError:
            raise
        except Exception as e:
            raise _classify_sd15_error(e)

        _validate_image_file(output_path)

    def _generate_image_local(self, prompt: str) -> "Image.Image":
        """
        Synchronous, CPU/GPU-bound: loads the pipeline (once per process, cached
        at class level) and runs inference. Automated tests monkeypatch this exact
        method, so torch/diffusers/a real GPU are never required to run them.
        """
        pipeline = self._get_or_load_pipeline()

        negative_prompt = "text, watermark, logo, blurry, distorted, deformed, low quality"
        generate_kwargs = dict(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=settings.SD15_NUM_INFERENCE_STEPS,
            guidance_scale=settings.SD15_GUIDANCE_SCALE,
            width=settings.SD15_WIDTH,
            height=settings.SD15_HEIGHT,
        )
        if settings.SD15_SEED is not None and settings.SD15_SEED >= 0:
            import torch
            generate_kwargs["generator"] = torch.Generator(device=self._pipeline_device).manual_seed(settings.SD15_SEED)

        result = pipeline(**generate_kwargs)
        return result.images[0]

    @classmethod
    def _get_or_load_pipeline(cls):
        if cls._pipeline is not None:
            return cls._pipeline

        try:
            import torch
            from diffusers import StableDiffusionPipeline
        except ImportError as e:
            raise ImagePermanentError(
                "diffusers/torch are not installed. See README's 'Stable Diffusion 1.5 "
                "(Local) Setup' section for install instructions."
            ) from e

        device = (settings.SD15_DEVICE or "auto").strip().lower()
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            raise ImagePermanentError(
                "SD15_DEVICE=cuda was configured but no CUDA device is available on this machine."
            )

        try:
            model_path = settings.SD15_MODEL_PATH or cls.DEFAULT_MODEL_PATH
            dtype = torch.float16 if device == "cuda" else torch.float32
            pipeline = StableDiffusionPipeline.from_pretrained(model_path, torch_dtype=dtype, safety_checker=None)
            pipeline = pipeline.to(device)

            if settings.SD15_LOW_VRAM:
                pipeline.enable_attention_slicing()
                if device == "cuda":
                    pipeline.enable_sequential_cpu_offload()
        except ImageGenerationError:
            raise
        except Exception as e:
            raise ImagePermanentError(f"Failed to load Stable Diffusion 1.5 model: {e}") from e

        cls._pipeline = pipeline
        cls._pipeline_device = device
        return pipeline


async def _generate_strict(provider: VideoProvider, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
    """
    Calls a provider's REAL generation attempt WITHOUT accepting its own internal
    graceful-degrade-to-branded behavior (Gemini/OpenAI only) -- used exclusively
    by ImageMotionProvider's cascade mode, so a Gemini failure moves on to try the
    next configured provider instead of prematurely settling for a branded card
    while Hugging Face/Stable Diffusion haven't been tried yet. Raises
    ImageGenerationError on failure for every provider type. BrandedFallbackProvider
    is never passed here -- the cascade calls it directly as the guaranteed last resort.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(provider, GeminiImageProvider):
        if not provider.is_configured:
            raise ImagePermanentError("GEMINI_API_KEY is not configured.")
        await _retry_transient(lambda: provider._generate_and_save(scene, brand, output_path))
        return SceneVisualResult(path=output_path, source=SOURCE_GEMINI, provider=provider.name, model=provider.model)

    if isinstance(provider, OpenAIImageProvider):
        if not provider.is_configured:
            raise ImagePermanentError("OPENAI_API_KEY is not configured.")
        await _retry_transient(lambda: provider._generate_and_validate(scene, brand, output_path))
        return SceneVisualResult(path=output_path, source=SOURCE_AI_GENERATED, provider=provider.name, model=provider.MODEL)

    # HuggingFaceImageProvider, LocalSD15ImageProvider: already raise-only by design
    # (no internal graceful fallback to short-circuit), so their normal public
    # entry point is exactly the strict behavior the cascade needs.
    return await provider.generate_scene_visual(scene, brand, output_path)


class ImageMotionProvider(VideoProvider):
    """
    Provider ORCHESTRATOR -- this is what video_generation_service.py instantiates
    (unchanged call site: `ImageMotionProvider()` -> `generate_scene_visual(...)`).

    Default behavior (settings.IMAGE_PROVIDER unset, "auto", or unrecognized):
    CASCADES through providers in priority order -- Gemini -> Hugging Face ->
    Stable Diffusion 1.5 (local) -> Branded fallback -- stopping at the first
    real success. If Gemini fails (no credential, quota, error) it tries Hugging
    Face next; if that also fails it tries the local Stable Diffusion model; only
    if ALL real providers fail does it use the branded card. Every real provider
    in the chain raises explicitly on failure (see _generate_strict) so the
    cascade can tell "this tier failed, try the next one" apart from "this tier
    succeeded" -- Gemini/OpenAI's own normal graceful-degrade-to-branded behavior
    is intentionally bypassed while cascading, since accepting it early would
    incorrectly skip the remaining configured providers.

    Explicitly setting IMAGE_PROVIDER to one specific value (gemini, openai,
    huggingface, stable_diffusion, branded_fallback) forces that ONE provider only
    (its own normal behavior applies, e.g. Gemini/OpenAI's built-in fallback to
    branded on failure) -- useful for testing, demos, or cost/compute control.
    """

    def __init__(self):
        self._providers: List[VideoProvider] = self._select_providers()

    @property
    def name(self) -> str:
        return "auto" if len(self._providers) > 1 else self._providers[0].name

    @property
    def _delegate(self) -> VideoProvider:
        """Backward-compat single-provider accessor: the first (highest-priority)
        provider this instance would try. In cascade mode this is Gemini; in an
        explicit single-provider selection it's that one provider."""
        return self._providers[0]

    @staticmethod
    def _select_providers() -> List[VideoProvider]:
        choice = (settings.IMAGE_PROVIDER or "auto").strip().lower()
        if choice == "openai":
            return [OpenAIImageProvider()]
        if choice == "huggingface":
            return [HuggingFaceImageProvider()]
        if choice in ("stable_diffusion", "stable_diffusion_1_5", "sd15"):
            return [LocalSD15ImageProvider()]
        if choice == "branded_fallback":
            return [BrandedFallbackProvider()]
        if choice == "gemini":
            return [GeminiImageProvider()]
        # "auto" (default) or an unrecognized value -> full priority cascade.
        return [GeminiImageProvider(), HuggingFaceImageProvider(), LocalSD15ImageProvider(), BrandedFallbackProvider()]

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        if len(self._providers) == 1:
            # Explicit single-provider selection -- unchanged behavior, including
            # Gemini/OpenAI's own internal graceful-degrade-to-branded.
            return await self._providers[0].generate_scene_visual(scene, brand, output_path)

        last_error: Optional[str] = None
        for provider in self._providers:
            try:
                return await _generate_strict(provider, scene, brand, output_path)
            except Exception as e:
                # Catches ImageGenerationError (the normal, classified case) AND
                # any unclassified exception a provider's own error handling
                # failed to wrap -- a cascade's whole point is resilience, so a
                # gap in one provider's classification must never crash the
                # entire generation when further fallback tiers remain.
                message = e.message if isinstance(e, ImageGenerationError) else str(e)
                last_error = f"{provider.name}: {message}"
                logger.info(f"[image cascade] {provider.name} failed ({message}); trying next provider.")
                continue

        # Unreachable in practice -- BrandedFallbackProvider never raises and is
        # always the last tier -- but guarded explicitly rather than assumed.
        fallback = await BrandedFallbackProvider().generate_scene_visual(scene, brand, output_path)
        fallback.provider_error = last_error
        return fallback
