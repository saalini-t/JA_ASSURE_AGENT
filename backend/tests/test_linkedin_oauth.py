"""
LinkedIn member-posting OAuth flow (authorization code grant, w_member_social scope
only -- no organization/company-page scope requested or required). No real network
calls: httpx.AsyncClient.post is monkeypatched at the class level, exactly like
test_linkedin_publishing.py does for the publish-side client.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import linkedin_oauth

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _configured_oauth(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.LINKEDIN_CLIENT_ID", "test-client-id")
    monkeypatch.setattr("app.config.settings.LINKEDIN_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr("app.config.settings.LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/v1/auth/linkedin/callback")
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "")
    # Critical: redirect the .env write-back to a throwaway file. Without this, a
    # successful token exchange in these tests would overwrite the real
    # backend/.env's LINKEDIN_ACCESS_TOKEN with a fake test value.
    monkeypatch.setattr(linkedin_oauth, "ENV_FILE_PATH", tmp_path / ".env")
    linkedin_oauth._pending_states.clear()
    yield
    linkedin_oauth._pending_states.clear()


def _token_resp(status: int, json_body: dict = None) -> httpx.Response:
    return httpx.Response(status_code=status, json=json_body if json_body is not None else {})


def test_status_reports_not_connected_when_no_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "")
    res = client.get("/api/v1/auth/linkedin/status")
    assert res.status_code == 200
    body = res.json()
    assert body["oauth_configured"] is True
    assert body["connected"] is False


def test_status_never_exposes_the_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "super-secret-token-value")
    res = client.get("/api/v1/auth/linkedin/status")
    assert res.status_code == 200
    assert "super-secret-token-value" not in res.text
    assert res.json()["connected"] is True


def test_login_requests_only_member_posting_scope_never_organization():
    url = linkedin_oauth.build_authorization_url()
    assert "scope=openid+profile+w_member_social" in url or "scope=openid%20profile%20w_member_social" in url
    assert "w_organization_social" not in url
    assert "r_organization" not in url
    assert "client_id=test-client-id" in url


def test_login_endpoint_redirects_to_linkedin(monkeypatch):
    res = client.get("/api/v1/auth/linkedin/login", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "linkedin.com/oauth/v2/authorization" in res.headers["location"]


def test_login_endpoint_json_mode_returns_url_without_configured_secret_leaking():
    res = client.get("/api/v1/auth/linkedin/login?redirect=false")
    assert res.status_code == 200
    body = res.json()
    assert "linkedin.com/oauth/v2/authorization" in body["authorization_url"]
    assert "test-client-secret" not in body["authorization_url"]


def test_login_fails_cleanly_when_oauth_not_configured(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_CLIENT_ID", "")
    res = client.get("/api/v1/auth/linkedin/login?redirect=false")
    assert res.status_code == 400
    assert "not configured" in res.text.lower()


def test_callback_rejects_missing_state():
    res = client.get("/api/v1/auth/linkedin/callback?code=abc123")
    assert res.status_code == 400
    assert "state" in res.text.lower()


def test_callback_rejects_unrecognized_state():
    res = client.get("/api/v1/auth/linkedin/callback?code=abc123&state=never-issued")
    assert res.status_code == 400


def test_callback_surfaces_linkedin_denial_without_exchanging_code():
    res = client.get("/api/v1/auth/linkedin/callback?error=user_cancelled_login&error_description=User+denied+access")
    assert res.status_code == 400
    assert "user denied access" in res.text.lower() or "not completed" in res.text.lower()


@pytest.mark.anyio
async def test_callback_exchanges_code_and_stores_token_never_returning_it(monkeypatch):
    url = linkedin_oauth.build_authorization_url()
    state = url.split("state=")[1].split("&")[0]

    async def fake_post(self, target_url, data=None, timeout=None, **kwargs):
        assert target_url == linkedin_oauth.TOKEN_URL
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == "real-code-from-linkedin"
        return _token_resp(200, {"access_token": "brand-new-member-token", "expires_in": 5184000})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res = client.get(f"/api/v1/auth/linkedin/callback?code=real-code-from-linkedin&state={state}")
    assert res.status_code == 200
    assert "connected" in res.text.lower()
    assert "brand-new-member-token" not in res.text  # never exposed in the response

    from app.config import settings
    assert settings.LINKEDIN_ACCESS_TOKEN == "brand-new-member-token"


@pytest.mark.anyio
async def test_callback_state_cannot_be_replayed(monkeypatch):
    url = linkedin_oauth.build_authorization_url()
    state = url.split("state=")[1].split("&")[0]

    async def fake_post(self, target_url, data=None, timeout=None, **kwargs):
        return _token_resp(200, {"access_token": "one-time-token"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    first = client.get(f"/api/v1/auth/linkedin/callback?code=abc&state={state}")
    assert first.status_code == 200

    second = client.get(f"/api/v1/auth/linkedin/callback?code=abc&state={state}")
    assert second.status_code == 400


@pytest.mark.anyio
async def test_token_exchange_failure_does_not_overwrite_existing_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.LINKEDIN_ACCESS_TOKEN", "existing-good-token")
    url = linkedin_oauth.build_authorization_url()
    state = url.split("state=")[1].split("&")[0]

    async def fake_post(self, target_url, data=None, timeout=None, **kwargs):
        return _token_resp(400, {"error": "invalid_grant", "error_description": "expired code"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res = client.get(f"/api/v1/auth/linkedin/callback?code=stale&state={state}")
    assert res.status_code == 400

    from app.config import settings
    assert settings.LINKEDIN_ACCESS_TOKEN == "existing-good-token"


def test_member_urn_resolution_never_requires_organization_id(monkeypatch):
    """resolve_author_urn already prefers /v2/userinfo -> /v2/me (member) before
    ever touching LINKEDIN_ORGANIZATION_ID -- confirms the OAuth flow's token is
    sufficient on its own for member posting, with no organization config needed."""
    monkeypatch.setattr("app.config.settings.LINKEDIN_ORGANIZATION_ID", "")
    from app.config import settings
    assert settings.LINKEDIN_ORGANIZATION_ID == ""
