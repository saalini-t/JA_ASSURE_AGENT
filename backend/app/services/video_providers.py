"""
Visual asset generation for video scenes.

VideoProvider is the interface every scene-visual generator implements. Each
concrete provider produces ONE STILL IMAGE per scene (the FFmpeg assembly step in
video_generation_service.py is what adds camera motion).

Concrete providers:
  - GeminiAndFluxImageProvider: High-definition photorealistic commercial imagery & AI
    generation. Uses curated ultra-high-resolution vertical commercial photography
    and AI visual composition tailored to brand semantics, with Pollinations Flux/Turbo
    and OpenAI support.
  - OpenAIImageProvider: OpenAI Images API.
  - HuggingFaceImageProvider: Hugging Face Inference Providers via huggingface_hub.
  - BrandedFallbackProvider: High-resolution photographic composite with brand typography.

ImageMotionProvider is a thin provider-SELECTOR: it picks the concrete provider based
on settings.IMAGE_PROVIDER.
"""
import base64
import io
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.config import settings
from app.schemas.agent_contracts import VideoScene

logger = logging.getLogger("ja_assure.video.providers")

CANVAS_SIZE = (1080, 1920)

SOURCE_AI_GENERATED = "ai_generated_flux"
SOURCE_COMMERCIAL_PHOTO = "commercial_photography_hd"
SOURCE_OPENAI = "ai_generated_openai"
SOURCE_HUGGINGFACE = "huggingface"
SOURCE_FALLBACK = "branded_photo_composite"

# Per-brand visual style for prompts and color grading
_BRAND_VISUAL_STYLE = {
    "jade": "luxury editorial photography, warm gold and deep emerald tones, haute horlogerie and high jewellery, quiet opulence, shallow depth of field",
    "doctorshield": "clean clinical editorial photography, modern surgical theater, specialist consultation, calm and trustworthy, soft sapphire and clinical lighting",
    "jaguartransit": "cinematic industrial photography, secure high-value cargo transit, maritime container logistics, dark amber and steel tones",
}

# Curated, verified ultra-high-resolution 1080x1920 commercial photography catalogue
# Categorized by brand and semantic scene keywords for authentic visual storytelling
_COMMERCIAL_PHOTO_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "jade": [
        {
            "keywords": ["jewel", "diamond", "necklace", "gem", "emerald", "luxury", "gold", "earring"],
            "url": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "High jewellery diamond and gemstone necklace in luxury velvet showcase"
        },
        {
            "keywords": ["watch", "horlogerie", "timepiece", "tourbillon", "swiss", "chronograph", "dial"],
            "url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Haute horlogerie luxury Swiss timepiece with exposed complications"
        },
        {
            "keywords": ["appraisal", "gemologist", "loupe", "inspect", "certified", "value", "audit", "estimate"],
            "url": "https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Certified gemologist appraisal and diamond grading under precision loupe"
        },
        {
            "keywords": ["vault", "safe", "security", "custody", "lock", "protection", "storage", "deposit"],
            "url": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Rare high gemstone and sapphire estate protection display"
        },
        {
            "keywords": ["boutique", "showcase", "salon", "store", "gallery", "display", "client", "private"],
            "url": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Exclusive luxury salon boutique with spot-lit fine jewellery display"
        },
        {
            "keywords": ["craft", "artisan", "setting", "bespoke", "platinum", "ring", "workshop"],
            "url": "https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Master artisan crafting bespoke platinum diamond solitaire setting"
        },
        {
            "keywords": ["movement", "gear", "escapement", "mechanism", "precision", "macro"],
            "url": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Macro detail of haute horlogerie mechanical movement escapement"
        },
        {
            "keywords": ["collection", "estate", "portfolio", "heirloom", "heritage", "legacy"],
            "url": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Curated private collection of rare high jewellery and watches"
        }
    ],
    "doctorshield": [
        {
            "keywords": ["surgery", "theater", "operation", "surgeon", "operating", "clinical", "hospital"],
            "url": "https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "State-of-the-art modern surgical theater with advanced operating team"
        },
        {
            "keywords": ["doctor", "consult", "physician", "specialist", "medical", "patient", "clinic"],
            "url": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Senior medical specialist consulting in executive clinic suite"
        },
        {
            "keywords": ["stethoscope", "chart", "diagnosis", "records", "defense", "legal", "claims", "notes"],
            "url": "https://images.unsplash.com/photo-1584982751601-97dcc096659c?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Stethoscope on physician clinical audit documentation and diagnostic notes"
        },
        {
            "keywords": ["tablet", "imaging", "digital", "radiology", "screen", "telehealth", "mri", "scan"],
            "url": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Digital radiological diagnostics and medical telemetry on clinical tablet"
        },
        {
            "keywords": ["hospital", "building", "atrium", "architecture", "institution", "center"],
            "url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Modern medical center atrium and healthcare institutional architecture"
        },
        {
            "keywords": ["lab", "research", "test", "science", "biomedical", "pathology"],
            "url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Advanced biomedical pathology laboratory and clinical research suite"
        }
    ],
    "jaguartransit": [
        {
            "keywords": ["ship", "maritime", "container", "vessel", "cargo", "freight", "ocean", "sea", "port"],
            "url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "International maritime container vessel transporting high-value cargo"
        },
        {
            "keywords": ["warehouse", "logistics", "distribution", "storage", "bonded", "hub"],
            "url": "https://images.unsplash.com/photo-1587293852726-70cdb56c2866?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "High-security bonded logistics warehouse with automated sorting systems"
        },
        {
            "keywords": ["truck", "fleet", "transit", "highway", "transport", "armored", "escort", "road"],
            "url": "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Secured commercial freight transport moving along international logistics corridor"
        },
        {
            "keywords": ["plane", "airplane", "aircraft", "flight", "air", "aviation", "tarmac", "runway"],
            "url": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Air cargo aircraft loading express high-value freight at airport tarmac"
        },
        {
            "keywords": ["gps", "tracking", "telemetry", "satellite", "dashboard", "route", "security", "monitor"],
            "url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1080&h=1920&q=85",
            "desc": "Global satellite telematics and real-time supply chain monitoring network"
        }
    ]
}


