"""
Voice Agent <-> video pipeline integration tests.

Covers: the scene_validator exception for a silent disclaimer/end-card scene,
VoiceAgentTTSProvider (which wraps the team's voice_service.VoiceService/GttsProvider
rather than a second competing TTS implementation), the per-scene skip-TTS-for-silent-
scenes behavior in video_generation_service, and that FFmpeg correctly receives real
audio for narrated scenes and genuine silence for the disclaimer scene.

The only network boundary mocked is GttsProvider.synthesize() (Google's TTS network
call) -- everything downstream of it (VoiceService.synthesize_text's file writing and
mutagen duration read, VoiceAgentTTSProvider's wrapping, FFmpeg muxing, ffprobe
validation) is exercised for real, using the same minimal-but-valid dummy MP3 byte
sequence the team's own test_voice_service.py uses.
"""
import shutil
import subprocess
import uuid

import pytest

from app.services.scene_validator import validate_video_script
from app.services.voice_service import GttsProvider
from app.services.tts_providers import VoiceAgentTTSProvider, TTSGenerationError
from app.services import video_generation_service as vgs
from app.services.video_generation_service import generate_video_mvp, _probe_final_output

from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe
from tests.test_video_generation import _make_scene, _make_script


def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)

# The team's own test_voice_service.py dummy MP3 header satisfies mutagen's lenient
# tag reader but NOT ffprobe's stricter MPEG frame-sync parsing that this pipeline's
# _probe_audio_duration() relies on. Generate a genuinely valid, ffprobe-parseable
# MP3 via ffmpeg itself instead (computed once, reused by every fake TTS call).
_VALID_MP3_BYTES = None


