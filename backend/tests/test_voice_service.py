import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.voice_service import (
    VoiceService,
    TTSProvider,
    GttsProvider,
    VoiceEmptyError,
    VoiceLanguageError,
    SUPPORTED_LANGUAGE_MAPPING
)
from app.schemas.agent_contracts import VideoScript, VideoScene, VoiceConfig

client = TestClient(app)


class MockTTSProvider(TTSProvider):
    """Mock TTS provider to avoid real network requests during automated tests."""
    @property
    def provider_name(self) -> str:
        return "mock_gtts"

    def synthesize(self, text: str, language_code: str, voice_config=None) -> bytes:
        # Return a minimal valid dummy MP3 byte sequence
        # (ID3v2 header + small MPEG frame payload)
        dummy_mp3_header = b"ID3\x04\x00\x00\x00\x00\x00#TIT2\x00\x00\x00\x05\x00\x00\x00Mock"
        return dummy_mp3_header + (b"\xff\xfb\x90d\x00" * 20)


@pytest.fixture
def temp_voice_service(tmp_path):
    """Provides a VoiceService instance targeting a clean temporary directory with mock provider."""
    mock_provider = MockTTSProvider()
    service = VoiceService(media_root=tmp_path / "voiceovers", provider=mock_provider)
    return service


# 1. VoiceService initialization
def test_01_voice_service_initialization(temp_voice_service):
    assert temp_voice_service.media_root.exists()
    assert temp_voice_service.provider.provider_name == "mock_gtts"


# 2. Empty voiceover handling
def test_02_empty_voiceover_handling(temp_voice_service):
    # Test completely empty script
    empty_script = VideoScript(brand="jade", scenes=[])
    with pytest.raises(VoiceEmptyError) as exc_info:
        temp_voice_service.synthesize_from_script(empty_script)
    assert "contains no scenes" in str(exc_info.value)

    # Test scenes with only whitespace
    blank_scenes_script = VideoScript(
        brand="jade",
        scenes=[VideoScene(scene_number=1, visual_description="None", voiceover="   ", onscreen_text="")]
    )
    with pytest.raises(VoiceEmptyError) as exc_info2:
        temp_voice_service.synthesize_from_script(blank_scenes_script)
    assert "empty voiceover fields" in str(exc_info2.value)


# 3. Supported language mapping (English, Malay, Indonesian, Thai, Chinese)
def test_03_supported_language_mapping(temp_voice_service):
    assert temp_voice_service.normalize_language("en") == "en"
    assert temp_voice_service.normalize_language("English") == "en"
    assert temp_voice_service.normalize_language("ms") == "ms"
    assert temp_voice_service.normalize_language("Malay") == "ms"
    assert temp_voice_service.normalize_language("id") == "id"
    assert temp_voice_service.normalize_language("Bahasa Indonesia") == "id"
    assert temp_voice_service.normalize_language("th") == "th"
    assert temp_voice_service.normalize_language("Thai") == "th"
    assert temp_voice_service.normalize_language("zh") == "zh-CN"
    assert temp_voice_service.normalize_language("zh-cn") == "zh-CN"
    assert temp_voice_service.normalize_language("Chinese") == "zh-CN"


# 4. Unsupported language handling
def test_04_unsupported_language_handling(temp_voice_service):
    with pytest.raises(VoiceLanguageError) as exc:
        temp_voice_service.normalize_language("klingon")
    assert "Unsupported language code" in str(exc.value)

    # Tamil is explicitly disallowed per user instruction
    with pytest.raises(VoiceLanguageError):
        temp_voice_service.normalize_language("ta")


# 5. Multiple scene voiceover concatenation in correct order
def test_05_scene_voiceover_concatenation(temp_voice_service):
    script = VideoScript(
        brand="doctorshield",
        scenes=[
            VideoScene(scene_number=2, visual_description="Scene 2", voiceover="Second paragraph.", onscreen_text="2"),
            VideoScene(scene_number=1, visual_description="Scene 1", voiceover="First sentence.", onscreen_text="1"),
            VideoScene(scene_number=3, visual_description="Scene 3", voiceover="Final conclusion.", onscreen_text="3"),
        ]
    )
    extracted = temp_voice_service.extract_voiceover_text(script)
    assert extracted == "First sentence. Second paragraph. Final conclusion."


