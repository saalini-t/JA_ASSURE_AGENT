"""
LinkedIn OAuth 2.0 (authorization code flow) for MEMBER posting only.

Scope requested is exactly "openid profile w_member_social" -- openid+profile let
linkedin_client.resolve_author_urn() resolve the member's own URN via /v2/userinfo
(the OIDC "Sign In with LinkedIn" product), and w_member_social is what authorizes
posting to that member's own feed via /v2/ugcPosts. This never requests or requires
any organization/company-page scope -- LINKEDIN_ORGANIZATION_ID stays fully optional
and untouched, exactly as linkedin_client.py already treats it (fallback only, used
solely when member URN resolution fails and an org ID happens to be configured).

This module only produces an access token and puts it where linkedin_client.py
already looks for one (settings.LINKEDIN_ACCESS_TOKEN, plus a best-effort write-back
to backend/.env so it survives a restart). It has no opinion about HITL/compliance --
publishing_service.py is unchanged and still gates every publish exactly as before.

The access token and client secret are NEVER logged, returned in an API response, or
otherwise exposed -- only a boolean "connected" status is ever surfaced.
"""
import logging
import secrets
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger("ja_assure.linkedin_oauth")

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPE = "openid profile w_member_social"
STATE_TTL_SECONDS = 600  # CSRF state tokens expire after 10 minutes, unused

# Module-level (not a function-local computation) so tests can redirect writes to a
# throwaway temp file via monkeypatch instead of ever touching the real backend/.env.
ENV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# In-memory CSRF state store. This is a single-operator local dev tool (one backend
# process, one person authorizing their own LinkedIn account), so a process-local
# dict is deliberately simpler than a DB table or signed token for this.
_pending_states: dict[str, float] = {}


class LinkedInOAuthError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LinkedInOAuthNotConfiguredError(LinkedInOAuthError):
    """Permanent: LINKEDIN_CLIENT_ID/SECRET/REDIRECT_URI not all set."""


def _require_oauth_config() -> None:
    if not (settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET and settings.LINKEDIN_REDIRECT_URI):
        raise LinkedInOAuthNotConfiguredError(
            "LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI must all be set in "
            "backend/.env to use the in-app OAuth flow. Alternatively, paste a token you obtained "
            "externally directly into LINKEDIN_ACCESS_TOKEN."
        )


def _prune_expired_states() -> None:
    now = time.monotonic()
    expired = [s for s, created in _pending_states.items() if now - created > STATE_TTL_SECONDS]
    for s in expired:
        _pending_states.pop(s, None)


def build_authorization_url() -> str:
    """Generates a fresh CSRF state and returns the full LinkedIn authorization URL
    the operator's browser should be sent to."""
    _require_oauth_config()
    _prune_expired_states()
    state = secrets.token_urlsafe(24)
    _pending_states[state] = time.monotonic()

    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": SCOPE,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _consume_state(state: Optional[str]) -> None:
    _prune_expired_states()
    if not state or state not in _pending_states:
        raise LinkedInOAuthError(
            "Missing or unrecognized OAuth state parameter -- possible CSRF or an expired/reused "
            "login attempt. Start over at GET /api/v1/auth/linkedin/login."
        )
    _pending_states.pop(state, None)


async def exchange_code_for_token(code: str, state: Optional[str]) -> None:
    """Validates state, exchanges the authorization code for an access token, and
    stores it (in-memory + best-effort .env write-back). Raises LinkedInOAuthError
    on any failure. Never returns or logs the token itself."""
    _consume_state(state)
    _require_oauth_config()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(TOKEN_URL, data=data, timeout=15.0)
        except httpx.TransportError as e:
            raise LinkedInOAuthError(f"Could not reach LinkedIn's token endpoint: {e}")

    if resp.status_code != 200:
        # LinkedIn's error responses are small JSON objects with no secrets in them
        # (error/error_description) -- safe to include in the exception message.
        raise LinkedInOAuthError(f"LinkedIn token exchange failed ({resp.status_code}): {resp.text[:300]}")

    token = resp.json().get("access_token")
    if not token:
        raise LinkedInOAuthError("LinkedIn's token response did not include an access_token.")

    settings.LINKEDIN_ACCESS_TOKEN = token
    _write_token_to_env_file(token)
    logger.info("[linkedin_oauth] Member access token obtained and stored (value not logged).")


def _write_token_to_env_file(token: str) -> None:
    """Best-effort persistence so the token survives a backend restart. Rewrites
    only the LINKEDIN_ACCESS_TOKEN= line in backend/.env, leaving every other line
    byte-for-byte untouched; appends the line if it's missing entirely. Never
    raises -- a failure here just means the token stays in-memory for this process."""
    env_path = ENV_FILE_PATH
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True) if env_path.exists() else []
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith("LINKEDIN_ACCESS_TOKEN="):
                lines[i] = f"LINKEDIN_ACCESS_TOKEN={token}\n"
                found = True
                break
        if not found:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(f"LINKEDIN_ACCESS_TOKEN={token}\n")
        env_path.write_text("".join(lines), encoding="utf-8")
    except OSError as e:
        logger.warning(f"[linkedin_oauth] Could not write token back to .env (in-memory only for now): {e}")


def is_oauth_configured() -> bool:
    return bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET and settings.LINKEDIN_REDIRECT_URI)


def is_connected() -> bool:
    return bool(settings.LINKEDIN_ACCESS_TOKEN)
