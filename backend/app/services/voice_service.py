import io
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import mutagen.mp3
from gtts import gTTS

from app.schemas.agent_contracts import VideoScript, VoiceConfig, VoiceGenerationResult

logger = logging.getLogger("ja_assure.voice")


# ==============================================================================
# Custom Exceptions for Voice Service
# ==============================================================================

class VoiceServiceError(Exception):
    """Base exception for all voice service operations."""
    pass

class VoiceEmptyError(VoiceServiceError):
    """Raised when no voiceover text is found to synthesize."""
    pass

class VoiceLanguageError(VoiceServiceError):
    """Raised when an unsupported or invalid language code is requested."""
    pass

class VoiceSynthesisError(VoiceServiceError):
    """Raised when TTS provider synthesis fails."""
    pass


# ==============================================================================
# Supported Language Normalization Mapping
# JA Assure core markets: Singapore, Malaysia, Hong Kong, Indonesia, Thailand
# (English, Malay, Bahasa Indonesia, Thai, Chinese)
# ==============================================================================

SUPPORTED_LANGUAGE_MAPPING: Dict[str, str] = {
    # English
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    # Malay (Malaysia)
    "ms": "ms",
    "ms-my": "ms",
    "malay": "ms",
    "bahasa melayu": "ms",
    # Bahasa Indonesia (Indonesia)
    "id": "id",
    "id-id": "id",
    "indonesian": "id",
    "bahasa indonesia": "id",
    # Thai (Thailand)
    "th": "th",
    "th-th": "th",
    "thai": "th",
    # Chinese (Hong Kong / Singapore / Greater China)
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "chinese": "zh-CN",
    "mandarin": "zh-CN",
}


# ==============================================================================
# Extensible TTS Provider Interface
# ==============================================================================

