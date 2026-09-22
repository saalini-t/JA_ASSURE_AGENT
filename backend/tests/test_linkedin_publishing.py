"""
LinkedIn publishing tests: linkedin_client (author URN resolution, text/image/video
post creation, error classification) and publishing_service (HITL gate enforcement,
idempotency, retry/backoff for transient failures, immutable per-attempt audit trail).

No real network calls: httpx.AsyncClient.get/post/put are monkeypatched at the class
level so linkedin_client's real logic runs end-to-end against canned responses.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import ContentQueue, PublishingRecord
from app.services import linkedin_client, publishing_service
from app.services.linkedin_client import (
    LinkedInNotConfiguredError,
    LinkedInPermanentError,
    LinkedInTransientError,
)
from app.services.publishing_service import PublishingGateError, DuplicatePublishError

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _resp(status: int, json_body: dict = None, headers: dict = None) -> httpx.Response:
    return httpx.Response(status_code=status, json=json_body if json_body is not None else {}, headers=headers or {})


def _create_approved_item(**overrides) -> dict:
    payload = {
        "brand": "jade",
        "platform": "linkedin",
        "content_type": "post",
        "topic": "LinkedIn Publishing Test",
        "content_raw": "Jade offers agreed-value coverage for bespoke jewellery collections.\n\n*Terms and conditions apply.*",
        "variation": "A",
        "language": "en",
        "compliance_status": "passed",
        "compliance_score": 100.0,
    }
    payload.update(overrides)
    res = client.post("/api/v1/queue", json=payload)
    assert res.status_code == 201, res.text
    item = res.json()
    res = client.post(f"/api/v1/queue/{item['id']}/approve")
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------------------
# linkedin_client: author URN resolution
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_author_urn_resolves_via_userinfo(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")

    async def fake_get(self, url, headers=None, timeout=None):
        assert "userinfo" in url
        return _resp(200, {"sub": "member123"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async with httpx.AsyncClient() as c:
        urn = await linkedin_client.resolve_author_urn(c, "fake-token")
    assert urn == "urn:li:person:member123"


@pytest.mark.anyio
async def test_author_urn_falls_back_to_me(monkeypatch):
    async def fake_get(self, url, headers=None, timeout=None):
        if "userinfo" in url:
            return _resp(403, {"error": "insufficient_scope"})
        return _resp(200, {"id": "member456"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async with httpx.AsyncClient() as c:
        urn = await linkedin_client.resolve_author_urn(c, "fake-token")
    assert urn == "urn:li:person:member456"


@pytest.mark.anyio
async def test_author_urn_falls_back_to_organization(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ORGANIZATION_ID", "https://www.linkedin.com/company/98765/")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(403, {"error": "insufficient_scope"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async with httpx.AsyncClient() as c:
        urn = await linkedin_client.resolve_author_urn(c, "fake-token")
    assert urn == "urn:li:organization:98765"


@pytest.mark.anyio
async def test_author_urn_raises_permanent_when_nothing_resolves(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ORGANIZATION_ID", "")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(403, {"error": "insufficient_scope"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(LinkedInPermanentError):
        async with httpx.AsyncClient() as c:
            await linkedin_client.resolve_author_urn(c, "fake-token")


# ---------------------------------------------------------------------------
# linkedin_client: text / image / video publishing
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_publish_text_success(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setattr("app.config.settings.LINKEDIN_ORGANIZATION_ID", "")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        assert "ugcPosts" in url
        assert json["author"] == "urn:li:person:abc123"
        content = json["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert content["shareMediaCategory"] == "NONE"
        assert content["shareCommentary"]["text"] == "Hello LinkedIn"
        return _resp(201, {"id": "urn:li:share:999"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await linkedin_client.publish_text("Hello LinkedIn")
    assert result["external_post_id"] == "urn:li:share:999"


@pytest.mark.anyio
async def test_publish_text_without_token_raises_not_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "")
    with pytest.raises(LinkedInNotConfiguredError):
        await linkedin_client.publish_text("Hello LinkedIn")


@pytest.mark.anyio
async def test_publish_image_registers_uploads_and_posts(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")
    image_path = tmp_path / "scene.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes")

    calls = {"put_url": None}

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        if "registerUpload" in url:
            return _resp(200, {"value": {
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://upload.example/image-slot"
                    }
                },
                "asset": "urn:li:digitalmediaAsset:IMG1",
            }})
        assert "ugcPosts" in url
        content = json["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert content["shareMediaCategory"] == "IMAGE"
        assert content["media"] == [{"status": "READY", "media": "urn:li:digitalmediaAsset:IMG1"}]
        return _resp(201, {"id": "urn:li:share:img1"})

    async def fake_put(self, url, headers=None, content=None, timeout=None):
        calls["put_url"] = url
        assert content == image_path.read_bytes()
        return _resp(201, {})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "put", fake_put)

    result = await linkedin_client.publish_image("Check out this ring", image_path)
    assert result["external_post_id"] == "urn:li:share:img1"
    assert result["asset_urn"] == "urn:li:digitalmediaAsset:IMG1"
    assert calls["put_url"] == "https://upload.example/image-slot"


@pytest.mark.anyio
async def test_publish_video_registers_uploads_and_posts(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fakemp4bytes")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        if "registerUpload" in url:
            return _resp(200, {"value": {
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://upload.example/video-slot"
                    }
                },
                "asset": "urn:li:digitalmediaAsset:VID1",
            }})
        content = json["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert content["shareMediaCategory"] == "VIDEO"
        return _resp(201, {"id": "urn:li:share:vid1"})

    async def fake_put(self, url, headers=None, content=None, timeout=None):
        return _resp(201, {})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "put", fake_put)

    result = await linkedin_client.publish_video("Watch our new reel", video_path)
    assert result["external_post_id"] == "urn:li:share:vid1"


@pytest.mark.anyio
async def test_publish_image_missing_file_is_permanent_error(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")
    with pytest.raises(LinkedInPermanentError, match="not found"):
        await linkedin_client.publish_image("text", tmp_path / "missing.png")


@pytest.mark.anyio
async def test_error_classification_401_is_permanent(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        return _resp(401, {"error": "invalid_token"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LinkedInPermanentError):
        await linkedin_client.publish_text("hello")


@pytest.mark.anyio
async def test_error_classification_503_is_transient(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        return _resp(503, {"error": "service_unavailable"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LinkedInTransientError):
        await linkedin_client.publish_text("hello")


@pytest.mark.anyio
async def test_error_classification_429_is_transient(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")

    async def fake_get(self, url, headers=None, timeout=None):
        return _resp(200, {"sub": "abc123"})

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        return _resp(429, {"error": "rate_limited"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LinkedInTransientError):
        await linkedin_client.publish_text("hello")


# ---------------------------------------------------------------------------
# publishing_service: HITL gate, idempotency, retries, audit trail
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_service_rejects_pending_content():
    db = SessionLocal()
    try:
        res = client.post("/api/v1/queue", json={
            "brand": "jade", "platform": "linkedin", "content_type": "post",
            "topic": "Gate test", "content_raw": "text", "variation": "A", "language": "en",
            "compliance_status": "passed", "compliance_score": 100.0,
        })
        item = res.json()  # created as status="pending" (server-clamped)

        with pytest.raises(PublishingGateError):
            await publishing_service.publish_to_linkedin(db, item["id"])
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_rejects_compliance_not_passed():
    db = SessionLocal()
    try:
        res = client.post("/api/v1/queue", json={
            "brand": "jade", "platform": "linkedin", "content_type": "post",
            "topic": "Gate test 2", "content_raw": "text", "variation": "A", "language": "en",
            "compliance_status": "flagged", "compliance_score": 40.0,
        })
        item = res.json()
        client.post(f"/api/v1/queue/{item['id']}/approve")  # approve won't fix compliance_status

        with pytest.raises(PublishingGateError):
            await publishing_service.publish_to_linkedin(db, item["id"])
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_publishes_approved_passed_content(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "fake-token")

    async def fake_publish_text(text):
        return {"external_post_id": "urn:li:share:svc1"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    item = _create_approved_item(topic="Service success test")
    db = SessionLocal()
    try:
        record = await publishing_service.publish_to_linkedin(db, item["id"])
        assert record.status == "published"
        assert record.external_post_id == "urn:li:share:svc1"
        assert record.attempt == 1

        content = db.get(ContentQueue, item["id"])
        assert content.status == "published"
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_idempotency_blocks_second_publish(monkeypatch):
    async def fake_publish_text(text):
        return {"external_post_id": "urn:li:share:once"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    item = _create_approved_item(topic="Idempotency test")
    db = SessionLocal()
    try:
        first = await publishing_service.publish_to_linkedin(db, item["id"])
        assert first.status == "published"

        with pytest.raises(DuplicatePublishError):
            await publishing_service.publish_to_linkedin(db, item["id"])
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_retries_transient_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    async def flaky_publish_text(text):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise LinkedInTransientError("simulated network blip")
        return {"external_post_id": "urn:li:share:retry-ok"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", flaky_publish_text)

    item = _create_approved_item(topic="Retry success test")
    db = SessionLocal()
    try:
        record = await publishing_service.publish_to_linkedin(db, item["id"], backoff_seconds=0.01)
        assert record.status == "published"
        assert record.attempt == 2
        assert attempts["n"] == 2

        # one immutable row per attempt, not a single overwritten row
        all_records = db.query(PublishingRecord).filter_by(content_id=item["id"]).order_by(PublishingRecord.attempt).all()
        assert len(all_records) == 2
        assert all_records[0].status == "failed"
        assert all_records[1].status == "published"
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_exhausts_retries_on_persistent_transient_failure(monkeypatch):
    async def always_flaky(text):
        raise LinkedInTransientError("simulated persistent outage")

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", always_flaky)

    item = _create_approved_item(topic="Retry exhaustion test")
    db = SessionLocal()
    try:
        record = await publishing_service.publish_to_linkedin(db, item["id"], max_attempts=3, backoff_seconds=0.01)
        assert record.status == "failed"
        assert record.attempt == 3

        all_records = db.query(PublishingRecord).filter_by(content_id=item["id"]).all()
        assert len(all_records) == 3
        assert all(r.status == "failed" for r in all_records)

        # never marked published in the DB despite exhausting retries
        content = db.get(ContentQueue, item["id"])
        assert content.status == "approved"
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_does_not_retry_permanent_failure(monkeypatch):
    calls = {"n": 0}

    async def permanent_failure(text):
        calls["n"] += 1
        raise LinkedInPermanentError("invalid token")

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", permanent_failure)

    item = _create_approved_item(topic="Permanent failure test")
    db = SessionLocal()
    try:
        record = await publishing_service.publish_to_linkedin(db, item["id"], backoff_seconds=0.01)
        assert record.status == "failed"
        assert "permanent" in record.error_info
        assert calls["n"] == 1  # never retried

        all_records = db.query(PublishingRecord).filter_by(content_id=item["id"]).all()
        assert len(all_records) == 1
    finally:
        db.close()


@pytest.mark.anyio
async def test_service_not_configured_fails_without_retry(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "")

    item = _create_approved_item(topic="Not configured test")
    db = SessionLocal()
    try:
        record = await publishing_service.publish_to_linkedin(db, item["id"], backoff_seconds=0.01)
        assert record.status == "failed"
        assert "not configured" in record.error_info.lower()

        all_records = db.query(PublishingRecord).filter_by(content_id=item["id"]).all()
        assert len(all_records) == 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# API route: POST /api/v1/publishing/{content_id}/linkedin
# ---------------------------------------------------------------------------

def test_api_rejects_unapproved_content():
    res = client.post("/api/v1/queue", json={
        "brand": "jade", "platform": "linkedin", "content_type": "post",
        "topic": "API gate test", "content_raw": "text", "variation": "A", "language": "en",
        "compliance_status": "passed", "compliance_score": 100.0,
    })
    item = res.json()  # still "pending", never approved
    res = client.post(f"/api/v1/publishing/{item['id']}/linkedin")
    assert res.status_code == 400


def test_api_404_for_missing_content():
    res = client.post("/api/v1/publishing/999999/linkedin")
    assert res.status_code == 404


def test_api_publishes_and_blocks_duplicate(monkeypatch):
    async def fake_publish_text(text):
        return {"external_post_id": "urn:li:share:api1"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    item = _create_approved_item(topic="API success test")

    res = client.post(f"/api/v1/publishing/{item['id']}/linkedin")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "published"
    assert body["external_post_id"] == "urn:li:share:api1"

    dup_res = client.post(f"/api/v1/publishing/{item['id']}/linkedin")
    assert dup_res.status_code == 409
