"""
Real-data lead discovery and contact enrichment, adapted from a companion
JA Assure lead-generation project (raw REST calls via httpx, no new SDKs).

Each function is a plain "real data in, dict/None out" call that NEVER
raises and NEVER fabricates -- a missing API key or any request failure
returns [] / None so lead_service.py's existing cascade (Groq-invented
profiles, then the demo pool) can fall through exactly as it already does
for the cloud image-provider cascade elsewhere in this codebase.
"""
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.services.url_safety import safe_fetch_text

logger = logging.getLogger("ja_assure.leads.discovery")

GOOGLE_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.websiteUri,places.rating,"
    "places.userRatingCount,places.editorialSummary,places.businessStatus"
)

# Query templates per brand vertical -- mirrors this codebase's existing
# brand -> industry-keyword mappings used elsewhere (lead scoring, compliance).
_BRAND_QUERY_TEMPLATES = {
    "jade": [
        "jewellery stores in {market}",
        "diamond and gemstone dealers in {market}",
        "luxury watch retailers in {market}",
    ],
    "doctorshield": [
        "private medical clinics in {market}",
        "aesthetic and cosmetic surgery clinics in {market}",
        "dental specialist clinics in {market}",
    ],
    "jaguartransit": [
        "freight forwarding companies in {market}",
        "logistics and cargo companies in {market}",
        "secure transport and courier companies in {market}",
    ],
}


def _brand_queries(brand: str, market: str, industry: Optional[str]) -> List[str]:
    if industry:
        return [f"{industry} businesses in {market}"]
    templates = _BRAND_QUERY_TEMPLATES.get(brand, [f"commercial businesses in {market}"])
    return [t.format(market=market) for t in templates]


def discover_real_businesses(
    brand: str, market: str, industry: Optional[str] = None, target_count: int = 5,
) -> List[Dict[str, Any]]:
    """Real business discovery via the Google Places API (New) Text Search
    endpoint. Returns real name/address/phone/website -- never a fabricated
    contact detail (email is never returned here; see find_real_contact_email
    for that, which only ever returns a real, discovered email or None)."""
    if not settings.GOOGLE_MAPS_API_KEY:
        return []

    candidates: List[Dict[str, Any]] = []
    seen_place_ids = set()
    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            for query in _brand_queries(brand, market, industry):
                if len(candidates) >= target_count:
                    break
                try:
                    resp = client.post(
                        GOOGLE_PLACES_SEARCH_URL, headers=headers,
                        json={"textQuery": query, "pageSize": 20},
                    )
                except httpx.HTTPError as e:
                    logger.warning(f"[google_places] query '{query}' network error: {e}")
                    continue
                if resp.status_code != 200:
                    logger.warning(f"[google_places] query '{query}' failed: HTTP {resp.status_code} {resp.text[:200]}")
                    continue
                for place in resp.json().get("places", []):
                    place_id = place.get("id")
                    if not place_id or place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(place_id)
                    website = (place.get("websiteUri") or "").strip() or None
                    domain = re.sub(r"^https?://(www\.)?", "", website).split("/")[0] if website else None
                    name = (place.get("displayName") or {}).get("text", "Unknown Business")
                    candidates.append({
                        "name": name,
                        "company": name,
                        "location": place.get("formattedAddress", market),
                        "phone": place.get("nationalPhoneNumber"),
                        "website": website,
                        "domain": domain,
                        "rating": place.get("rating"),
                        "user_rating_count": place.get("userRatingCount"),
                        "description": (place.get("editorialSummary") or {}).get("text"),
                    })
                    if len(candidates) >= target_count:
                        break
    except Exception as e:
        logger.error(f"[google_places] discovery failed unexpectedly: {e}")
        return []

    return candidates


_EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ASSET_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".js", ".css", ".webp")
_NOISE_DOMAINS = ("sentry.io", "wixpress.com", "google.com", "facebook.com", "example.com", "w3.org", "schema.org")
_NOISE_LOCALPARTS = ("noreply", "no-reply", "abuse", "postmaster", "webmaster")


def _clean_emails(raw_emails: List[str]) -> List[str]:
    cleaned = []
    for email in raw_emails:
        email_lower = email.lower().strip()
        if email_lower.endswith(_ASSET_EXTENSIONS):
            continue
        domain_part = email_lower.rsplit("@", 1)[-1]
        if any(noise in domain_part for noise in _NOISE_DOMAINS):
            continue
        local_part = email_lower.split("@", 1)[0]
        if any(local_part.startswith(noise) for noise in _NOISE_LOCALPARTS):
            continue
        if email_lower not in cleaned:
            cleaned.append(email_lower)
    return cleaned


def _find_via_hunter(domain: str) -> Optional[Dict[str, Any]]:
    if not settings.HUNTER_API_KEY:
        return None
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                "https://api.hunter.io/v2/domain-search",
                headers={"X-API-KEY": settings.HUNTER_API_KEY},
                params={"domain": domain, "limit": 10},
            )
    except httpx.HTTPError as e:
        logger.warning(f"[hunter_io] lookup for {domain} failed: {e}")
        return None
    if resp.status_code != 200:
        logger.info(f"[hunter_io] lookup for {domain} returned HTTP {resp.status_code}")
        return None

    for entry in resp.json().get("data", {}).get("emails", []):
        email = entry.get("value")
        if not email or not _clean_emails([email]):
            continue
        verification = (entry.get("verification") or {}).get("status")
        confidence = (entry.get("confidence") or 0) / 100
        if verification == "valid" or confidence >= 0.7:
            name = " ".join(filter(None, [entry.get("first_name"), entry.get("last_name")])) or None
            return {
                "email": email, "name": name, "role": entry.get("position"),
                "source": "hunter_io", "verified": verification == "valid",
            }
    return None


def _find_via_direct_scrape(domain: str) -> Optional[Dict[str, Any]]:
    try:
        html = safe_fetch_text(f"https://{domain}", max_bytes=60_000)
    except Exception as e:
        logger.info(f"[direct_scrape] could not fetch https://{domain}: {e}")
        return None

    found = _clean_emails(_EMAIL_REGEX.findall(html))
    if not found:
        return None
    domain_matches = [e for e in found if e.endswith(f"@{domain}")]
    best = domain_matches or found
    return {
        "email": best[0], "name": None, "role": None,
        "source": "direct_website_scrape", "verified": bool(domain_matches),
    }


def find_real_contact_email(domain: str) -> Optional[Dict[str, Any]]:
    """Real contact discovery: Hunter.io first (if configured), falling back
    to an SSRF-safe homepage scrape. Returns None -- never a fabricated
    email -- if neither source finds one."""
    if not domain:
        return None
    return _find_via_hunter(domain) or _find_via_direct_scrape(domain)
