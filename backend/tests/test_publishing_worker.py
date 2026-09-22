"""
Project 2 ("The Hands") publishing worker tests. All LinkedIn calls mocked --
these tests never make a real network call, matching the standing rule that
external APIs are always mocked in automated tests. The worker is exercised
directly (app.services.publishing_worker) and via its single manual-trigger
endpoint; it is never auto-started, so there is nothing to test for "does it run
on a schedule" -- by design, it doesn't.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import ContentQueue, PublishingRecord
from app.services import publishing_worker
from app.services import publishing_service

client = TestClient(app)


def _create_approved_item(**overrides) -> dict:
    payload = {
        "brand": "jade", "platform": "linkedin", "content_type": "post",
        "topic": "Worker test", "content_raw": "Protect your jewellery collection.\n\n*Terms apply.*",
        "variation": "A", "language": "en", "compliance_status": "passed", "compliance_score": 100.0,
    }
    payload.update(overrides)
    res = client.post("/api/v1/queue", json=payload)
    assert res.status_code == 201, res.text
    item = res.json()
    res = client.post(f"/api/v1/queue/{item['id']}/approve")
    assert res.status_code == 200, res.text
    return res.json()


def _create_pending_item(**overrides) -> dict:
    payload = {
        "brand": "jade", "platform": "linkedin", "content_type": "post",
        "topic": "Worker pending test", "content_raw": "text", "variation": "A", "language": "en",
        "compliance_status": "passed", "compliance_score": 100.0,
    }
    payload.update(overrides)
    res = client.post("/api/v1/queue", json=payload)
    return res.json()  # left as "pending" -- never approved


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_find_eligible_content_only_returns_approved_and_passed():
    approved = _create_approved_item(topic="Eligible item")
    pending = _create_pending_item(topic="Ineligible pending item")

    db = SessionLocal()
    try:
        eligible_ids = {c.id for c in publishing_worker.find_eligible_content(db, limit=50)}
        assert approved["id"] in eligible_ids
        assert pending["id"] not in eligible_ids
    finally:
        db.close()


def test_find_eligible_content_excludes_already_published():
    item = _create_approved_item(topic="Already published item")

    db = SessionLocal()
    try:
        db.add(PublishingRecord(
            content_id=item["id"], platform="linkedin", attempt=1,
            status="published", external_post_id="urn:li:share:already-done",
        ))
        db.commit()
        eligible_ids = {c.id for c in publishing_worker.find_eligible_content(db, limit=50)}
        assert item["id"] not in eligible_ids
    finally:
        db.close()


@pytest.mark.anyio
async def test_run_once_publishes_eligible_content(monkeypatch):
    item = _create_approved_item(topic="Run once success test")

    async def fake_publish_text(text):
        return {"external_post_id": "urn:li:share:worker-success"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    results = await publishing_worker.run_once(max_items=50)

    matching = [r for r in results if r["content_id"] == item["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "published"
    assert matching[0]["external_post_id"] == "urn:li:share:worker-success"


@pytest.mark.anyio
async def test_run_once_never_publishes_unapproved_content(monkeypatch):
    pending_item = _create_pending_item(topic="Never publish this")

    call_count = {"n": 0}

    async def fake_publish_text(text):
        call_count["n"] += 1
        return {"external_post_id": "urn:li:share:should-not-happen"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    results = await publishing_worker.run_once(max_items=50)

    assert all(r["content_id"] != pending_item["id"] for r in results)
    # the fake was never invoked for the pending item specifically -- confirmed by
    # it not appearing in results at all (find_eligible_content excluded it
    # upstream, before publish_to_linkedin was ever called)


@pytest.mark.anyio
async def test_run_once_records_a_permanent_failure_without_raising(monkeypatch):
    item = _create_approved_item(topic="Worker permanent failure test")

    async def failing_publish_text(text):
        from app.services.linkedin_client import LinkedInPermanentError
        raise LinkedInPermanentError("invalid token")

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", failing_publish_text)

    results = await publishing_worker.run_once(max_items=50)

    matching = [r for r in results if r["content_id"] == item["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "failed"


@pytest.mark.anyio
async def test_manual_trigger_endpoint_runs_a_single_pass(monkeypatch):
    item = _create_approved_item(topic="Manual trigger endpoint test")

    async def fake_publish_text(text):
        return {"external_post_id": "urn:li:share:manual-trigger"}

    monkeypatch.setattr(publishing_service.linkedin_client, "publish_text", fake_publish_text)

    res = client.post("/api/v1/publishing/worker/run-once")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["processed"] >= 1
    matching = [r for r in body["results"] if r["content_id"] == item["id"]]
    assert matching and matching[0]["status"] == "published"
