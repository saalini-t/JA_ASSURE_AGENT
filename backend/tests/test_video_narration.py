"""
Phase 2 tests: TTS provider contract, measured-audio-duration authority, SRT caption
generation/validation, and the FFmpeg audio+caption pipeline. External TTS calls are
mocked in unit tests; the full pipeline integration test (test_full_narrated_pipeline_*)
uses SilentTestTTSProvider -- a REAL local WAV file, no network -- so the actual FFmpeg
audio-muxing pipeline is genuinely exercised, not mocked away.
"""
import json
import subprocess
import uuid

import pytest

from app.services import caption_service
from app.services import video_generation_service as vgs
from app.services.ffmpeg_locator import resolve_ffmpeg, resolve_ffprobe
from app.services.tts_providers import (
    VideoTTSProvider,
    OpenAITTSProvider,
    SilentTestTTSProvider,
    TTSGenerationError,
)
from app.services.video_generation_service import (
    generate_video_mvp,
    _render_narrated_scene_clip,
    _probe_audio_duration,
    _probe_final_output,
    VideoGenerationError,
)

from tests.test_video_generation import _make_scene, _make_script, _binary_available  # reuse existing fixtures

FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)
FFPROBE_AVAILABLE = _binary_available(resolve_ffprobe)


# ---------------------------------------------------------------------------
# A. TTS provider interface
# ---------------------------------------------------------------------------

def test_a_tts_providers_implement_the_common_interface():
    assert issubclass(OpenAITTSProvider, VideoTTSProvider)
    assert issubclass(SilentTestTTSProvider, VideoTTSProvider)
    assert OpenAITTSProvider().name == "openai_tts"
    assert SilentTestTTSProvider().name == "silent_test_provider"


def test_a_cannot_instantiate_the_abstract_interface_directly():
    with pytest.raises(TypeError):
        VideoTTSProvider()  # abstract -- must be subclassed


# ---------------------------------------------------------------------------
# B. TTS failure handling
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_b_openai_tts_raises_explicit_error_without_credential(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    provider = OpenAITTSProvider()
    assert provider.is_configured is False

    with pytest.raises(TTSGenerationError, match="OPENAI_API_KEY is not configured"):
        await provider.generate_voiceover("Hello", tmp_path / "out.mp3")


@pytest.mark.anyio
async def test_b_pipeline_reports_explicit_tts_failed_stage_not_silent_success(tmp_path, monkeypatch):
    """The pipeline must never report a narrated video as successful when TTS fails.

    VoiceAgentTTSProvider (gTTS) is now the pipeline's default and needs no API key,
    so OpenAITTSProvider is injected explicitly here to keep testing THIS provider's
    explicit-failure-on-missing-credential behavior.
    """
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # OpenAITTSProvider will raise
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[_make_scene(scene_number=1, duration_seconds=6)])
    result = await generate_video_mvp(
        script, job_id="tts-fail-test", narrate=True, tts_provider=OpenAITTSProvider()
    )

    assert result.success is False
    assert result.error_stage == "tts"
    assert result.has_audio is False


# ---------------------------------------------------------------------------
# C. Measured audio duration
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFPROBE_AVAILABLE, reason="ffprobe not installed on this machine")
@pytest.mark.anyio
async def test_c_measured_audio_duration_is_read_from_the_real_file(tmp_path):
    provider = SilentTestTTSProvider(duration_seconds=2.5)
    audio_path = tmp_path / "scene_001.wav"
    await provider.generate_voiceover("irrelevant text", audio_path)

    measured = _probe_audio_duration(audio_path)

    assert 2.3 <= measured <= 2.7  # measured, not assumed -- small tolerance for encoding rounding


def test_c_probe_raises_on_missing_audio_file(tmp_path):
    with pytest.raises(VideoGenerationError) as exc_info:
        _probe_audio_duration(tmp_path / "does_not_exist.wav")
    assert exc_info.value.stage == "tts"


# ---------------------------------------------------------------------------
# D/E/F. SRT generation, validity, and the "cannot exceed audio duration" rule
# ---------------------------------------------------------------------------

def test_d_build_scene_cues_produces_cumulative_srt_matching_the_brief_format():
    cues = caption_service.build_scene_cues([
        ("Your jewellery deserves protection.", 2.5),
        ("Especially when travelling internationally.", 2.5),
    ])
    srt_text = caption_service.render_srt(cues)

    assert srt_text.startswith("1\n00:00:00,000 --> 00:00:02,500\n")
    assert "2\n00:00:02,500 --> 00:00:05,000\n" in srt_text
    assert "Your jewellery deserves protection." in srt_text
    assert "Especially when travelling internationally." in srt_text


def test_e_valid_srt_passes_validation():
    cues = caption_service.build_scene_cues([("First scene.", 3.0), ("Second scene.", 2.0)])
    result = caption_service.validate_srt(cues, total_duration_seconds=5.0)
    assert result.valid is True
    assert result.errors == []


