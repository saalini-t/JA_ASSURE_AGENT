"""
Real-data lead discovery (Google Places) and contact enrichment (Hunter.io +
direct-scrape fallback). No real network calls -- httpx.Client is
monkeypatched at the class level; safe_fetch_text is monkeypatched directly
for the direct-scrape tests.
"""
import httpx
import pytest

from app.services import lead_discovery_providers as ldp


def _resp(status: int, json_body=None, text: str = "") -> httpx.Response:
    return httpx.Response(status_code=status, json=json_body, text=text if json_body is None else None)


# ---------------------------------------------------------------------------
# discover_real_businesses
# ---------------------------------------------------------------------------

def test_returns_empty_list_when_no_api_key(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "")
    assert ldp.discover_real_businesses("jade", "Singapore") == []


def test_parses_real_places_response_into_candidates(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")

    def fake_post(self, url, headers=None, json=None):
        assert url == ldp.GOOGLE_PLACES_SEARCH_URL
        assert headers["X-Goog-Api-Key"] == "test-key"
        assert "textQuery" in json
        return _resp(200, {
            "places": [
                {
                    "id": "place-1",
                    "displayName": {"text": "Marina Bay Jewels"},
                    "formattedAddress": "1 Marina Bay, Singapore",
                    "nationalPhoneNumber": "+65 6123 4567",
                    "websiteUri": "https://www.marinabayjewels.example.sg/home",
                    "rating": 4.7,
                    "userRatingCount": 132,
                    "editorialSummary": {"text": "Fine jewellery boutique."},
                },
            ]
        })

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    results = ldp.discover_real_businesses("jade", "Singapore", target_count=5)
    assert len(results) == 1
    biz = results[0]
    assert biz["company"] == "Marina Bay Jewels"
    assert biz["domain"] == "marinabayjewels.example.sg"
    assert biz["phone"] == "+65 6123 4567"
    assert biz["rating"] == 4.7


def test_deduplicates_by_place_id_across_queries(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")
    call_count = {"n": 0}

    def fake_post(self, url, headers=None, json=None):
        call_count["n"] += 1
        return _resp(200, {"places": [{"id": "same-place", "displayName": {"text": "Same Co"}}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    results = ldp.discover_real_businesses("jaguartransit", "Singapore", target_count=5)
    assert call_count["n"] >= 2  # multiple queries attempted
    assert len(results) == 1  # but deduplicated to one real business


def test_stops_early_once_target_count_reached(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")

    def fake_post(self, url, headers=None, json=None):
        return _resp(200, {"places": [
            {"id": f"p{i}", "displayName": {"text": f"Business {i}"}} for i in range(10)
        ]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    results = ldp.discover_real_businesses("doctorshield", "Singapore", target_count=3)
    assert len(results) == 3


def test_never_raises_on_http_failure(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")

    def fake_post(self, url, headers=None, json=None):
        return _resp(403, {"error": "quota exceeded"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    assert ldp.discover_real_businesses("jade", "Singapore") == []


def test_never_raises_on_network_error(monkeypatch):
    monkeypatch.setattr("app.config.settings.GOOGLE_MAPS_API_KEY", "test-key")

    def fake_post(self, url, headers=None, json=None):
        raise httpx.ConnectError("network unreachable")

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    assert ldp.discover_real_businesses("jade", "Singapore") == []


# ---------------------------------------------------------------------------
# find_real_contact_email
# ---------------------------------------------------------------------------

def test_contact_lookup_returns_none_without_domain():
    assert ldp.find_real_contact_email("") is None
    assert ldp.find_real_contact_email(None) is None


def test_hunter_verified_email_is_used_when_available(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "test-hunter-key")

    def fake_get(self, url, headers=None, params=None):
        assert "hunter.io" in url
        return _resp(200, {"data": {"emails": [
            {"value": "director@realbiz.example", "first_name": "Jane", "last_name": "Tan",
             "position": "Managing Director", "confidence": 92, "verification": {"status": "valid"}},
        ]}})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    contact = ldp.find_real_contact_email("realbiz.example")
    assert contact["email"] == "director@realbiz.example"
    assert contact["source"] == "hunter_io"
    assert contact["verified"] is True


def test_falls_back_to_direct_scrape_when_hunter_unconfigured(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")
    monkeypatch.setattr(ldp, "safe_fetch_text", lambda url, max_bytes=60000: "<html>Contact: info@realbiz.example</html>")

    contact = ldp.find_real_contact_email("realbiz.example")
    assert contact["email"] == "info@realbiz.example"
    assert contact["source"] == "direct_website_scrape"
    assert contact["verified"] is True  # domain-matched


def test_falls_back_to_direct_scrape_when_hunter_finds_nothing(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "test-hunter-key")

    def fake_get(self, url, headers=None, params=None):
        return _resp(200, {"data": {"emails": []}})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    monkeypatch.setattr(ldp, "safe_fetch_text", lambda url, max_bytes=60000: "<html>sales@realbiz.example</html>")

    contact = ldp.find_real_contact_email("realbiz.example")
    assert contact["email"] == "sales@realbiz.example"


def test_returns_none_when_nothing_found_anywhere(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")
    monkeypatch.setattr(ldp, "safe_fetch_text", lambda url, max_bytes=60000: "<html>no contact info here</html>")

    assert ldp.find_real_contact_email("realbiz.example") is None


def test_never_fabricates_when_scrape_fails(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")

    def raise_error(url, max_bytes=60000):
        raise Exception("connection refused")

    monkeypatch.setattr(ldp, "safe_fetch_text", raise_error)

    assert ldp.find_real_contact_email("realbiz.example") is None


def test_noise_emails_are_filtered_out(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUNTER_API_KEY", "")
    monkeypatch.setattr(
        ldp, "safe_fetch_text",
        lambda url, max_bytes=60000: "<html>webmaster@realbiz.example noreply@realbiz.example logo.png@sentry.io</html>",
    )

    # Only genuinely usable emails should ever be considered -- noise/system
    # addresses must never be returned as "the" discovered contact.
    contact = ldp.find_real_contact_email("realbiz.example")
    assert contact is None
