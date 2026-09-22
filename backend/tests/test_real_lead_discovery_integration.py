"""
Integration test: POST /leads/discover must use the real Google Places tier
when GOOGLE_MAPS_API_KEY is configured (in preference to the Groq-invented /
demo-pool tiers), and persist the resulting Lead with source="VERIFIED_SOURCE"
and a real (or honestly absent) email -- never a fabricated one.
"""
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import lead_discovery_providers as ldp

client = TestClient(app)

_REAL_CLIENT_POST = httpx.Client.post


def _fake_places_response(self, url, *args, **kwargs):
    # TestClient itself is built on httpx.Client -- only intercept the actual
    # outbound Google Places call, and pass everything else through untouched.
    if url != ldp.GOOGLE_PLACES_SEARCH_URL:
        return _REAL_CLIENT_POST(self, url, *args, **kwargs)
    return httpx.Response(status_code=200, json={
        "places": [
            {
                "id": "real-place-1",
                "displayName": {"text": "Real Test Jewellers Pte Ltd"},
                "formattedAddress": "123 Orchard Road, Singapore",
                "nationalPhoneNumber": "+65 6555 1234",
                "websiteUri": "https://www.realtestjewellers.example",
                "rating": 4.8,
                "userRatingCount": 210,
            },
        ],
    })


def test_discover_uses_real_google_places_tier_when_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")
    monkeypatch.setattr(httpx.Client, "post", _fake_places_response)
    # No real contact found anywhere -- confirms email stays honestly None.
    monkeypatch.setattr(
        "app.services.lead_discovery_providers.safe_fetch_text",
        lambda url, max_bytes=60000: "<html>no contact here</html>",
    )

    res = client.post("/api/v1/leads/discover", json={"brand": "jade", "country": "Singapore"})
    assert res.status_code == 200
    prospects = res.json()
    assert len(prospects) == 1
    prospect = prospects[0]
    assert prospect["company"] == "Real Test Jewellers Pte Ltd"
    assert prospect["source_type"] == "VERIFIED_SOURCE"
    assert prospect["email"] is None  # never fabricated

    leads = client.get("/api/v1/leads").json()
    saved = next(l for l in leads if l["company"] == "Real Test Jewellers Pte Ltd")
    assert saved["source_type"] == "VERIFIED_SOURCE"
    assert saved["scoring_breakdown"] is not None


def test_discover_populates_real_email_when_contact_found(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")
    monkeypatch.setattr(httpx.Client, "post", _fake_places_response)
    monkeypatch.setattr(
        "app.services.lead_discovery_providers.safe_fetch_text",
        lambda url, max_bytes=60000: "<html>Contact us: sales@realtestjewellers.example</html>",
    )

    res = client.post("/api/v1/leads/discover", json={"brand": "jade", "country": "Singapore"})
    assert res.status_code == 200
    prospect = res.json()[0]
    assert prospect["email"] == "sales@realtestjewellers.example"


def test_discover_falls_through_to_existing_tiers_when_places_not_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "")

    res = client.post("/api/v1/leads/discover", json={"brand": "doctorshield"})
    assert res.status_code == 200
    prospects = res.json()
    assert len(prospects) > 0
    # Without GOOGLE_MAPS_API_KEY, nothing should claim to be a real verified
    # Google-Places-sourced business -- only the Groq/demo-pool tiers can run.
    assert all(p["source_type"] in ("AI_GENERATED_PROSPECT", "DEMO_DATA") for p in prospects)
