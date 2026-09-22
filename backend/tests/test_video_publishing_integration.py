"""
Media-to-publishing wiring (Phase E): closes the previously-real gap where a
rendered video had no path into ContentQueue, so LinkedIn video publishing had
nothing to actually publish. Covers POST /content/video/enqueue, and proves the
full chain end to end: render -> enqueue -> compliance -> human_review -> approve
-> LinkedIn video publish (mocked) actually receives the real video file path.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import ContentQueue
from app.schemas.agent_contracts import VideoScript
from app.services import video_generation_service as vgs
from app.services.video_generation_service import generate_video_mvp
from app.services.ffmpeg_locator import resolve_ffmpeg
from app.services import publishing_service
from tests.test_video_generation import _make_scene, _make_script

client = TestClient(app)


def _binary_available(resolver) -> bool:
    try:
        resolver()
        return True
    except Exception:
        return False


FFMPEG_AVAILABLE = _binary_available(resolve_ffmpeg)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _render_and_build_script(tmp_path, monkeypatch, job_id: str, **script_overrides) -> VideoScript:
    """Renders a real (silent, branded-fallback) video and builds the exact
    VideoScript object POST /content/video would return -- mirrors content.py's
    own render_result -> script field mapping precisely."""
    monkeypatch.setattr("app.config.settings.IMAGE_PROVIDER", "branded_fallback")
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)

    script = _make_script(scenes=[_make_scene(scene_number=1), _make_scene(scene_number=2)], **script_overrides)
    result = await generate_video_mvp(script, job_id=job_id, narrate=False)
    assert result.success is True, result.error_message

    script.job_id = result.job_id
    script.video_url = result.video_url
    script.video_duration_seconds = result.duration_seconds
    script.scenes_generated = result.scenes_generated
    script.image_source = result.image_source_summary
    script.render_status = "completed"
    script.has_audio = result.has_audio
    script.has_captions = result.has_captions
    script.scene_image_sources = [
        {
            "scene_number": r.scene_number, "source": r.source, "is_real_ai": r.is_real_ai,
            "provider": r.provider, "model": r.model, "provider_error": r.provider_error,
        }
        for r in result.scene_image_reports
    ]
    script.ai_generated_scene_count = result.ai_generated_scene_count
    script.fallback_scene_count = result.fallback_scene_count
    return script


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_enqueue_creates_content_queue_row_with_real_video_path(tmp_path, monkeypatch):
    script = await _render_and_build_script(tmp_path, monkeypatch, "enqueue-test-1")

    res = client.post("/api/v1/content/video/enqueue", json=script.model_dump())
    assert res.status_code == 201, res.text
    item = res.json()

    assert item["content_type"] == "reel"
    assert item["platform"] == "linkedin"
    assert item["status"] in ("human_review", "pending")

    meta = json.loads(item["metadata_json"])
    assert meta["video_path"] == str(tmp_path / "enqueue-test-1" / "final.mp4")
    assert (tmp_path / "enqueue-test-1" / "final.mp4").exists()
    assert meta["ai_generated_scene_count"] == 0  # branded fallback, honestly reported
    assert meta["fallback_scene_count"] == 2


@pytest.mark.anyio
async def test_enqueue_rejects_unrendered_script():
    script = _make_script()
    script.render_status = "failed"
    script.job_id = "never-rendered"

    res = client.post("/api/v1/content/video/enqueue", json=script.model_dump())
    assert res.status_code == 400
    assert "render" in res.json()["detail"].lower()


@pytest.mark.anyio
async def test_enqueue_rejects_missing_video_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vgs, "MEDIA_ROOT", tmp_path)
    script = _make_script()
    script.render_status = "completed"
    script.job_id = "no-such-job-dir"

    res = client.post("/api/v1/content/video/enqueue", json=script.model_dump())
    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_enqueue_runs_real_compliance_not_auto_approved(tmp_path, monkeypatch):
    script = await _render_and_build_script(tmp_path, monkeypatch, "enqueue-test-2")

    res = client.post("/api/v1/content/video/enqueue", json=script.model_dump())
    assert res.status_code == 201, res.text
    item = res.json()

    assert item["status"] not in ("approved", "published", "scheduled")
    assert item["compliance_status"] in ("passed", "flagged")
    assert item["compliance_score"] >= 0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed on this machine")
@pytest.mark.anyio
async def test_full_chain_render_enqueue_approve_publish_to_linkedin(tmp_path, monkeypatch):
    """
    The actual end-to-end proof this phase exists for: a real rendered MP4,
    enqueued, approved through the same HITL gate as any other content, then
    published through the REAL PublishingService/LinkedInClient wiring (only the
    network call is mocked) -- and the mocked LinkedIn call receives the genuine
    on-disk video file, not a placeholder.
    """
    script = await _render_and_build_script(
        tmp_path, monkeypatch, "enqueue-e2e-test",
        hook="Protect what matters most.", cta="Learn more today.",
        disclaimer="*Terms and conditions apply.*",
    )

    res = client.post("/api/v1/content/video/enqueue", json=script.model_dump())
    assert res.status_code == 201, res.text
    item = res.json()
    content_id = item["id"]
    assert item["compliance_status"] == "passed", item  # clean hook/cta/disclaimer text

    approve_res = client.post(f"/api/v1/queue/{content_id}/approve")
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["status"] == "approved"

    received_video_path = {}

    async def fake_publish_video(text, video_path):
        received_video_path["path"] = video_path
        return {"external_post_id": "urn:li:share:video-e2e-test"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_video", fake_publish_video)

    publish_res = client.post(f"/api/v1/publishing/{content_id}/linkedin")
    assert publish_res.status_code == 200, publish_res.text
    record = publish_res.json()
    assert record["status"] == "published"
    assert record["external_post_id"] == "urn:li:share:video-e2e-test"

    assert received_video_path["path"] == tmp_path / "enqueue-e2e-test" / "final.mp4"
    assert received_video_path["path"].exists()

    # Duplicate publish is still blocked, exactly like text/image content.
    dup_res = client.post(f"/api/v1/publishing/{content_id}/linkedin")
    assert dup_res.status_code == 409
