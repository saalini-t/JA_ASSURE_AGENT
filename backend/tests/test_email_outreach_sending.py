"""
Email outreach sending (Phase 17A). The send endpoint is the ONLY path from a
LeadOutreach draft to an actual email -- must reject anything not status=="approved",
must never fabricate a recipient, and must never mark send_status="sent" without a
real provider call succeeding. EMAIL_PROVIDER=mock (the default) never touches a
real network -- no credentials required to run these tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.email_provider import MockEmailProvider, SMTPProvider, EmailSendError, get_email_provider

client = TestClient(app)


def _create_lead_with_email(**overrides) -> dict:
    payload = {
        "name": "Test Contact", "company": "Send Test Co", "industry": "Jewellery",
        "location": "Singapore", "recommended_brand": "jade", "email": "verified-contact@example.test",
    }
    payload.update(overrides)
    res = client.post("/api/v1/leads", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def _generate_and_approve_outreach(lead_id: int) -> dict:
    res = client.post(f"/api/v1/leads/{lead_id}/outreach/generate")
    assert res.status_code == 201, res.text
    outreach = res.json()
    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/approve")
    assert res.status_code == 200, res.text
    return res.json()


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_PROVIDER", "mock")
    assert isinstance(get_email_provider(), MockEmailProvider)


def test_smtp_selected_when_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_PROVIDER", "smtp")
    assert isinstance(get_email_provider(), SMTPProvider)


@pytest.mark.anyio
async def test_mock_provider_never_touches_network_and_reports_sent():
    provider = MockEmailProvider()
    result = await provider.send("someone@example.test", "Subject", "Body")
    assert result["status"] == "sent"
    assert result["provider"] == "mock"
    assert "message_id" in result


@pytest.mark.anyio
async def test_smtp_provider_without_config_raises_explicit_error(monkeypatch):
    monkeypatch.setattr("app.config.settings.SMTP_HOST", "")
    monkeypatch.setattr("app.config.settings.EMAIL_FROM", "")
    provider = SMTPProvider()
    with pytest.raises(EmailSendError, match="SMTP_HOST and EMAIL_FROM"):
        await provider.send("someone@example.test", "Subject", "Body")


def test_send_rejects_unapproved_outreach():
    lead = _create_lead_with_email(company="Unapproved Send Co")
    res = client.post(f"/api/v1/leads/{lead['id']}/outreach/generate")
    outreach = res.json()  # left at human_review, never approved

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/send")
    assert res.status_code == 400
    assert "approved" in res.json()["detail"].lower()


def test_send_rejects_rejected_outreach():
    lead = _create_lead_with_email(company="Rejected Send Co")
    res = client.post(f"/api/v1/leads/{lead['id']}/outreach/generate")
    outreach = res.json()
    client.post(f"/api/v1/leads/outreach/{outreach['id']}/reject", json={"reason_tag": "x", "notes": "x"})

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/send")
    assert res.status_code == 400


def test_send_succeeds_with_mock_provider_for_approved_outreach(monkeypatch):
    # Forced explicitly rather than relying on the ambient default -- if an
    # operator's local .env has EMAIL_PROVIDER=smtp configured for a deliberate
    # live-send demo, this test must still never make a real network call.
    monkeypatch.setattr("app.config.settings.EMAIL_PROVIDER", "mock")
    lead = _create_lead_with_email(company="Approved Send Co")
    outreach = _generate_and_approve_outreach(lead["id"])

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/send")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["send_status"] == "sent"
    assert body["sent_at"] is not None
    assert body["send_error"] is None


def test_send_rejects_lead_with_no_verified_email():
    # never fabricates contact info -- Lead.email intentionally blank
    res = client.post("/api/v1/leads", json={
        "name": "No Email Contact", "company": "No Email Co", "industry": "Jewellery",
        "recommended_brand": "jade",
    })
    lead = res.json()
    assert lead["email"] is None
    outreach = _generate_and_approve_outreach(lead["id"])

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/send")
    assert res.status_code == 400
    assert "no verified email" in res.json()["detail"].lower()


def test_send_failure_is_recorded_honestly_not_as_sent(monkeypatch):
    # Same as above -- force mock so this test isn't affected by ambient .env state.
    monkeypatch.setattr("app.config.settings.EMAIL_PROVIDER", "mock")
    lead = _create_lead_with_email(company="Failing Send Co")
    outreach = _generate_and_approve_outreach(lead["id"])

    async def failing_send(self, to, subject, body):
        raise EmailSendError("simulated provider outage")

    monkeypatch.setattr(MockEmailProvider, "send", failing_send)

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/send")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["send_status"] == "failed"
    assert "simulated provider outage" in body["send_error"]


def test_send_404s_for_missing_outreach():
    res = client.post("/api/v1/leads/outreach/999999/send")
    assert res.status_code == 404


@pytest.fixture
def anyio_backend():
    return "asyncio"