# 6. Unique filename generation and audio file creation
def test_06_unique_filename_and_file_creation(temp_voice_service):
    script = VideoScript(
        brand="jaguartransit",
        scenes=[VideoScene(scene_number=1, visual_description="Port", voiceover="Port transit security.", onscreen_text="Security")]
    )
    res1 = temp_voice_service.synthesize_from_script(script)
    res2 = temp_voice_service.synthesize_from_script(script)

    assert res1.audio_filename != res2.audio_filename
    assert res1.audio_filename.startswith("jaguartransit_vo_")
    assert res1.audio_filename.endswith(".mp3")

    file1 = temp_voice_service.media_root / res1.audio_filename
    file2 = temp_voice_service.media_root / res2.audio_filename
    assert file1.exists()
    assert file2.exists()
    assert file1.stat().st_size > 0


# 7. Returned audio URL format
def test_07_returned_audio_url_format(temp_voice_service):
    script = VideoScript(
        brand="jade",
        scenes=[VideoScene(scene_number=1, visual_description="Ring", voiceover="Rare diamonds.", onscreen_text="Jewel")]
    )
    res = temp_voice_service.synthesize_from_script(script)
    assert res.audio_url == f"/media/voiceovers/{res.audio_filename}"
    assert res.status == "generated"
    assert res.provider == "mock_gtts"
    assert res.scene_count == 1


# 8. API Validation & Generation endpoint (using mocked provider)
def test_08_api_content_voice_endpoint(monkeypatch):
    from app.services.voice_service import voice_service

    # Monkeypatch the singleton provider with mock provider
    monkeypatch.setattr(voice_service, "provider", MockTTSProvider())

    payload = {
        "brand": "jade",
        "language": "en",
        "title": "Bespoke Jewellery Script",
        "scenes": [
            {
                "scene_number": 1,
                "visual_description": "Emerald necklace",
                "voiceover": "Every rare jewel carries legacy and memory.",
                "onscreen_text": "Legacy Protected"
            }
        ]
    }
    response = client.post("/api/v1/content/voice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert data["audio_url"].startswith("/media/voiceovers/")
    assert data["audio_filename"].endswith(".mp3")
    assert data["language"] == "en"

    # Verify static file serving
    get_res = client.get(data["audio_url"])
    assert get_res.status_code == 200
    assert "audio" in get_res.headers.get("content-type", "")


# 9. API Error handling on empty voiceover
def test_09_api_empty_voiceover_error():
    payload = {
        "brand": "jade",
        "scenes": [
            {"scene_number": 1, "visual_description": "No text", "voiceover": "", "onscreen_text": ""}
        ]
    }
    response = client.post("/api/v1/content/voice", json=payload)
    assert response.status_code == 400
    assert "empty voiceover" in response.json()["detail"].lower()


# 10. API Error handling on unsupported language
def test_10_api_unsupported_language_error():
    payload = {
        "brand": "jade",
        "language": "latin",
        "scenes": [
            {"scene_number": 1, "visual_description": "Necklace", "voiceover": "Carpe diem.", "onscreen_text": "Latin"}
        ]
    }
    response = client.post("/api/v1/content/voice", json=payload)
    assert response.status_code == 400
    assert "unsupported language code" in response.json()["detail"].lower()


# 11. Existing /content/video endpoint still works
def test_11_existing_video_endpoint_unaffected():
    payload = {
        "brand": "doctorshield",
        "topic": "Telehealth Medico-Legal Risk",
        "target_duration": 45,
        "platform": "reel",
        "language": "en"
    }
    response = client.post("/api/v1/content/video", json=payload)
    assert response.status_code == 200
    script = response.json()
    assert "scenes" in script
    assert len(script["scenes"]) >= 3
    assert script["media_status"] == "ai_storyboard_generated"
