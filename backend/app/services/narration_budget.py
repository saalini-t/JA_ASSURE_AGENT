"""
Narration-duration budgeting for the video pipeline -- runs AFTER scene duration
normalization and validation, BEFORE any TTS call. Estimates how long each scene's
voiceover text will take to speak (deterministic word-count math, no TTS call
needed), and rewrites any scene whose narration would overrun its own allotted
on-screen time, so a requested target_duration doesn't blow out because the LLM
wrote more narration than a scene's runtime can hold.

This does NOT replace measured TTS duration as the final authority (see
video_generation_service.py, which still measures the real synthesized audio and
uses that for the rendered clip length) -- it's a best-effort pre-check that makes
overruns rare rather than eliminating them by contract. Silent disclaimer/end-card
scenes (blank voiceover) are skipped entirely: they contribute their planned
duration to the video's runtime but never compete for narration time.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings
from app.schemas.agent_contracts import VideoScene, VideoScript
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.video.narration_budget")

# Documented assumption: 150 words/minute is a standard reference pace for a
# measured, professional/informative voiceover read (typical cited range for
# narration and e-learning VO is ~130-160 wpm; conversational speech is faster).
# Overridable via NARRATION_WORDS_PER_MINUTE in settings without a code change.
DEFAULT_WORDS_PER_MINUTE = 150.0

# A scene's spoken narration is only allowed to fill this fraction of its own
# planned on-screen duration -- the remainder is reserved headroom for the visual
# beat, camera motion, and the transition into the next scene, so narration isn't
# assumed to occupy literally every second a scene is on screen.
NARRATION_FRACTION_OF_SCENE = 0.85

# How far over its own budget a scene's ESTIMATED narration may run before this
# module rewrites it. Looser than TARGET_DURATION_TOLERANCE (0.15) because a
# word-count estimate is inherently approximate -- measured TTS duration (not this
# estimate) remains the final authority once synthesis actually happens.
BUDGET_TOLERANCE = 0.20


def _words_per_minute() -> float:
    return getattr(settings, "NARRATION_WORDS_PER_MINUTE", DEFAULT_WORDS_PER_MINUTE) or DEFAULT_WORDS_PER_MINUTE


def estimate_narration_seconds(text: str, words_per_minute: Optional[float] = None) -> float:
    """Deterministic word-count-based estimate of spoken duration. No LLM, no TTS."""
    words = len((text or "").split())
    if words == 0:
        return 0.0
    wpm = words_per_minute or _words_per_minute()
    return words / (wpm / 60.0)


def scene_budget_seconds(scene: VideoScene) -> float:
    """Seconds of narration a single scene's own planned duration allows for."""
    return scene.duration_seconds * NARRATION_FRACTION_OF_SCENE


@dataclass
class SceneNarrationReport:
    scene_number: int
    original_word_count: int
    original_estimated_seconds: float
    budget_seconds: float
    was_rewritten: bool
    final_word_count: int
    final_estimated_seconds: float
    still_over_budget: bool


@dataclass
class NarrationBudgetReport:
    scenes: List[SceneNarrationReport] = field(default_factory=list)

    @property
    def any_rewritten(self) -> bool:
        return any(s.was_rewritten for s in self.scenes)

    @property
    def any_still_over_budget(self) -> bool:
        return any(s.still_over_budget for s in self.scenes)

    @property
    def total_estimated_seconds(self) -> float:
        return sum(s.final_estimated_seconds for s in self.scenes)


def _split_sentences(text: str) -> List[str]:
    """Deterministic whole-sentence splitter -- good enough for short VO lines.
    Used only by the no-LLM fallback so trimming never cuts a sentence in half."""
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p for p in parts if p]


