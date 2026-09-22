"""
Pipeline-level tests for narration-duration budgeting: proves that a requested
target_duration no longer blows out because generated narration was too long to
speak within its scene's allotted time.

Uses a test-only TTS provider whose synthesized (silent) audio duration is
proportional to the input text's word count -- simulating real TTS pacing
deterministically, with no network call, so these tests can verify that a REWRITTEN
(shorter) narration actually produces a shorter clip, not just that some rewrite
happened.
"""
import wave

import pytest

from app.services import video_generation_service as vgs
from app.services.video_generation_service import generate_video_mvp
from app.services.ffmpeg_locator import resolve_ffmpeg
from tests.test_video_generation import _make_scene, _make_script

# Same documented pace narration_budget.py assumes by default, so a scene rewritten
# to fit its budget also fits when "spoken" by this provider.
_WORDS_PER_MINUTE = 150.0


def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)


class ProportionalTTSProvider:
    """
    Test double: produces a real, valid, silent WAV whose duration is proportional
    to the input text's word count at a fixed words-per-minute rate -- simulating
    real TTS pacing without a network call. Lets duration-budgeting tests verify
    that a shorter (rewritten) narration line genuinely produces a shorter clip.
    """

    def __init__(self, words_per_minute: float = _WORDS_PER_MINUTE):
        self.words_per_minute = words_per_minute

    @property
    def name(self) -> str:
        return "proportional_test_provider"

    async def generate_voiceover(self, text, output_path, voice=None):
        words = len((text or "").split())
        duration = max(0.5, words / (self.words_per_minute / 60.0))
        framerate = 16000
        n_frames = int(framerate * duration)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(framerate)
            wav_file.writeframes(b"\x00\x00" * n_frames)
        return output_path


def _overlong_scenes(count: int, per_scene_seconds: int):
    """Scenes whose voiceover is deliberately far too long to speak within
    per_scene_seconds -- simulates an LLM that ignored the duration budget, which is
    exactly the failure mode this whole feature exists to correct. Many short
    sentences (~5 words each, matching real Groq-generated narration style) so the
    whole-sentence-only deterministic trim fallback has fine enough granularity to
    land close to the budget rather than stopping short after just one big sentence."""
    overlong_text = (
        "Protect your jewellery collection today. Agreed value coverage is included. "
        "Worldwide transit protection applies here. Zero deductible for certified items. "
        "Fast claims processing is guaranteed. Trusted by collectors worldwide. "
        "Coverage extends to private vaults. Exhibitions and travel are included. "
        "Specialist underwriters review every claim. Your legacy pieces stay protected. "
        "Peace of mind comes standard. Speak to our specialist team today."
    )
    return [
        _make_scene(scene_number=i + 1, duration_seconds=per_scene_seconds, voiceover=overlong_text)
        for i in range(count)
    ]


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_h_requested_30_second_video_lands_near_target(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")  # fallback images, no network
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    # 4 scenes at 7-8s each (~30s total) -- narration is deliberately far too long
    # for each scene's slice before budgeting runs.
    scenes = _overlong_scenes(4, per_scene_seconds=8)
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(
        script, job_id="duration-30s-test", target_duration_seconds=30,
        narrate=True, tts_provider=ProportionalTTSProvider(),
    )

    assert result.success is True, result.error_message
    assert result.narration_rewritten is True
    # Previously this kind of overlong narration produced ~2x the requested
    # duration (68s/40s for a 30s request) -- budgeting must bring it back close.
    assert abs(result.duration_seconds - 30) <= 30 * 0.30, (
        f"expected ~30s, got {result.duration_seconds}s"
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_i_requested_60_second_video_lands_near_target(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    scenes = _overlong_scenes(5, per_scene_seconds=12)  # ~60s total
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(
        script, job_id="duration-60s-test", target_duration_seconds=60,
        narrate=True, tts_provider=ProportionalTTSProvider(),
    )

    assert result.success is True, result.error_message
    assert result.narration_rewritten is True
    assert abs(result.duration_seconds - 60) <= 60 * 0.30, (
        f"expected ~60s, got {result.duration_seconds}s"
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_j_final_duration_tolerance_is_documented_and_enforced_in_test(tmp_path, monkeypatch):
    """
    Explicit tolerance check (kept separate from h/i per the requirement list): the
    final rendered duration must be within a reasonable, DOCUMENTED tolerance of the
    requested target, not mathematically exact. 30% is generous on top of
    narration_budget's own BUDGET_TOLERANCE (20%) and video_generation_service's
    TARGET_DURATION_TOLERANCE (15%) stacking through planning + real TTS variance.
    """
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    target = 30
    scenes = _overlong_scenes(4, per_scene_seconds=8)
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(
        script, job_id="duration-tolerance-test", target_duration_seconds=target,
        narrate=True, tts_provider=ProportionalTTSProvider(),
    )

    assert result.success is True, result.error_message
    relative_deviation = abs(result.duration_seconds - target) / target
    assert relative_deviation <= 0.30, (
        f"final duration {result.duration_seconds}s deviates {relative_deviation:.0%} from target {target}s"
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_narration_budgeting_coexists_with_silent_disclaimer_scene(tmp_path, monkeypatch):
    """Budgeting must not touch a silent disclaimer/end-card scene, and the silent-
    scene handling (no TTS call, real digital silence, kept on screen) must still
    work correctly alongside budgeting of the OTHER, narrated scenes."""
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    overlong_text = (
        "Protect your jewellery collection today. Agreed value coverage is included. "
        "Worldwide transit protection applies here. Zero deductible for certified items. "
        "Fast claims processing is guaranteed. Trusted by collectors worldwide. "
        "Coverage extends to private vaults. Exhibitions and travel are included."
    )
    scenes = [
        _make_scene(scene_number=1, duration_seconds=8, voiceover=overlong_text),
        _make_scene(scene_number=2, duration_seconds=8, voiceover=overlong_text),
        _make_scene(
            scene_number=3, duration_seconds=5, voiceover="",
            visual_description="Jade logo with statutory disclaimer text on screen.",
            onscreen_text="*Terms, conditions, and underwriting limits apply.*",
            compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*",
        ),
    ]
    script = _make_script(scenes=scenes)

    result = await generate_video_mvp(
        script, job_id="duration-mixed-silent-test", target_duration_seconds=21,
        narrate=True, tts_provider=ProportionalTTSProvider(),
    )

    assert result.success is True, result.error_message
    assert result.scenes_generated == 3
    assert result.narration_rewritten is True
    assert result.has_audio is True

    # the disclaimer scene's own clip must exist and never have been sent to TTS
    assert not (tmp_path / "duration-mixed-silent-test" / "scene_003.srt").exists()
    captions_text = (tmp_path / "duration-mixed-silent-test" / "captions.srt").read_text(encoding="utf-8")
    assert "Terms, conditions" not in captions_text


@pytest.fixture
def anyio_backend():
    return "asyncio"