class TTSProvider(ABC):
    """
    Provider-neutral interface for speech synthesis.
    Enables future plug-and-play addition of ElevenLabs, Azure Speech, or Google Cloud TTS
    without modifying the VoiceService business logic.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def synthesize(self, text: str, language_code: str, voice_config: Optional[VoiceConfig] = None) -> bytes:
        """Synthesize text into raw MP3 audio bytes."""
        pass


class GttsProvider(TTSProvider):
    """
    Default free, zero-API-key TTS provider utilizing Google Text-to-Speech (gTTS).
    Produces standardized MP3 audio streams.
    """
    @property
    def provider_name(self) -> str:
        return "gtts"

    def synthesize(self, text: str, language_code: str, voice_config: Optional[VoiceConfig] = None) -> bytes:
        slow = voice_config.slow if voice_config else False
        tld = voice_config.tld if voice_config else "com"

        try:
            tts = gTTS(text=text, lang=language_code, slow=slow, tld=tld)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"gTTS speech synthesis failed for language '{language_code}': {e}", exc_info=True)
            raise VoiceSynthesisError(f"Speech synthesis provider encountered an error: {str(e)}") from e


# ==============================================================================
# VoiceService Implementation
# ==============================================================================

class VoiceService:
    """
    Voice Agent and Audio Production Service for JA Assure marketing video assets.
    Orchestrates:
    1. Voiceover text extraction and chronological sequence concatenation from VideoScript scenes.
    2. Strict language validation and mapping for JA Assure regional markets.
    3. Multi-provider speech synthesis (defaulting to GttsProvider).
    4. Secure local MP3 persistence and mutagen-backed audio duration inspection.
    5. Clean metadata generation for frontend playback and downstream video assembly.
    """

    def __init__(
        self,
        media_root: Optional[Path] = None,
        provider: Optional[TTSProvider] = None
    ):
        if media_root is None:
            # Anchor to repo_root/media/voiceovers -- the same shared media root the
            # video pipeline uses (see video_generation_service.MEDIA_ROOT and the
            # single /media static mount in main.py), so audio_url is actually
            # servable rather than pointing at an unmounted directory.
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.media_root = base_dir / "media" / "voiceovers"
        else:
            self.media_root = Path(media_root)

        self.media_root.mkdir(parents=True, exist_ok=True)
        self.provider: TTSProvider = provider or GttsProvider()

    def normalize_language(self, language_input: Optional[str]) -> str:
        """
        Validate and normalize input language to supported gTTS language code.
        Supported: English ('en'), Malay ('ms'), Bahasa Indonesia ('id'), Thai ('th'), Chinese ('zh-CN').
        """
        if not language_input:
            return "en"

        cleaned = language_input.strip().lower()
        normalized = SUPPORTED_LANGUAGE_MAPPING.get(cleaned)
        if not normalized:
            allowed = ", ".join(["en (English)", "ms (Malay)", "id (Bahasa Indonesia)", "th (Thai)", "zh / zh-CN (Chinese)"])
            raise VoiceLanguageError(
                f"Unsupported language code '{language_input}'. "
                f"JA Assure Voice Agent supports: {allowed}."
            )
        return normalized

    def extract_voiceover_text(self, script: VideoScript) -> str:
        """
        Extract and concatenate scene voiceover strings in strict scene order.
        Validates that non-empty speech text exists.
        """
        if not script.scenes or len(script.scenes) == 0:
            raise VoiceEmptyError("VideoScript contains no scenes to synthesize.")

        ordered_scenes = sorted(script.scenes, key=lambda s: s.scene_number)
        segments: List[str] = []

        for scene in ordered_scenes:
            vo_text = (scene.voiceover or "").strip()
            if vo_text:
                from app.services.voice_agent import clean_voiceover_text
                cleaned = clean_voiceover_text(vo_text)
                if cleaned:
                    segments.append(cleaned)

        combined = " ".join(segments).strip()
        if not combined:
            raise VoiceEmptyError(
                "All scenes in the VideoScript have empty voiceover fields. "
                "Provide spoken voiceover copy for at least one scene."
            )

        return combined

    def synthesize_from_script(
        self,
        script: VideoScript,
        language_override: Optional[str] = None,
        voice_config: Optional[VoiceConfig] = None
    ) -> VoiceGenerationResult:
        """
        Extract scene voiceovers from a VideoScript, synthesize MP3 audio,
        save to local media storage, and return structured metadata.
        """
        voiceover_text = self.extract_voiceover_text(script)
        lang_to_use = language_override or script.language or "en"
        target_lang = self.normalize_language(lang_to_use)

        brand_prefix = (script.brand or "ja_assure").lower().replace(" ", "_")
        prefix = f"{brand_prefix}_vo"

        result = self.synthesize_text(
            text=voiceover_text,
            language_code=target_lang,
            voice_config=voice_config,
            prefix=prefix,
            scene_count=len(script.scenes)
        )

        # Update the script model in place for seamless pipeline forwarding
        script.audio_url = result.audio_url
        script.audio_filename = result.audio_filename
        script.audio_duration_seconds = result.duration_seconds
        script.voice_provider = result.provider
        script.voice_language = result.language
        script.voice_status = "generated"
        script.media_status = "voice_generated"

        return result

    def synthesize_text(
        self,
        text: str,
        language_code: str = "en",
        voice_config: Optional[VoiceConfig] = None,
        prefix: str = "voice",
        scene_count: int = 1
    ) -> VoiceGenerationResult:
        """
        Directly synthesize an arbitrary string of text to a secure MP3 file.
        """
        from app.services.voice_agent import clean_voiceover_text
        cleaned_text = clean_voiceover_text(text)
        if not cleaned_text:
            raise VoiceEmptyError("Cannot synthesize empty text string.")

        target_lang = self.normalize_language(language_code)

        # Generate secure unique filename
        file_id = uuid.uuid4().hex[:16]
        filename = f"{prefix}_{file_id}.mp3"
        target_path = (self.media_root / filename).resolve()

        # Prevent directory traversal
        if not target_path.is_relative_to(self.media_root.resolve()):
            raise VoiceServiceError("Invalid destination path resolved; path traversal blocked.")

        # Synthesize audio bytes
        audio_bytes = self.provider.synthesize(
            text=cleaned_text,
            language_code=target_lang,
            voice_config=voice_config
        )

        # Write to disk securely
        with open(target_path, "wb") as f:
            f.write(audio_bytes)

        file_size = len(audio_bytes)

        # Inspect duration via mutagen
        duration_seconds: Optional[float] = None
        try:
            audio_info = mutagen.mp3.MP3(target_path).info
            duration_seconds = round(float(audio_info.length), 2)
        except Exception as e:
            logger.warning(f"Could not read MP3 duration for {filename}: {e}")
            duration_seconds = None

        audio_url = f"/media/voiceovers/{filename}"

        logger.info(
            f"Successfully synthesized MP3 voiceover: {filename} "
            f"({file_size} bytes, {duration_seconds}s, lang={target_lang}, provider={self.provider.provider_name})"
        )

        return VoiceGenerationResult(
            status="generated",
            audio_url=audio_url,
            audio_filename=filename,
            language=target_lang,
            provider=self.provider.provider_name,
            duration_seconds=duration_seconds,
            voiceover_text=cleaned_text,
            scene_count=scene_count,
            file_size_bytes=file_size,
            created_at=datetime.now(timezone.utc).isoformat()
        )


# Singleton instance
voice_service = VoiceService()
