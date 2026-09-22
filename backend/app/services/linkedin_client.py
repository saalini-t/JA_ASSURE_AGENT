"""
LinkedIn API client -- low-level, stateless HTTP calls only.

No compliance/HITL/idempotency logic lives here (that's publishing_service.py's job).
This module must NEVER be imported from a route handler directly -- the only caller
is publishing_service.py, which enforces hitl_service.is_publishable() before ever
reaching LinkedIn. That is what makes the gate impossible to bypass by accident.

Author-URN resolution order (userinfo -> me -> organization) and the ugcPosts text
payload shape are adapted from a teammate's separate LinkedIn integration, rewritten
here as async httpx (instead of synchronous `requests`) so a slow LinkedIn response
never blocks the FastAPI event loop.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger("ja_assure.linkedin")

API_BASE = "https://api.linkedin.com/v2"
REST_TIMEOUT = 15.0
UPLOAD_TIMEOUT = 60.0


class LinkedInError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LinkedInNotConfiguredError(LinkedInError):
    """Permanent: no access token configured. Never retry."""


class LinkedInPermanentError(LinkedInError):
    """Permanent: invalid token/payload/asset, or any other non-retryable 4xx."""


class LinkedInTransientError(LinkedInError):
    """Transient: timeout, connection error, 5xx, rate limiting. Safe to retry."""


def _require_token() -> str:
    if not settings.LINKEDIN_ACCESS_TOKEN:
        raise LinkedInNotConfiguredError(
            "LINKEDIN_ACCESS_TOKEN is not configured. Set it in backend/.env to enable LinkedIn publishing."
        )
    return settings.LINKEDIN_ACCESS_TOKEN


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _raise_for_status(resp: httpx.Response, action: str) -> None:
    if resp.status_code in (200, 201):
        return
    body = resp.text[:300]
    if resp.status_code in (401, 403):
        raise LinkedInPermanentError(f"LinkedIn {action} failed: authorization error ({resp.status_code}): {body}")
    if resp.status_code == 429:
        raise LinkedInTransientError(f"LinkedIn {action} failed: rate limited (429): {body}")
    if resp.status_code >= 500:
        raise LinkedInTransientError(f"LinkedIn {action} failed: server error ({resp.status_code}): {body}")
    raise LinkedInPermanentError(f"LinkedIn {action} failed: invalid request ({resp.status_code}): {body}")


async def _get(client: httpx.AsyncClient, url: str, headers: dict) -> httpx.Response:
    try:
        return await client.get(url, headers=headers, timeout=REST_TIMEOUT)
    except httpx.TransportError as e:
        raise LinkedInTransientError(f"Request to {url} failed: {e}")


async def _post(client: httpx.AsyncClient, url: str, headers: dict, json: dict) -> httpx.Response:
    try:
        return await client.post(url, headers=headers, json=json, timeout=REST_TIMEOUT)
    except httpx.TransportError as e:
        raise LinkedInTransientError(f"Request to {url} failed: {e}")


async def _put_binary(client: httpx.AsyncClient, url: str, token: str, content: bytes) -> httpx.Response:
    try:
        return await client.put(
            url, headers={"Authorization": f"Bearer {token}"}, content=content, timeout=UPLOAD_TIMEOUT
        )
    except httpx.TransportError as e:
        raise LinkedInTransientError(f"Media upload to LinkedIn failed: {e}")


async def resolve_author_urn(client: httpx.AsyncClient, token: str) -> str:
    """
    Resolve the URN to publish as: personal member URN via /v2/userinfo, falling back
    to /v2/me, falling back to the configured organization URN. Raises
    LinkedInPermanentError if none of these resolve.
    """
    headers = _headers(token)

    resp = await _get(client, f"{API_BASE}/userinfo", headers)
    if resp.status_code == 200:
        sub = resp.json().get("sub")
        if sub:
            return f"urn:li:person:{sub}"

    resp = await _get(client, f"{API_BASE}/me", headers)
    if resp.status_code == 200:
        member_id = resp.json().get("id")
        if member_id:
            return f"urn:li:person:{member_id}"

    if settings.LINKEDIN_ORGANIZATION_ID:
        org_id = settings.LINKEDIN_ORGANIZATION_ID.strip().rstrip("/").split("/")[-1]
        return f"urn:li:organization:{org_id}"

    raise LinkedInPermanentError(
        "Could not resolve a LinkedIn author URN: /v2/userinfo and /v2/me both failed, "
        "and LINKEDIN_ORGANIZATION_ID is not configured as a fallback."
    )


def _ugc_payload(author_urn: str, text: str, media_category: str, asset_urn: Optional[str] = None) -> dict:
    content: dict = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": media_category,
    }
    if asset_urn:
        content["media"] = [{"status": "READY", "media": asset_urn}]
    return {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }


async def _register_upload(
    client: httpx.AsyncClient, token: str, author_urn: str, recipe: str
) -> Tuple[str, str]:
    """recipe: 'feedshare-image' or 'feedshare-video'. Returns (upload_url, asset_urn)."""
    payload = {
        "registerUploadRequest": {
            "recipes": [f"urn:li:digitalmediaRecipe:{recipe}"],
            "owner": author_urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    resp = await _post(client, f"{API_BASE}/assets?action=registerUpload", _headers(token), payload)
    _raise_for_status(resp, "asset registration")
    value = resp.json()["value"]
    upload_url = value["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    return upload_url, value["asset"]


async def publish_text(text: str) -> dict:
    """Create a plain text LinkedIn post. Returns {"external_post_id": str}."""
    token = _require_token()
    async with httpx.AsyncClient() as client:
        author_urn = await resolve_author_urn(client, token)
        payload = _ugc_payload(author_urn, text, "NONE")
        resp = await _post(client, f"{API_BASE}/ugcPosts", _headers(token), payload)
        _raise_for_status(resp, "text post creation")
        post_id = resp.json().get("id") or resp.headers.get("x-restli-id") or "urn:li:share:unknown"
        return {"external_post_id": post_id}


async def _publish_with_media(text: str, file_path: Path, recipe: str, media_category: str) -> dict:
    token = _require_token()
    if not file_path.exists():
        raise LinkedInPermanentError(f"{media_category.title()} file not found: {file_path}")
    file_bytes = file_path.read_bytes()

    async with httpx.AsyncClient() as client:
        author_urn = await resolve_author_urn(client, token)
        upload_url, asset_urn = await _register_upload(client, token, author_urn, recipe)

        upload_resp = await _put_binary(client, upload_url, token, file_bytes)
        if upload_resp.status_code not in (200, 201):
            _raise_for_status(upload_resp, f"{media_category.lower()} binary upload")

        payload = _ugc_payload(author_urn, text, media_category, asset_urn=asset_urn)
        resp = await _post(client, f"{API_BASE}/ugcPosts", _headers(token), payload)
        _raise_for_status(resp, f"{media_category.lower()} post creation")
        post_id = resp.json().get("id") or resp.headers.get("x-restli-id") or "urn:li:share:unknown"
        return {"external_post_id": post_id, "asset_urn": asset_urn}


async def publish_image(text: str, image_path: Path) -> dict:
    """Register + upload an image asset, then create a LinkedIn post referencing it."""
    return await _publish_with_media(text, image_path, "feedshare-image", "IMAGE")


async def publish_video(text: str, video_path: Path) -> dict:
    """Register + upload a video asset, then create a LinkedIn post referencing it."""
    return await _publish_with_media(text, video_path, "feedshare-video", "VIDEO")


async def get_post_engagement(post_urn: str) -> dict:
    """
    Real LinkedIn Social Actions API call for a published post's likes/comments
    counts (GET /v2/socialActions/{urn}). This is a genuinely real attempt, not
    fabricated data -- most publish-only OAuth tokens (w_member_social /
    w_organization_social) lack the read scope (r_organization_social) this
    endpoint requires, so a permission failure here is an expected, HONEST outcome
    to surface, never papered over with invented numbers. Raises
    LinkedInPermanentError/LinkedInTransientError on failure, exactly like the
    publish functions -- the caller (analytics_service) is responsible for
    recording that failure honestly rather than treating it as zero engagement.
    """
    token = _require_token()
    encoded_urn = post_urn.replace(":", "%3A")
    async with httpx.AsyncClient() as client:
        resp = await _get(client, f"{API_BASE}/socialActions/{encoded_urn}", _headers(token))
        _raise_for_status(resp, "engagement fetch")
        data = resp.json()
        likes = data.get("likesSummary", {}).get("totalLikes", 0)
        comments = data.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
        return {"post_urn": post_urn, "likes": likes, "comments": comments, "source": "linkedin_api"}
