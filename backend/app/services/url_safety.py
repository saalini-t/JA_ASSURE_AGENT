"""
SSRF-safe URL validation and fetching, adapted from a companion JA Assure
lead-generation project. Self-contained (stdlib + httpx only) -- used by
research_service.py's competitor scraper and lead_service.py's contact
enrichment before ever making an outbound request to a user/AI-supplied URL.

Blocks requests to loopback, private (RFC1918), link-local (including the
169.254.169.254 cloud metadata endpoint), multicast, and IANA-reserved
addresses -- for every IP a hostname resolves to, not just the first.

Known limitation (inherited from the source project, documented rather than
silently assumed away): this validates the resolved address at request time,
then lets httpx perform its own independent DNS resolution and connection --
a DNS answer that changes between validation and connection (DNS rebinding)
is not defended against. Acceptable for this use case (scraping public
marketing/competitor pages, not a security-critical proxy), not acceptable
to reuse as-is for a general-purpose SSRF-hardened proxy.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("ja_assure.url_safety")

_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF safety validation. Never retried."""


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(f"Unsupported URL scheme: {parsed.scheme!r} (only http/https allowed)")
    if not parsed.hostname:
        raise UnsafeURLError("URL has no hostname")
    if parsed.hostname.lower() in _BLOCKED_HOSTNAMES:
        raise UnsafeURLError(f"Blocked hostname: {parsed.hostname}")

    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        raise UnsafeURLError(f"Could not resolve hostname {parsed.hostname}: {e}")

    for family, _, _, _, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise UnsafeURLError(f"{parsed.hostname} resolves to a non-public address ({ip}) -- refusing to fetch")

    return url


def safe_fetch_text(url: str, max_bytes: int = 50_000, timeout: float = 8.0) -> str:
    """Validates the URL, fetches it, then re-validates the FINAL URL after
    any redirects (does not re-validate intermediate hops -- see module
    docstring). Returns up to max_bytes of decoded text. Raises
    UnsafeURLError or httpx exceptions on failure; never returns fabricated
    content."""
    validate_public_http_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JA-Assure-ResearchBot/2.0",
    }
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=min(timeout, 3.0)), follow_redirects=True, max_redirects=5) as client:
        with client.stream("GET", url, headers=headers) as response:
            validate_public_http_url(str(response.url))
            chunks = []
            total = 0
            for chunk in response.iter_text():
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
            return "".join(chunks)[:max_bytes]
