"""
LinkedIn OAuth routes -- member posting only (w_member_social), no HITL/compliance
logic here at all. This only ever produces an access token for linkedin_client.py
to use; it cannot publish anything by itself. See app/services/linkedin_oauth.py.
"""
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services import linkedin_oauth
from app.services.linkedin_oauth import LinkedInOAuthError

router = APIRouter(prefix="/auth/linkedin", tags=["LinkedIn OAuth (Member Posting)"])


def _page(title: str, message: str, ok: bool) -> str:
    color = "#059669" if ok else "#dc2626"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 80px auto; text-align: center;">
  <h2 style="color: {color};">{title}</h2>
  <p style="color: #444;">{message}</p>
  <p style="color: #999; font-size: 12px;">You can close this tab.</p>
</body></html>"""


@router.get("/status")
def oauth_status():
    """Never returns the token itself -- only whether one is configured/present."""
    return {
        "oauth_configured": linkedin_oauth.is_oauth_configured(),
        "connected": linkedin_oauth.is_connected(),
    }


@router.get("/login")
def login(redirect: bool = Query(True, description="If true (default), 307-redirects the browser straight to LinkedIn. If false, returns the URL as JSON instead.")):
    """
    Visit this URL directly in a browser (http://localhost:8000/api/v1/auth/linkedin/login)
    to start the LinkedIn member-posting authorization flow. Requests exactly
    "openid profile w_member_social" -- never any organization/company-page scope.
    """
    try:
        url = linkedin_oauth.build_authorization_url()
    except LinkedInOAuthError as e:
        return HTMLResponse(_page("LinkedIn OAuth not configured", e.message, ok=False), status_code=400)

    if redirect:
        return RedirectResponse(url)
    return {"authorization_url": url}


@router.get("/callback")
async def callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """LinkedIn redirects the browser here after the member approves (or denies) access."""
    if error:
        return HTMLResponse(
            _page("LinkedIn authorization was not completed", error_description or error, ok=False),
            status_code=400,
        )
    if not code:
        return HTMLResponse(_page("Missing authorization code", "LinkedIn did not return a code.", ok=False), status_code=400)

    try:
        await linkedin_oauth.exchange_code_for_token(code, state)
    except LinkedInOAuthError as e:
        return HTMLResponse(_page("LinkedIn authorization failed", e.message, ok=False), status_code=400)

    return HTMLResponse(_page(
        "LinkedIn connected",
        "Your personal LinkedIn account is now authorized for posting (w_member_social). "
        "Approved content can now be dispatched from the Publishing screen or "
        "POST /api/v1/publishing/{content_id}/linkedin -- human approval is still required for every post.",
        ok=True,
    ))