def _valid_mp3_bytes() -> bytes:
    global _VALID_MP3_BYTES
    if _VALID_MP3_BYTES is None:
        import tempfile
        from pathlib import Path as _Path
        with tempfile.TemporaryDirectory() as tmp:
            out_path = _Path(tmp) / "fixture.mp3"
            subprocess.run(
                [resolve_ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", "2", "-codec:a", "libmp3lame", "-b:a", "64k", str(out_path)],
                capture_output=True, check=True, timeout=30,
            )
            _VALID_MP3_BYTES = out_path.read_bytes()
    return _VALID_MP3_BYTES


def _fake_gtts_synthesize(self, text, language_code, voice_config=None) -> bytes:
    return _valid_mp3_bytes()


# ---------------------------------------------------------------------------
# 1/2/3. Scene validator: disclaimer exception, without weakening normal scenes
# ---------------------------------------------------------------------------

def test_normal_scene_with_missing_voiceover_fails_validation():
    """
    VideoScene.voiceover is a required `str` field -- normal Pydantic construction
    can't produce a genuinely absent/None value (VideoScene(voiceover=None, ...) would
    raise ValidationError before ever reaching the validator). The realistic "missing"
    case is a malformed object bypassing validation (e.g. llm_provider's
    model_construct() fallback path) -- reproduced here the same way, so the
    validator's defensive getattr(scene, "voiceover", None) is genuinely exercised.
    """
    from app.schemas.agent_contracts import VideoScene

    scene = VideoScene.model_construct(
        scene_number=1, duration_seconds=5, visual_description="A diamond ring.", onscreen_text="Protected."
    )  # voiceover deliberately omitted entirely
    script = _make_script(scenes=[scene])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("voiceover is missing or empty" in e for e in result.errors)


def test_normal_scene_with_empty_voiceover_fails_validation():
    scene = _make_scene(voiceover="   ")  # whitespace-only, no compliance_disclaimer
    script = _make_script(scenes=[scene])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("voiceover is missing or empty" in e for e in result.errors)


def test_disclaimer_scene_with_empty_voiceover_and_disclaimer_passes_validation():
    normal_scene = _make_scene(scene_number=1, duration_seconds=10)
    disclaimer_scene = _make_scene(
        scene_number=2,
        duration_seconds=5,
        voiceover="",
        compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*",
    )
    script = _make_script(scenes=[normal_scene, disclaimer_scene])
    result = validate_video_script(script)
    assert result.valid is True, result.errors


def test_disclaimer_scene_without_compliance_disclaimer_still_fails():
    """The exception is specifically for compliance_disclaimer scenes -- an empty
    voiceover with no disclaimer field set must still fail, exactly like before."""
    scene = _make_scene(voiceover="", compliance_disclaimer=None)
    script = _make_script(scenes=[scene])
    result = validate_video_script(script)
    assert result.valid is False
    assert any("compliance_disclaimer" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 4. Voice Agent generates audio for a normal scene (reuses voice_service, not a
#    competing implementation -- only the network call is mocked)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_voice_agent_provider_generates_real_audio_file(tmp_path, monkeypatch):
    monkeypatch.setattr(GttsProvider, "synthesize", _fake_gtts_synthesize)

    provider = VoiceAgentTTSProvider(language="en")
    output_path = tmp_path / "scene_001.mp3"
    result_path = await provider.generate_voiceover("Protect your jewellery collection.", output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert provider.name == "gtts"


@pytest.mark.anyio
async def test_voice_agent_provider_raises_explicit_error_on_empty_text(tmp_path):
    provider = VoiceAgentTTSProvider(language="en")
    with pytest.raises(TTSGenerationError, match="empty voiceover"):
        await provider.generate_voiceover("", tmp_path / "scene_001.mp3")


@pytest.mark.anyio
async def test_voice_agent_provider_surfaces_synthesis_failure_explicitly(tmp_path, monkeypatch):
    def failing_synthesize(self, text, language_code, voice_config=None):
        raise RuntimeError("simulated gTTS network failure")

    monkeypatch.setattr(GttsProvider, "synthesize", failing_synthesize)

    provider = VoiceAgentTTSProvider(language="en")
    with pytest.raises(TTSGenerationError, match="Voice Agent \\(gTTS\\) synthesis failed"):
        await provider.generate_voiceover("Some narration.", tmp_path / "scene_001.mp3")


# ---------------------------------------------------------------------------
# 5. Disclaimer scene does not invoke TTS
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_disclaimer_scene_never_calls_tts(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # fallback images, no network
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    class CountingTTSProvider:
        """Records every call instead of failing inline -- a call for the disclaimer
        scene (2) would be a real pipeline bug, but asserting immediately inside
        generate_voiceover would also fail the legitimate call for scene 1. Assert on
        the recorded calls once the pipeline is done instead."""
        name = "counting_test_provider"

        def __init__(self):
            self.calls = []

        async def generate_voiceover(self, text, output_path, voice=None):
            self.calls.append(text)
            import wave
            with wave.open(str(output_path), "w") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 16000 * 2)
            return output_path

    provider = CountingTTSProvider()
    script = _make_script(scenes=[
        _make_scene(scene_number=1, duration_seconds=6, voiceover="Real narration for scene one."),
        _make_scene(
            scene_number=2, duration_seconds=4, voiceover="",
            compliance_disclaimer="*Terms and conditions apply.*",
        ),
    ])

    result = await generate_video_mvp(
        script, job_id="no-tts-on-disclaimer", narrate=True, tts_provider=provider
    )

    assert result.success is True, result.error_message
    assert provider.calls == ["Real narration for scene one."]  # never called for scene 2


# ---------------------------------------------------------------------------
# 6/7/8. Generated audio reaches FFmpeg correctly; final video has audio even with
# a silent disclaimer scene mixed in
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_full_pipeline_with_normal_and_disclaimer_scenes(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # fallback images, no network
    monkeypatch.setattr(GttsProvider, "synthesize", _fake_gtts_synthesize)  # real Voice Agent, fake network
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[
        _make_scene(scene_number=1, duration_seconds=6, voiceover="Your jewellery deserves real protection."),
        _make_scene(scene_number=2, duration_seconds=6, voiceover="Especially when travelling internationally."),
        _make_scene(
            scene_number=3, duration_seconds=5, voiceover="",
            visual_description="Jade logo with statutory disclaimer text on screen.",
            onscreen_text="*Terms, conditions, and underwriting limits apply.*",
            compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*",
        ),
    ])

    job_id = uuid.uuid4().hex[:8]
    result = await generate_video_mvp(
        script, job_id=job_id, narrate=True, tts_provider=VoiceAgentTTSProvider(language="en")
    )

    assert result.success is True, result.error_message
    assert result.scenes_generated == 3
    assert result.audio_source == "gtts"  # identifies the team's Voice Agent, not a competing TTS

    # 7: final video contains an audio stream (real narration on scenes 1-2)
    duration, has_audio = _probe_final_output(result.video_path, require_audio=True)
    assert has_audio is True

    # 8: the silent disclaimer scene's own clip still exists, has its full planned
    # duration, and -- critically -- ALSO has an audio stream (silence), proving the
    # concat step received a uniform layout rather than a broken mixed one.
    disclaimer_clip = tmp_path / job_id / "scene_003.mp4"
    assert disclaimer_clip.exists()
    ffprobe_bin = resolve_ffprobe()
    proc = subprocess.run(
        [ffprobe_bin, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(disclaimer_clip)],
        capture_output=True, text=True, timeout=30,
    )
    import json
    info = json.loads(proc.stdout)
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert any(s["codec_type"] == "video" for s in info["streams"])
    assert abs(float(info["format"]["duration"]) - 5.0) < 0.5  # kept its planned duration, not TTS-measured

    # The disclaimer scene's text must never have been sent to TTS/captions: no
    # scene_003.srt (per-scene caption) and its text is absent from the global track.
    assert not (tmp_path / job_id / "scene_003.srt").exists()
    captions_text = (tmp_path / job_id / "captions.srt").read_text(encoding="utf-8")
    assert "Terms, conditions" not in captions_text


@pytest.fixture
def anyio_backend():
    return "asyncio"