def test_e_srt_with_end_before_start_fails_validation():
    bad_cue = caption_service.CaptionCue(index=1, start_ms=2000, end_ms=1000, text="broken")
    result = caption_service.validate_srt([bad_cue])
    assert result.valid is False
    assert any("must be after start" in e for e in result.errors)


def test_e_srt_with_no_cues_fails_validation():
    result = caption_service.validate_srt([])
    assert result.valid is False


def test_f_captions_cannot_exceed_audio_duration():
    cues = caption_service.build_scene_cues([("Runs long.", 10.0)])
    # Audio is only 4 seconds -- the 10-second cue must be rejected.
    result = caption_service.validate_srt(cues, total_duration_seconds=4.0)
    assert result.valid is False
    assert any("exceeds the total audio duration" in e for e in result.errors)


def test_f_local_cue_is_rebased_to_zero():
    cue = caption_service.build_local_cue("A single scene caption.", 3.2)
    assert cue.start_ms == 0
    assert cue.end_ms == 3200


# ---------------------------------------------------------------------------
# G/H/I/J. FFmpeg scene with audio, and final MP4 stream/format validation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_g_narrated_scene_clip_has_video_and_audio(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    from app.services.video_providers import ImageMotionProvider

    image_path = tmp_path / "scene_001.png"
    await ImageMotionProvider().generate_scene_visual(_make_scene(), "jade", image_path)

    audio_path = tmp_path / "scene_001.wav"
    await SilentTestTTSProvider(duration_seconds=2.0).generate_voiceover("test", audio_path)

    caption_path = tmp_path / "scene_001.srt"
    caption_path.write_text("Protect what matters most.", encoding="utf-8")

    clip_path = tmp_path / "scene_001_clip.mp4"
    _render_narrated_scene_clip(
        tmp_path, image_path.name, audio_path.name, caption_path.name,
        clip_path.name, duration_seconds=2.0, motion="zoom_in",
    )

    assert clip_path.exists() and clip_path.stat().st_size > 0
    duration, has_audio = _probe_final_output(clip_path, require_audio=True)
    assert has_audio is True
    assert duration > 0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_full_narrated_pipeline_produces_real_mp4_with_audio_and_captions(tmp_path, monkeypatch):
    """
    REAL local integration test: exercises the actual FFmpeg pipeline (image
    fallback, audio muxing, caption burn-in, concat, ffprobe validation) end to
    end. Only the network TTS call is substituted -- SilentTestTTSProvider writes a
    genuine local WAV file, so everything downstream of it is the real thing.
    """
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # fallback images, no network
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[
        _make_scene(scene_number=1, duration_seconds=5, voiceover="Your jewellery deserves real protection."),
        _make_scene(scene_number=2, duration_seconds=5, voiceover="Especially when travelling internationally."),
    ])

    job_id = uuid.uuid4().hex[:8]
    result = await generate_video_mvp(
        script, job_id=job_id, narrate=True, tts_provider=SilentTestTTSProvider(duration_seconds=3.0)
    )

    assert result.success is True, result.error_message

    # H/I: final MP4 has both a video AND an audio stream (ffprobe, not assumed)
    assert result.has_audio is True
    duration, has_audio = _probe_final_output(result.video_path, require_audio=True)
    assert has_audio is True

    # Captions were generated and validated
    assert result.has_captions is True
    assert result.caption_file == f"/media/generated/{job_id}/captions.srt"
    captions_on_disk = tmp_path / job_id / "captions.srt"
    assert captions_on_disk.exists()
    srt_content = captions_on_disk.read_text(encoding="utf-8")
    assert "Your jewellery deserves real protection." in srt_content
    assert "Especially when travelling internationally." in srt_content

    # J: resolution / fps / codec on the actual file, via ffprobe
    ffprobe_bin = resolve_ffprobe()
    proc = subprocess.run(
        [ffprobe_bin, "-v", "error", "-show_entries",
         "stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt",
         "-of", "json", str(result.video_path)],
        capture_output=True, text=True, timeout=30,
    )
    info = json.loads(proc.stdout)
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")

    assert video_stream["codec_name"] == "h264"
    assert video_stream["width"] == 1080
    assert video_stream["height"] == 1920
    assert video_stream["r_frame_rate"] == "30/1"
    assert video_stream["pix_fmt"] == "yuv420p"
    assert audio_stream["codec_name"] == "aac"


# ---------------------------------------------------------------------------
# L. Existing Phase 1 behavior is unaffected by default (narrate=False)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_l_default_narrate_false_produces_silent_video_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[_make_scene(scene_number=1, duration_seconds=5)])
    result = await generate_video_mvp(script, job_id="phase1-unaffected")  # no narrate kwarg at all

    assert result.success is True, result.error_message
    assert result.has_audio is False
    assert result.has_captions is False
    assert result.caption_file is None


@pytest.fixture
def anyio_backend():
    return "asyncio"
