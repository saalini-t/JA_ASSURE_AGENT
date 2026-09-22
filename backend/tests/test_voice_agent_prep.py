import pytest
from app.services.voice_agent import VoiceAgent, clean_voiceover_text
from app.schemas.agent_contracts import VideoScript, VideoScene


def test_clean_voiceover_stage_directions():
    raw = "[Visual: Luxury diamond ring] (voiceover:) Protect your heirloom pieces today. [Music swells]"
    cleaned = clean_voiceover_text(raw)
    assert "[Visual" not in cleaned
    assert "[Music swells]" not in cleaned
    assert "(voiceover:)" not in cleaned
    assert cleaned == "Protect your heirloom pieces today."


def test_clean_voiceover_markdown_formatting():
    raw = "Here is **essential** protection for *rare jewels* and `precious gems`! Visit https://ja-assure.com."
    cleaned = clean_voiceover_text(raw)
    assert "**" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "https://" not in cleaned
    assert "essential protection for rare jewels and precious gems" in cleaned


def test_clean_voiceover_regional_acronyms():
    raw = "Our policies strictly comply with MAS guidelines, MOH standards, and PDPA security. Powered by advanced AI for B2B."
    cleaned = clean_voiceover_text(raw)
    assert "M-A-S" in cleaned
    assert "M-O-H" in cleaned
    assert "P-D-P-A" in cleaned
    assert "A-I" in cleaned
    assert "B-to-B" in cleaned


def test_clean_voiceover_currencies_and_abbreviations():
    raw = "Coverage starts at S$500 in Singapore and RM 800 in Malaysia, e.g. w/ full transit riders."
    cleaned = clean_voiceover_text(raw)
    assert "500 Singapore dollars" in cleaned
    assert "800 Ringgit" in cleaned
    assert "for example" in cleaned
    assert "with full transit riders" in cleaned


def test_voice_agent_prepare_video_script():
    agent = VoiceAgent()
    script = VideoScript(
        brand="jade",
        scenes=[
            VideoScene(
                scene_number=1,
                visual_description="Ring display",
                voiceover="[Scene 1] **Jade** safeguards your legacy w/ MAS compliance.",
                onscreen_text="Jade Security"
            ),
            VideoScene(
                scene_number=2,
                visual_description="Vault door",
                voiceover="Only S$1,000 annual premium w/o hidden fees.",
                onscreen_text="Affordable"
            )
        ]
    )

    prepared = agent.prepare_video_script(script)
    assert prepared.scenes[0].voiceover == "Jade safeguards your legacy with M-A-S compliance."
    assert "Singapore dollars" in prepared.scenes[1].voiceover
    assert "without hidden fees" in prepared.scenes[1].voiceover
