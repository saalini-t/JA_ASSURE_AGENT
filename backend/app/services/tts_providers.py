"""
Voiceover generation for narrated video scenes.

VideoTTSProvider is the interface every TTS generator implements -- mirrors
VideoProvider's shape (video_providers.py) so both follow the same pattern.

Unlike ImageMotionProvider's graceful branded-card fallback, TTS failure is NEVER
silently masked here: OpenAITTSProvider raises TTSGenerationError on any failure
(missing credential, network error, empty response). The caller
(video_generation_service.generate_video_mvp) must treat this as an explicit failed
render (stage="tts"), never as a silently-degraded "success".

SilentTestTTSProvider exists ONLY for tests. It writes a real, valid, silent WAV
file using Python's stdlib `wave` module (no network, no API key, no ffmpeg needed
to produce it) so the FFmpeg audio-muxing pipeline can be genuinely exercised
without depending on a live API. It must never be wired into a production code path.
"""
import logging
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("ja_assure.video.tts")


class TTSGenerationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class VideoTTSProvider(ABC):
    """Interface every voiceover generator (real or future) must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate_voiceover(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        """
        Write a real audio file to output_path and return it.
        Raises TTSGenerationError on any failure -- callers must treat a raised
        error as a hard stop, never substitute silence and call it success.
        """
        ...


class OpenAITTSProvider(VideoTTSProvider):
    """
    Real, API-based TTS via OpenAI's /v1/audio/speech endpoint. Reuses the same
    OPENAI_API_KEY already configured for ImageMotionProvider (Phase 1) -- one
    vendor relationship, one credential, no new environment variable needed.
    """

    DEFAULT_VOICE = "alloy"
    DEFAULT_MODEL = "tts-1"

    @property
    def name(self) -> str:
        return "openai_tts"

    @property
    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate_voiceover(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        if not self.is_configured:
            raise TTSGenerationError(
                "OPENAI_API_KEY is not configured. Set it in backend/.env to enable voiceover generation."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.DEFAULT_MODEL,
                        "voice": voice or self.DEFAULT_VOICE,
                        "input": text,
                        "response_format": "mp3",
                    },
                )
                resp.raise_for_status()
                output_path.write_bytes(resp.content)
        except TTSGenerationError:
            raise
        except Exception as e:
            raise TTSGenerationError(f"OpenAI TTS request failed: {e}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise TTSGenerationError("OpenAI TTS returned an empty response.")
        return output_path


class VoiceAgentTTSProvider(VideoTTSProvider):
    """
    Wraps the team's Voice Agent (app.services.voice_service.VoiceService, gTTS-backed)
    so the video pipeline's per-scene narration reuses that SAME engine rather than a
    second, competing TTS implementation. This is the default provider for narrated
    video generation -- unlike OpenAITTSProvider, gTTS needs no API key/credential.

    Only wraps voice_service's existing synthesize_text() primitive (arbitrary text ->
    one MP3 file); the whole-script synthesize_from_script() used by the standalone
    Voice Studio feature (/content/voice) is untouched and unrelated to this class.
    """

    @property
    def name(self) -> str:
        return "gtts"  # matches GttsProvider.provider_name, surfaced as audio_source

    def __init__(self, language: str = "en"):
        self.language = language

    async def generate_voiceover(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        import asyncio
        from app.services.voice_service import VoiceService, VoiceServiceError

        cleaned = (text or "").strip()
        if not cleaned:
            raise TTSGenerationError("Cannot synthesize an empty voiceover string.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Root a VoiceService instance directly at this scene's own job directory so
        # the file lands exactly where the video pipeline expects it -- reuses their
        # synthesize_text()/GttsProvider/mutagen-duration logic unchanged, just with
        # a job-scoped destination instead of the global backend/media/voiceovers/.
        service = VoiceService(media_root=output_path.parent)

        try:
            result = await asyncio.to_thread(
                service.synthesize_text,
                text=cleaned,
                language_code=voice or self.language,
                prefix=output_path.stem,
                scene_count=1,
            )
        except VoiceServiceError as e:
            raise TTSGenerationError(f"Voice Agent (gTTS) synthesis failed: {e}")
        except Exception as e:
            raise TTSGenerationError(f"Voice Agent (gTTS) synthesis failed: {e}")

        generated_path = service.media_root / result.audio_filename
        if not generated_path.exists() or generated_path.stat().st_size == 0:
            raise TTSGenerationError("Voice Agent (gTTS) produced an empty audio file.")

        # synthesize_text() names the file itself (uuid-suffixed); move it to the
        # exact scene_NNN.mp3 path video_generation_service expects for FFmpeg.
        if generated_path != output_path:
            generated_path.replace(output_path)
        return output_path


class SilentTestTTSProvider(VideoTTSProvider):
    """
    TEST-ONLY provider -- never used in production code paths. Generates a real,
    valid, silent mono WAV file of a fixed duration so tests can exercise the real
    FFmpeg audio pipeline (muxing, ffprobe audio-stream detection, caption timing
    derived from "measured" duration) without a network call or API key.
    """

    def __init__(self, duration_seconds: float = 3.0):
        self.duration_seconds = duration_seconds

    @property
    def name(self) -> str:
        return "silent_test_provider"

    async def generate_voiceover(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        framerate = 16000
        n_frames = int(framerate * self.duration_seconds)
        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(framerate)
            wav_file.writeframes(b"\x00\x00" * n_frames)
        return output_path
