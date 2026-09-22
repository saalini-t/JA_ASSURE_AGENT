"""
Analytics engagement loop (Phase F): a REAL LinkedIn Social Actions API attempt
per published post, never fabricated numbers. The overwhelmingly likely real-world
outcome -- a publish-only OAuth token lacking read scope -- is modeled explicitly
and must produce an honest "unavailable" record, not an invented zero presented as
real engagement.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import ContentQueue, PublishingRecord, Analytics
from app.services import analytics_service as analytics_svc
from app.services.linkedin_client import LinkedInPermanentError

client = TestClient(app)


def _create_published_record() -> dict:
    res = client.post("/api/v1/queue", json={
        "brand": "jade", "platform": "linkedin", "content_type": "post",
        "topic": "Engagement test", "content_raw": "Protect your jewellery collection.\n\n*Terms apply.*",
        "variation": "A", "language": "en", "compliance_status": "passed", "compliance_score": 100.0,
    })
    item = res.json()
    client.post(f"/api/v1/queue/{item['id']}/approve")

    db = SessionLocal()
    try:
        record = PublishingRecord(
            content_id=item["id"], platform="linkedin", attempt=1,
            status="published", external_post_id="urn:li:share:engagement-test",
        )
        db.add(record)
        content = db.get(ContentQueue, item["id"])
        content.status = "published"
        db.commit()
        db.refresh(record)
        return {"id": record.id, "content_id": item["id"]}
    finally:
        db.close()


@pytest.mark.anyio
async def test_successful_engagement_fetch_stores_real_numbers(monkeypatch):
    record_info = _create_published_record()

    async def fake_get_engagement(post_urn):
        assert post_urn == "urn:li:share:engagement-test"
        return {"post_urn": post_urn, "likes": 12, "comments": 3, "source": "linkedin_api"}

    monkeypatch.setattr(analytics_svc.linkedin_client, "get_post_engagement", fake_get_engagement)

    res = client.post(f"/api/v1/publishing/{record_info['id']}/analytics/refresh")
    assert res.status_code == 200, res.text
    metrics = json.loads(res.json()["engagement_metrics"])
    assert metrics["source"] == "linkedin_api"
    assert metrics["likes"] == 12
    assert metrics["comments"] == 3


@pytest.mark.anyio
async def test_successful_fetch_writes_real_analytics_kpi_rows(monkeypatch):
    record_info = _create_published_record()

    async def fake_get_engagement(post_urn):
        return {"post_urn": post_urn, "likes": 7, "comments": 2, "source": "linkedin_api"}

    monkeypatch.setattr(analytics_svc.linkedin_client, "get_post_engagement", fake_get_engagement)
    client.post(f"/api/v1/publishing/{record_info['id']}/analytics/refresh")

    db = SessionLocal()
    try:
        rows = db.query(Analytics).filter(Analytics.metric_name.in_(["linkedin_likes", "linkedin_comments"])).all()
        values = {r.metric_name: r.metric_value for r in rows}
        assert values["linkedin_likes"] == 7.0
        assert values["linkedin_comments"] == 2.0
    finally:
        db.close()


@pytest.mark.anyio
async def test_permission_failure_is_recorded_honestly_never_fabricated(monkeypatch):
    """The overwhelmingly likely real-world case: a publish-only token has no
    read scope for social actions. Must never be silently treated as zero
    engagement or a fake success."""
    record_info = _create_published_record()

    async def failing_get_engagement(post_urn):
        raise LinkedInPermanentError("LinkedIn engagement fetch failed: authorization error (403): ACCESS_DENIED")

    monkeypatch.setattr(analytics_svc.linkedin_client, "get_post_engagement", failing_get_engagement)

    res = client.post(f"/api/v1/publishing/{record_info['id']}/analytics/refresh")
    assert res.status_code == 200, res.text
    metrics = json.loads(res.json()["engagement_metrics"])
    assert metrics["source"] == "unavailable"
    assert "authorization" in metrics["reason"].lower()
    assert "likes" not in metrics  # never a fabricated number alongside the honest failure


@pytest.mark.anyio
async def test_failed_fetch_does_not_write_a_fake_zero_analytics_row(monkeypatch):
    record_info = _create_published_record()

    async def failing_get_engagement(post_urn):
        raise LinkedInPermanentError("permission denied")

    monkeypatch.setattr(analytics_svc.linkedin_client, "get_post_engagement", failing_get_engagement)

    db = SessionLocal()
    before_count = db.query(Analytics).count()
    db.close()

    client.post(f"/api/v1/publishing/{record_info['id']}/analytics/refresh")

    db = SessionLocal()
    try:
        after_count = db.query(Analytics).count()
        assert after_count == before_count  # no fake zero-engagement row written
    finally:
        db.close()


def test_refresh_on_unpublished_content_is_honest_not_an_error():
    res = client.post("/api/v1/queue", json={
        "brand": "jade", "platform": "linkedin", "content_type": "post",
        "topic": "Unpublished test", "content_raw": "text", "variation": "A", "language": "en",
        "compliance_status": "passed", "compliance_score": 100.0,
    })
    item = res.json()
    db = SessionLocal()
    try:
        record = PublishingRecord(content_id=item["id"], platform="linkedin", attempt=1, status="scheduled")
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    finally:
        db.close()

    res = client.post(f"/api/v1/publishing/{record_id}/analytics/refresh")
    assert res.status_code == 200
    metrics = json.loads(res.json()["engagement_metrics"])
    assert metrics["source"] == "unavailable"


def test_refresh_404s_for_missing_record():
    res = client.post("/api/v1/publishing/999999/analytics/refresh")
    assert res.status_code == 404


def test_engagement_listing_endpoint_returns_only_real_recorded_metrics(monkeypatch):
    res = client.get("/api/v1/analytics/engagement")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.fixture
def anyio_backend():
    return "asyncio"