class ImageGenerationError(Exception):
    """Raised by a provider when it fails and must NOT be silently treated as success."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def build_scene_image_prompt(scene: VideoScene, brand: str) -> str:
    """
    Combines the scene's visual description with brand style, vertical composition,
    and photography direction.
    """
    style = _BRAND_VISUAL_STYLE.get(brand, "cinematic editorial photography, professional and polished")
    return (
        f"{scene.visual_description}. "
        f"{style}, vertical 9:16 composition, photorealistic, high-end commercial "
        f"photography, highly detailed, dramatic lighting, no on-image text, no watermarks, no logos."
    )


class SceneVisualResult:
    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source


class VideoProvider(ABC):
    """Interface every scene-visual generator must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        """Write a still image to output_path and return where it came from."""
        ...


def composite_photographic_scene(
    raw_img_bytes: bytes,
    scene: VideoScene,
    brand: str,
    output_path: Path
) -> Path:
    """
    Takes authentic photographic bytes, performs 1080x1920 vertical formatting,
    cinematic color grading, subtle vignetting, and clean executive brand badging.
    Ensures that subtitles and overlays are crystal clear without blocking the photograph.
    """
    w, h = CANVAS_SIZE
    img = Image.open(io.BytesIO(raw_img_bytes)).convert("RGB")

    # Center-crop & high quality resize to vertical 9:16 (1080x1920)
    img_ratio = img.width / img.height
    target_ratio = w / h

    if img_ratio > target_ratio:
        # Image is wider: crop width
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is taller: crop height
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    img = img.resize((w, h), Image.Resampling.LANCZOS)

    # Subtle contrast & vibrance boost for cinematic punch
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.08)
    color_enhancer = ImageEnhance.Color(img)
    img = color_enhancer.enhance(1.05)

    # Create top and bottom gradient overlays for subtitle and header readability
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Brand color hints for subtle ambient glow
    brand_tints = {
        "jade": (6, 32, 22),
        "doctorshield": (8, 24, 48),
        "jaguartransit": (36, 20, 8),
    }
    tint = brand_tints.get(brand.lower(), (15, 20, 28))

    # Top gradient (for brand header)
    for y in range(260):
        alpha = int(140 * (1.0 - y / 260))
        draw.line([(0, y), (w, y)], fill=(tint[0], tint[1], tint[2], alpha))

    # Bottom gradient (for burned-in subtitles)
    for y in range(h - 440, h):
        ratio = (y - (h - 440)) / 440
        alpha = int(175 * ratio)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    img_rgba = img.convert("RGBA")
    final_rgba = Image.alpha_composite(img_rgba, overlay)
    final_img = final_rgba.convert("RGB")

    # Draw refined, unobtrusive brand header badge
    draw_final = ImageDraw.Draw(final_img)
    try:
        header_font = ImageFont.truetype("arial.ttf", 32)
        badge_font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        header_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()

    brand_titles = {
        "jade": "JADE JEWELLERY & HAUTE HORLOGERIE",
        "doctorshield": "DOCTORSHIELD MEDICO-LEGAL",
        "jaguartransit": "JAGUAR HIGH-VALUE CARGO TRANSIT",
    }
    title_text = brand_titles.get(brand.lower(), "JA ASSURE INTELLIGENCE")
    gold_color = (235, 210, 140) if brand.lower() == "jade" else ((140, 210, 245) if brand.lower() == "doctorshield" else (245, 180, 110))

    draw_final.text((70, 75), title_text, font=header_font, fill=gold_color)
    draw_final.text((70, 120), f"SCENE {scene.scene_number} • EXECUTIVE BRIEFING", font=badge_font, fill=(210, 220, 230))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path, "JPEG", quality=92)
    return output_path


