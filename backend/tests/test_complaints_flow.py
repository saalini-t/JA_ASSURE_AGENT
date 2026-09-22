import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db_ready():
    from app.database.base import Base
    from app.database.session import engine
    import app.models.entities  # registers Complaint
    Base.metadata.create_all(bind=engine)


def test_01_submit_complaint_and_auto_route():
    payload = {
        "customer_name": "Marcus Tan",
        "customer_email": "marcus.tan@example.sg",
        "customer_phone": "+65 9123 4567",
        "brand": "jade",
        "category": "claims_denial",
        "priority": "high",
        "subject": "Claim #JAD-8819 rejected without explanation",
        "description": "My bespoke diamond necklace was stolen during travel. The claim was denied immediately with no justification."
    }

    response = client.post("/api/v1/complaints/", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] > 0
    assert data["complaint_number"].startswith("CMP-")
    assert data["customer_name"] == "Marcus Tan"
    assert data["brand"] == "jade"
    assert data["status"] == "pending"
    assert data["routed_to"] == "claims_desk"
    assert "claims denial" in data["routing_reason"].lower()


def test_02_auto_escalation_on_regulatory_keyword():
    payload = {
        "customer_name": "Dr. Sarah Lee",
        "customer_email": "dr.lee@medicalclinic.com",
        "brand": "doctorshield",
        "category": "compliance_misleading",
        "priority": "medium",
        "subject": "Misleading marketing brochure regarding telemedicine coverage",
        "description": "Your brochure claims full coverage for overseas telehealth consultations. If this is not resolved, I will report to the MAS regulator and health ministry."
    }

    response = client.post("/api/v1/complaints/", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["priority"] == "urgent"
    assert data["routed_to"] == "executive_escalations"
    assert "urgent regulatory" in data["routing_reason"].lower()


def test_03_route_complaint_to_specialist():
    # Submit first
    sub_res = client.post("/api/v1/complaints/", json={
        "customer_name": "Alex Wong",
        "customer_email": "alex@transitlogistics.my",
        "brand": "jaguartransit",
        "category": "policy_coverage",
        "subject": "Port delay deductible inquiry",
        "description": "Dispute on the applied deductible rate for cross-border cargo."
    })
    comp_id = sub_res.json()["id"]

    # Route to underwriting
    route_payload = {
        "routed_to": "underwriting_team",
        "routing_reason": "Complex maritime policy terms require senior underwriter review",
        "assigned_reviewer": "senior_underwriter_tan"
    }
    route_res = client.post(f"/api/v1/complaints/{comp_id}/route", json=route_payload)
    assert route_res.status_code == 200
    routed_data = route_res.json()

    assert routed_data["routed_to"] == "underwriting_team"
    assert routed_data["assigned_reviewer"] == "senior_underwriter_tan"
    assert routed_data["status"] == "under_review"
    assert routed_data["routed_at"] is not None


def test_04_action_and_resolve_complaint():
    # Submit complaint
    sub_res = client.post("/api/v1/complaints/", json={
        "customer_name": "Elena Lim",
        "customer_email": "elena.lim@singapore.com",
        "brand": "jade",
        "category": "billing_dispute",
        "subject": "Double charged annual premium",
        "description": "Two credit card charges appeared on my monthly statement."
    })
    comp_id = sub_res.json()["id"]

    # Action to resolve
    action_payload = {
        "action": "resolve",
        "resolution_notes": "Identified duplicate gateway charge. Refund of S$450 processed successfully to customer card.",
        "actioned_by": "billing_officer_chua",
        "response_draft": "Dear Ms. Lim, we have verified the duplicate billing and processed an immediate refund."
    }
    action_res = client.post(f"/api/v1/complaints/{comp_id}/action", json=action_payload)
    assert action_res.status_code == 200
    action_data = action_res.json()

    assert action_data["status"] == "resolved"
    assert action_data["resolved_at"] is not None
    assert action_data["actioned_by"] == "billing_officer_chua"
    assert "Refund of S$450" in action_data["resolution_notes"]


def test_05_list_and_filter_complaints():
    res = client.get("/api/v1/complaints/", params={"brand": "jade"})
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert all(item["brand"] == "jade" for item in items)


def test_06_complaint_metrics():
    res = client.get("/api/v1/complaints/metrics")
    assert res.status_code == 200
    metrics = res.json()

    assert "total_complaints" in metrics
    assert "pending_count" in metrics
    assert "brand_breakdown" in metrics
    assert "category_breakdown" in metrics
    assert metrics["total_complaints"] >= 3