def _deterministic_trim(text: str, target_words: int, disclaimer: Optional[str] = None) -> str:
    """
    Trims by whole sentences, never mid-sentence: always keeps at least the first
    sentence (even if it alone exceeds target_words -- a genuinely too-long single
    sentence is a content problem no amount of trimming can fix safely), then adds
    further whole sentences only while staying within budget. Appends the required
    disclaimer verbatim if it isn't already present in the kept text.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return (text or "").strip()

    kept = [sentences[0]]
    word_count = len(sentences[0].split())
    for sentence in sentences[1:]:
        next_count = word_count + len(sentence.split())
        if next_count > target_words:
            break
        kept.append(sentence)
        word_count = next_count

    trimmed = " ".join(kept)
    if disclaimer and disclaimer.strip() and disclaimer.strip() not in trimmed:
        trimmed = f"{trimmed} {disclaimer.strip()}"
    return trimmed


def _llm_rewrite(text: str, target_words: int, disclaimer: Optional[str], brand: str) -> Optional[str]:
    system_prompt = (
        f"You are a professional video voiceover script editor for {brand}, an insurance brand. "
        f"Rewrite narration lines to fit a strict spoken-word budget while preserving the core "
        f"message, tone, and any required legal/compliance disclaimer content."
    )
    disclaimer_clause = (
        f"MANDATORY: the rewritten line must still convey this required disclaimer content "
        f"(paraphrase or include verbatim): \"{disclaimer}\"\n\n" if disclaimer else ""
    )
    prompt = (
        f"ORIGINAL VOICEOVER LINE:\n\"\"\"\n{text}\n\"\"\"\n\n"
        f"TARGET LENGTH: approximately {target_words} words or fewer -- this scene has a strict "
        f"time budget when spoken aloud at a natural pace.\n\n"
        f"{disclaimer_clause}"
        f"Rewrite the line to be more concise while preserving its core meaning and brand tone. "
        f"Do not cut off mid-sentence -- produce a complete, natural-sounding line. "
        f"Return ONLY the rewritten voiceover text, no meta-commentary, no surrounding quotes."
    )
    try:
        rewritten = llm_provider.generate_text(prompt=prompt, system_instruction=system_prompt)
        rewritten = (rewritten or "").strip()
        if rewritten and not rewritten.startswith("[Demo Mode"):
            return rewritten
    except Exception as e:
        logger.warning(f"Narration budget LLM rewrite failed, using deterministic fallback: {e}")
    return None


def rewrite_narration_to_fit_budget(
    text: str, budget_seconds: float, disclaimer: Optional[str] = None, brand: str = "jade"
) -> str:
    """
    Shortens `text` to approximately fit `budget_seconds` of speaking time. Tries an
    LLM rewrite first (if configured/live); falls back to a deterministic whole-
    sentence trim otherwise or if the LLM call fails. Never returns an empty string
    and never truncates mid-sentence.
    """
    target_words = max(5, int(budget_seconds * _words_per_minute() / 60.0))

    if llm_provider.is_live:
        rewritten = _llm_rewrite(text, target_words, disclaimer, brand)
        if rewritten:
            return rewritten

    return _deterministic_trim(text, target_words, disclaimer)


def enforce_narration_budget(script: VideoScript) -> NarrationBudgetReport:
    """
    Mutates script.scenes in place: any narrated scene (non-empty voiceover) whose
    estimated speaking time exceeds its own budget (scene_budget_seconds, with
    BUDGET_TOLERANCE headroom) gets its voiceover rewritten to fit. Rewriting is
    attempted once per scene -- if the rewrite still estimates over budget, the
    best-effort result is kept (measured TTS duration is the real final authority;
    see video_generation_service.py) and this is reported, not silently hidden.
    """
    report = NarrationBudgetReport()
    brand = script.brand or "jade"

    for scene in script.scenes:
        original_text = (scene.voiceover or "").strip()
        if not original_text:
            continue  # silent disclaimer/end-card scene -- no narration to budget

        budget = scene_budget_seconds(scene)
        original_words = len(original_text.split())
        original_estimate = estimate_narration_seconds(original_text)

        if original_estimate <= budget * (1 + BUDGET_TOLERANCE):
            report.scenes.append(SceneNarrationReport(
                scene_number=scene.scene_number,
                original_word_count=original_words,
                original_estimated_seconds=original_estimate,
                budget_seconds=budget,
                was_rewritten=False,
                final_word_count=original_words,
                final_estimated_seconds=original_estimate,
                still_over_budget=False,
            ))
            continue

        logger.info(
            f"Scene {scene.scene_number} narration estimated at {original_estimate:.1f}s "
            f"exceeds its {budget:.1f}s budget ({original_words} words) -- rewriting to fit."
        )
        rewritten_text = rewrite_narration_to_fit_budget(
            original_text, budget, disclaimer=scene.compliance_disclaimer, brand=brand
        )
        scene.voiceover = rewritten_text
        final_words = len(rewritten_text.split())
        final_estimate = estimate_narration_seconds(rewritten_text)
        still_over = final_estimate > budget * (1 + BUDGET_TOLERANCE)
        if still_over:
            logger.warning(
                f"Scene {scene.scene_number} narration still estimated at {final_estimate:.1f}s "
                f"after rewrite (budget {budget:.1f}s) -- proceeding with best-effort text; "
                f"measured TTS duration will be authoritative for the rendered clip length."
            )

        report.scenes.append(SceneNarrationReport(
            scene_number=scene.scene_number,
            original_word_count=original_words,
            original_estimated_seconds=original_estimate,
            budget_seconds=budget,
            was_rewritten=True,
            final_word_count=final_words,
            final_estimated_seconds=final_estimate,
            still_over_budget=still_over,
        ))

    return report