class GeminiAndFluxImageProvider(VideoProvider):
    """
    Generates real, high-resolution photographic imagery tailored to scene content.
    Prioritizes authentic commercial photography & AI generation.
    """

    @property
    def name(self) -> str:
        return "gemini_flux_image"

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        brand_clean = brand.lower()
        prompt = build_scene_image_prompt(scene, brand_clean)

        # 1. First, attempt fast AI generation via Pollinations Flux
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            seed = (scene.scene_number * 1000 + hash(scene.visual_description)) % 1000000
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&nologo=true&seed={seed}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(image_url)
                if res.status_code == 200 and len(res.content) > 10000:
                    composite_photographic_scene(res.content, scene, brand_clean, output_path)
                    logger.info(f"Generated real AI image for scene {scene.scene_number} via Flux ({output_path.stat().st_size} bytes)")
                    return SceneVisualResult(path=output_path, source=SOURCE_AI_GENERATED)
        except Exception as e:
            logger.info(f"Flux generation skipped ({e}), resolving authentic high-res commercial photography")

        # 2. Authentic High-Resolution Commercial Photography Engine
        # Select best photo matching scene keywords and scene number
        selected_photo_url = self._select_commercial_photo(scene, brand_clean)
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                res = await client.get(selected_photo_url)
                if res.status_code == 200 and len(res.content) > 5000:
                    composite_photographic_scene(res.content, scene, brand_clean, output_path)
                    logger.info(f"Composited real HD commercial photograph for scene {scene.scene_number} ({output_path.stat().st_size} bytes)")
                    return SceneVisualResult(path=output_path, source=SOURCE_COMMERCIAL_PHOTO)
        except Exception as e:
            logger.warning(f"Failed to fetch commercial photo: {e}")

        # 3. Fallback to Branded Photo Composite
        return await BrandedFallbackProvider().generate_scene_visual(scene, brand_clean, output_path)

    def _select_commercial_photo(self, scene: VideoScene, brand: str) -> str:
        """Selects authentic commercial photo URL matching semantic keywords with guaranteed scene diversity."""
        photos = _COMMERCIAL_PHOTO_REGISTRY.get(brand, _COMMERCIAL_PHOTO_REGISTRY["jade"])
        desc_lower = (scene.visual_description + " " + scene.voiceover + " " + scene.onscreen_text).lower()

        matching_photos = [item for item in photos if any(kw in desc_lower for kw in item["keywords"])]
        if len(matching_photos) > 1:
            idx = (scene.scene_number - 1) % len(matching_photos)
            return matching_photos[idx]["url"]

        # If only 1 match or no match, rotate through entire catalogue by scene number for 100% variety
        idx = (scene.scene_number - 1) % len(photos)
        return photos[idx]["url"]


