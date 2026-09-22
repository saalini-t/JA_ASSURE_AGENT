"""
Unit tests for narration_budget.py -- deterministic word-count estimation, per-scene
budget calculation, and the rewrite-to-fit logic (LLM path + deterministic sentence-
trim fallback). No TTS, no ffmpeg, no network: these test pure Python logic.
"""
from app.schemas.agent_contracts import VideoScene, VideoScript
from app.services import narration_budget as nb


def _scene(voiceover, duration_seconds=10, disclaimer=None, scene_number=1):
    return VideoScene(
        scene_number=scene_number,
        duration_seconds=duration_seconds,
        visual_description="A diamond ring on velvet.",
        voiceover=voiceover,
        onscreen_text="Protected.",
        compliance_disclaimer=disclaimer,
    )


def _script(scenes):
    return VideoScript(
        title="Narration Budget Test", brand="jade", target_platform="reel",
        disclaimer="*Terms and conditions apply.*", scenes=scenes,
    )


def _make_llm_live(monkeypatch, fake_text: str):
    """Forces llm_provider.is_live True and generate_text to return fake_text --
    is_live is a property on the shared LLMProvider singleton, so it's patched on
    the class (affects the instance via normal descriptor lookup)."""
    monkeypatch.setattr(type(nb.llm_provider), "is_live", property(lambda self: True))
    monkeypatch.setattr(nb.llm_provider, "generate_text", lambda prompt, system_instruction=None: fake_text)


# ---------------------------------------------------------------------------
# a. Comfortably within budget -- untouched
# ---------------------------------------------------------------------------

def test_a_narration_comfortably_within_budget_is_not_rewritten():
    # 10s scene -> budget = 8.5s @ 150wpm = ~21 words allowed; this line is 6 words.
    scene = _scene("Protect your jewellery collection today.", duration_seconds=10)
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    assert report.any_rewritten is False
    assert scene.voiceover == "Protect your jewellery collection today."
    entry = report.scenes[0]
    assert entry.still_over_budget is False


# ---------------------------------------------------------------------------
# b. Slightly over budget -- deterministic fallback rewrite (no LLM configured
#    under the standard GROQ_API_KEY="" test invocation)
# ---------------------------------------------------------------------------

def test_b_narration_slightly_over_budget_is_rewritten_by_deterministic_fallback():
    # 5s scene -> budget = 4.25s @ 150wpm = ~10 words. This is two short sentences,
    # ~16 words total -- moderately over, not wildly so.
    text = "Protect your entire jewellery collection with agreed value coverage. It travels with you everywhere."
    scene = _scene(text, duration_seconds=5)
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    assert report.any_rewritten is True
    entry = report.scenes[0]
    assert entry.was_rewritten is True
    # Trimmed by whole sentences -- the kept text must be a genuine prefix of
    # complete sentences, never a mid-sentence cut.
    assert scene.voiceover == "Protect your entire jewellery collection with agreed value coverage."
    assert entry.final_word_count < entry.original_word_count


# ---------------------------------------------------------------------------
# c. Significantly over budget -- aggressive trim, still whole-sentence
# ---------------------------------------------------------------------------

def test_c_narration_significantly_over_budget_keeps_at_least_one_full_sentence():
    # 3s scene -> budget = 2.55s @ 150wpm = ~6 words. Even the first sentence alone
    # is far longer than that -- deterministic fallback must still keep it whole
    # rather than cutting mid-sentence, and report the residual overage honestly.
    text = (
        "Our comprehensive jewellery protection plan covers loss, theft, and accidental "
        "damage anywhere in the world you travel. It also includes agreed-value payouts."
    )
    scene = _scene(text, duration_seconds=3)
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    entry = report.scenes[0]
    assert entry.was_rewritten is True
    assert scene.voiceover.startswith("Our comprehensive jewellery protection plan covers")
    assert scene.voiceover.count(".") <= 1 or scene.voiceover.endswith(
        "you travel."
    )  # kept only the first whole sentence
    assert entry.still_over_budget is True  # first sentence alone still exceeds ~6 words -- honestly reported


