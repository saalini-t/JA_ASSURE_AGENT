"""
Lead outreach governance: structured drafts (subject/body/personalization_points/
source_evidence) that must pass through compliance + the SAME HITL primitives that
guard ContentQueue before they can be approved. Fixes a real gap found during audit:
outreach previously had no compliance check and PATCH /leads/{id}/status accepted
any string directly (that endpoint is unrelated CRM status, not outreach approval --
outreach approval now lives exclusively on LeadOutreach.status, governed here).
"""
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import ReviewDecision

client = TestClient(app)


def _create_lead(**overrides) -> dict:
    payload = {
        "name": "Dato' Test Jeweller",
        "company": "Test Heritage Jewellers",
        "industry": "Luxury Goods & Haute Horlogerie",
        "location": "Kuala Lumpur, Malaysia",
        "company_size": "20-50 staff",
        "recommended_brand": "jade",
        "fit_score": 82.0,
        "qualification_reason": "High-value gemstone inventory with regional exhibition travel exposure.",
        "source": "prospecting",
    }
    payload.update(overrides)
    res = client.post("/api/v1/leads", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def _generate_outreach(lead_id: int) -> dict:
    res = client.post(f"/api/v1/leads/{lead_id}/outreach/generate")
    assert res.status_code == 201, res.text
    return res.json()


def test_lead_create_no_longer_crashes_on_source_type():
    # Regression test for a real pre-existing bug found during Phase C audit:
    # LeadCreate used to include the read-only `source_type` property, which has
    # no setter on the SQLAlchemy model and crashed the constructor.
    lead = _create_lead()
    assert lead["id"] > 0
    assert lead["source_type"] in ("VERIFIED_SOURCE", "AI_GENERATED_PROSPECT", "DEMO_DATA")


def test_generate_outreach_produces_structured_draft_and_enters_human_review():
    lead = _create_lead()
    outreach = _generate_outreach(lead["id"])

    assert outreach["lead_id"] == lead["id"]
    assert outreach["product"] == "jade"
    assert outreach["subject"]
    assert "Test Heritage Jewellers" in outreach["subject"]
    assert outreach["body"]
    assert outreach["original_body"] == outreach["body"]
    assert any("Industry" in p for p in outreach["personalization_points"])
    assert any("Location" in p for p in outreach["personalization_points"])
    assert len(outreach["source_evidence"]) > 0
    # brand's standard template is conservative -- should pass compliance cleanly
    assert outreach["compliance_status"] == "passed"
    assert outreach["status"] == "human_review"


def test_outreach_is_never_auto_approved():
    lead = _create_lead(company="Never Auto Approved Co")
    outreach = _generate_outreach(lead["id"])
    assert outreach["status"] != "approved"


def test_approve_from_human_review_succeeds_and_is_logged():
    lead = _create_lead(company="Approve Flow Co")
    outreach = _generate_outreach(lead["id"])

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/approve")
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "approved"

    db = SessionLocal()
    try:
        decisions = db.query(ReviewDecision).filter(
            ReviewDecision.asset_type == "lead_outreach", ReviewDecision.asset_id == outreach["id"]
        ).all()
        assert len(decisions) == 1
        assert decisions[0].decision == "approve"
        assert decisions[0].previous_status == "human_review"
        assert decisions[0].new_status == "approved"
    finally:
        db.close()


def test_cannot_approve_an_already_approved_outreach():
    lead = _create_lead(company="Double Approve Co")
    outreach = _generate_outreach(lead["id"])
    client.post(f"/api/v1/leads/outreach/{outreach['id']}/approve")

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/approve")
    assert res.status_code == 409


def test_reject_records_reason_and_notes():
    lead = _create_lead(company="Reject Flow Co")
    outreach = _generate_outreach(lead["id"])

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/reject", json={
        "reason_tag": "tone_too_salesy", "notes": "Too pushy for a first-touch email.",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "rejected"
    assert body["reason_tag"] == "tone_too_salesy"


def test_rejected_outreach_cannot_be_approved():
    lead = _create_lead(company="Reject Then Approve Co")
    outreach = _generate_outreach(lead["id"])
    client.post(f"/api/v1/leads/outreach/{outreach['id']}/reject", json={
        "reason_tag": "x", "notes": "x",
    })

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/approve")
    assert res.status_code == 409


def test_edit_preserves_original_body_and_returns_to_human_review():
    lead = _create_lead(company="Edit Flow Co")
    outreach = _generate_outreach(lead["id"])
    original_body = outreach["body"]

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/edit", json={
        "edited_body": "A shorter, more concise version of the outreach email.",
        "edited_subject": "A revised subject line",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "human_review"  # never auto-approved after an edit
    assert body["original_body"] == original_body
    assert body["body"] == "A shorter, more concise version of the outreach email."
    assert body["subject"] == "A revised subject line"


def test_edit_rechecks_compliance_and_flags_noncompliant_text():
    lead = _create_lead(company="Noncompliant Edit Co")
    outreach = _generate_outreach(lead["id"])
    assert outreach["compliance_status"] == "passed"

    res = client.post(f"/api/v1/leads/outreach/{outreach['id']}/edit", json={
        "edited_body": "We offer a 100% guaranteed payout with zero risk, no exceptions ever.",
    })
    assert res.status_code == 200, res.text
    assert res.json()["compliance_status"] == "flagged"


def test_404_for_missing_lead_on_generate():
    res = client.post("/api/v1/leads/999999/outreach/generate")
    assert res.status_code == 404


def test_404_for_missing_outreach_on_approve():
    res = client.post("/api/v1/leads/outreach/999999/approve")
    assert res.status_code == 404


def test_list_outreach_history_for_a_lead():
    lead = _create_lead(company="History List Co")
    _generate_outreach(lead["id"])
    _generate_outreach(lead["id"])

    res = client.get(f"/api/v1/leads/{lead['id']}/outreach")
    assert res.status_code == 200
    assert len(res.json()) == 2