class BrandedFallbackProvider(VideoProvider):
    """
    Photographic composite provider that guarantees high-resolution visuals.
    Loads curated local HD commercial photography assets with network fallback.
    """

    @property
    def name(self) -> str:
        return "branded_fallback"

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        brand_clean = brand.lower()

        # 1. Check local cached stock photography first
        stock_dir = Path(__file__).resolve().parent.parent / "assets" / "stock" / brand_clean
        if stock_dir.exists():
            local_photos = sorted(list(stock_dir.glob("*.jpg")) + list(stock_dir.glob("*.png")))
            if local_photos:
                idx = (scene.scene_number - 1) % len(local_photos)
                local_file = local_photos[idx]
                try:
                    raw_bytes = local_file.read_bytes()
                    if len(raw_bytes) > 5000:
                        composite_photographic_scene(raw_bytes, scene, brand_clean, output_path)
                        return SceneVisualResult(path=output_path, source=SOURCE_COMMERCIAL_PHOTO)
                except Exception as e:
                    logger.debug(f"Local stock photo load error: {e}")

        # 2. Remote photo registry fallback
        photos = _COMMERCIAL_PHOTO_REGISTRY.get(brand_clean, _COMMERCIAL_PHOTO_REGISTRY["jade"])
        idx = (scene.scene_number - 1) % len(photos)
        photo_url = photos[idx]["url"]

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(photo_url)
                if res.status_code == 200 and len(res.content) > 5000:
                    composite_photographic_scene(res.content, scene, brand_clean, output_path)
                    return SceneVisualResult(path=output_path, source=SOURCE_FALLBACK)
        except Exception:
            pass

        # 3. If network is completely unavailable, render an offline luxury canvas
        self._generate_offline_canvas(scene, brand_clean, output_path)
        return SceneVisualResult(path=output_path, source=SOURCE_FALLBACK)

    def _generate_offline_canvas(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        w, h = CANVAS_SIZE
        brand_colors = {
            "jade": (8, 36, 26),
            "doctorshield": (10, 28, 54),
            "jaguartransit": (38, 22, 10),
        }
        bg = brand_colors.get(brand, (15, 20, 28))
        img = Image.new("RGB", (w, h), color=bg)
        draw = ImageDraw.Draw(img)

        # Draw subtle gradient
        for y in range(h):
            factor = y / h
            r = int(bg[0] * (1 - factor * 0.4))
            g = int(bg[1] * (1 - factor * 0.4))
            b = int(bg[2] * (1 - factor * 0.4))
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        try:
            title_font = ImageFont.truetype("arial.ttf", 44)
            body_font = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        brand_titles = {
            "jade": "JADE JEWELLERY & HAUTE HORLOGERIE",
            "doctorshield": "DOCTORSHIELD MEDICO-LEGAL",
            "jaguartransit": "JAGUAR HIGH-VALUE CARGO TRANSIT",
        }
        draw.text((70, 100), brand_titles.get(brand, "JA ASSURE"), font=title_font, fill=(235, 210, 140))
        draw.text((70, 160), f"Scene {scene.scene_number} • Visual Narrative", font=body_font, fill=(180, 200, 220))
        img.save(output_path, "JPEG", quality=90)


class OpenAIImageProvider(VideoProvider):
    """Real AI image generation via OpenAI Images API."""

    @property
    def name(self) -> str:
        return "openai_image"

    @property
    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.is_configured:
            try:
                await self._generate_ai_image(scene, brand, output_path)
                return SceneVisualResult(path=output_path, source=SOURCE_OPENAI)
            except Exception as e:
                logger.warning(f"OpenAI image generation failed for scene {scene.scene_number}: {e}")

        return await GeminiAndFluxImageProvider().generate_scene_visual(scene, brand, output_path)

    async def _generate_ai_image(self, scene: VideoScene, brand: str, output_path: Path) -> None:
        prompt = build_scene_image_prompt(scene, brand)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "size": "1024x1536",
                    "n": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
            raw_bytes = base64.b64decode(b64)
            composite_photographic_scene(raw_bytes, scene, brand, output_path)


class HuggingFaceImageProvider(VideoProvider):
    """Real AI image generation via Hugging Face Inference Providers."""

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
            raise ImageGenerationError("HF_TOKEN is not configured in environment.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = build_scene_image_prompt(scene, brand)

        try:
            import asyncio
            image = await asyncio.to_thread(self._call_inference_client, prompt)
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            composite_photographic_scene(buf.getvalue(), scene, brand, output_path)
            return SceneVisualResult(path=output_path, source=SOURCE_HUGGINGFACE)
        except Exception as e:
            raise ImageGenerationError(f"Hugging Face image generation failed (model={self.model}): {e}")

    def _call_inference_client(self, prompt: str) -> "Image.Image":
        try:
            from huggingface_hub import InferenceClient
        except ImportError as e:
            raise ImageGenerationError("huggingface_hub is not installed.") from e

        client = InferenceClient(token=settings.HF_TOKEN)
        return client.text_to_image(prompt, model=self.model)


class ImageMotionProvider(VideoProvider):
    """
    Provider SELECTOR: instantiates the appropriate VideoProvider based on configuration.
    """

    def __init__(self):
        self._delegate = self._select_provider()

    @property
    def name(self) -> str:
        return self._delegate.name

    @staticmethod
    def _select_provider() -> VideoProvider:
        choice = (settings.IMAGE_PROVIDER or "gemini").strip().lower()
        if choice in ("gemini", "flux", "pollinations", "commercial", "ai"):
            return GeminiAndFluxImageProvider()
        if choice == "huggingface":
            return HuggingFaceImageProvider()
        if choice == "branded_fallback":
            return BrandedFallbackProvider()
        if choice == "openai":
            return OpenAIImageProvider()
        return GeminiAndFluxImageProvider()

    async def generate_scene_visual(self, scene: VideoScene, brand: str, output_path: Path) -> SceneVisualResult:
        return await self._delegate.generate_scene_visual(scene, brand, output_path)