# ---------------------------------------------------------------------------
# d. Successful rewrite into budget via the LLM path
# ---------------------------------------------------------------------------

def test_d_successful_llm_rewrite_replaces_voiceover_and_fits_budget(monkeypatch):
    _make_llm_live(monkeypatch, "Protect your collection, wherever you travel.")

    text = "Protect your entire jewellery collection with agreed value coverage that travels everywhere you go, worldwide."
    scene = _scene(text, duration_seconds=5)  # budget ~10 words
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    entry = report.scenes[0]
    assert entry.was_rewritten is True
    assert scene.voiceover == "Protect your collection, wherever you travel."
    assert entry.still_over_budget is False


# ---------------------------------------------------------------------------
# e. Failed rewrite / still too long -- LLM returns something still over budget,
#    or LLM fails outright and deterministic fallback is used instead. Either way
#    the pipeline must not error out or produce an empty voiceover.
# ---------------------------------------------------------------------------

def test_e_llm_failure_falls_back_to_deterministic_trim(monkeypatch):
    monkeypatch.setattr(type(nb.llm_provider), "is_live", property(lambda self: True))

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated Groq outage")

    monkeypatch.setattr(nb.llm_provider, "generate_text", _raise)

    text = "Protect your entire jewellery collection with agreed value coverage. It travels with you everywhere."
    scene = _scene(text, duration_seconds=5)
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    assert report.scenes[0].was_rewritten is True
    assert scene.voiceover  # never empty
    assert scene.voiceover == "Protect your entire jewellery collection with agreed value coverage."


def test_e_rewrite_still_over_budget_is_reported_not_hidden(monkeypatch):
    # LLM "rewrite" that itself is still too long for the budget -- must be reported
    # as still_over_budget rather than silently treated as a success.
    _make_llm_live(monkeypatch, "This rewritten line is still much too long for the tiny time budget given.")

    scene = _scene("Original overly long narration line that definitely exceeds budget here.", duration_seconds=2)
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    entry = report.scenes[0]
    assert entry.was_rewritten is True
    assert entry.still_over_budget is True
    assert scene.voiceover  # best-effort text kept, not discarded


# ---------------------------------------------------------------------------
# f. Silent disclaimer/end-card scene -- never touched by narration budgeting
# ---------------------------------------------------------------------------

def test_f_silent_disclaimer_scene_is_skipped_entirely():
    scene = _scene("", duration_seconds=5, disclaimer="*Terms, conditions, and underwriting limits apply.*")
    script = _script([scene])

    report = nb.enforce_narration_budget(script)

    assert report.scenes == []  # no report entry at all for a silent scene
    assert scene.voiceover == ""  # untouched


# ---------------------------------------------------------------------------
# g. Mixed narrated + silent scenes -- only the narrated, over-budget one is rewritten
# ---------------------------------------------------------------------------

def test_g_mixed_narrated_and_silent_scenes_only_rewrites_the_narrated_one():
    narrated = _scene(
        "Protect your entire jewellery collection with agreed value coverage. It travels with you everywhere.",
        duration_seconds=4, scene_number=1,
    )
    silent = _scene("", duration_seconds=5, disclaimer="*Terms and conditions apply.*", scene_number=2)
    script = _script([narrated, silent])

    report = nb.enforce_narration_budget(script)

    assert len(report.scenes) == 1
    assert report.scenes[0].scene_number == 1
    assert report.any_rewritten is True
    assert silent.voiceover == ""  # untouched
    assert narrated.voiceover == "Protect your entire jewellery collection with agreed value coverage."


# ---------------------------------------------------------------------------
# Estimation helper sanity
# ---------------------------------------------------------------------------

def test_estimate_narration_seconds_is_deterministic_and_word_count_based():
    assert nb.estimate_narration_seconds("") == 0.0
    ten_words = "one two three four five six seven eight nine ten"
    # 10 words @ 150wpm (2.5 words/sec) = 4.0s
    assert abs(nb.estimate_narration_seconds(ten_words, words_per_minute=150.0) - 4.0) < 0.01
