"""
POST /content/campaign -- one sequential call replacing separate
/content/generate + /content/video + /content/video/enqueue calls.

Critical invariant tested repeatedly here: this must NEVER auto-approve or
auto-publish, unlike the reference project it was adapted from (which had an
explicit SYSTEM-approved auto-publish node -- deliberately not ported). Media
generation is mocked throughout -- no real GPU/network calls, no minutes-long
video renders in a test run.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import media_decision_engine as mde
from app.services.media_decision_engine import MediaDecisionResult

client = TestClient(app)


def test_campaign_without_media_creates_text_only_item():
    res = client.post("/api/v1/content/campaign", json={
        "brand": "jade", "topic": "Agreed-value coverage for bespoke rings",
        "platform": "linkedin", "include_media": False,
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["content_type"] == "post"
    assert item["status"] in ("human_review", "pending")  # never "approved"


def test_campaign_never_auto_approves_even_when_compliance_passes():
    """The single most important test in this file -- mirrors the exact gap
    found in the reference project's auto_approval_node, which this codebase
    deliberately does not replicate."""
    res = client.post("/api/v1/content/campaign", json={
        "brand": "doctorshield", "topic": "Routine indemnity renewal reminder",
        "platform": "linkedin", "include_media": False,
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["status"] != "approved"
    assert item["status"] != "published"


def test_campaign_with_video_media_sets_content_type_reel_and_video_path(monkeypatch, tmp_path):
    fake_video = tmp_path / "final.mp4"
    fake_video.write_bytes(b"fake mp4 bytes")

    async def fake_decide(brand, topic, format_type="auto", target_duration=45, platform="reel", language="en"):
        return MediaDecisionResult(
            media_type="video", media_path=fake_video, media_url="/media/generated/xyz/final.mp4",
            source="stable_diffusion_1_5", is_real_ai=True, duration_seconds=43.0,
            scenes_generated=4, ai_generated_scene_count=2, fallback_scene_count=2,
        )

    monkeypatch.setattr(mde, "decide_and_generate_media", fake_decide)

    res = client.post("/api/v1/content/campaign", json={
        "brand": "jade", "topic": "Why sub-limits fail luxury collections",
        "platform": "linkedin", "include_media": True, "media_format": "video",
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["content_type"] == "reel"
    assert item["status"] in ("human_review", "pending")

    import json
    meta = json.loads(item["metadata_json"])
    assert meta["video_path"] == str(fake_video)
    assert meta["media_type"] == "video"
    assert meta["media_is_real_ai"] is True


def test_campaign_with_image_media_keeps_content_type_and_sets_image_path(monkeypatch, tmp_path):
    fake_image = tmp_path / "creative_image.png"

    async def fake_decide(brand, topic, format_type="auto", target_duration=45, platform="reel", language="en"):
        return MediaDecisionResult(
            media_type="image", media_path=fake_image,
            media_url="/media/generated/abc/creative_image.png",
            source="branded_fallback_demo", is_real_ai=False,
        )

    monkeypatch.setattr(mde, "decide_and_generate_media", fake_decide)

    res = client.post("/api/v1/content/campaign", json={
        "brand": "jaguartransit", "topic": "Secure high-value cargo transit",
        "platform": "linkedin", "content_type": "post", "include_media": True, "media_format": "image",
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["content_type"] == "post"  # image media never forces "reel"

    import json
    meta = json.loads(item["metadata_json"])
    assert meta["image_path"] == str(fake_image)
    assert meta["media_is_real_ai"] is False


def test_campaign_survives_media_failure_and_still_creates_text_item(monkeypatch):
    async def failing_decide(brand, topic, format_type="auto", target_duration=45, platform="reel", language="en"):
        return MediaDecisionResult(
            media_type="video", media_path=None, media_url=None,
            source="none", is_real_ai=False, error="ffmpeg not found",
        )

    monkeypatch.setattr(mde, "decide_and_generate_media", failing_decide)

    res = client.post("/api/v1/content/campaign", json={
        "brand": "jade", "topic": "Test resilience", "include_media": True,
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["status"] in ("human_review", "pending")

    import json
    meta = json.loads(item["metadata_json"])
    assert meta["media_error"] == "ffmpeg not found"
    assert "video_path" not in meta


# ---------------------------------------------------------------------------
# media_decision_engine unit tests (mocked video/image generation calls)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_decide_media_auto_falls_back_to_image_when_video_fails(monkeypatch):
    from app.services import video_generation_service as vgs
    from app.schemas.agent_contracts import VideoScript

    async def fake_script(**kwargs):
        return VideoScript(brand="jade", scenes=[])

    class FakeVideoResult:
        success = False
        video_path = None
        error_message = "no scenes"

    async def fake_generate_mvp(script, **kwargs):
        return FakeVideoResult()

    monkeypatch.setattr(mde.media_service, "generate_video_script", fake_script)
    monkeypatch.setattr(mde, "generate_video_mvp", fake_generate_mvp)

    class FakeImageProvider:
        async def generate_scene_visual(self, scene, brand, path):
            from app.services.video_providers import SceneVisualResult, SOURCE_FALLBACK
            path.write_bytes(b"fake png")
            return SceneVisualResult(path=path, source=SOURCE_FALLBACK, provider="branded_fallback")

    monkeypatch.setattr(mde, "ImageMotionProvider", FakeImageProvider)

    result = await mde.decide_and_generate_media(brand="jade", topic="test", format_type="auto")
    assert result.media_type == "image"
    assert result.is_real_ai is False


@pytest.fixture
def anyio_backend():
    return "asyncio"
