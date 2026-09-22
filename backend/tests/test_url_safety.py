"""
SSRF-safe URL validation. No real network calls -- httpx.Client.stream is
monkeypatched for the fetch test; validation tests use real DNS resolution
for "localhost"/loopback/known-private literals only (no external lookups).
"""
import pytest

from app.services.url_safety import UnsafeURLError, validate_public_http_url, safe_fetch_text


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeURLError, match="scheme"):
        validate_public_http_url("ftp://example.com/file")


def test_rejects_missing_hostname():
    with pytest.raises(UnsafeURLError, match="hostname"):
        validate_public_http_url("http:///no-host")


def test_rejects_localhost_by_name():
    with pytest.raises(UnsafeURLError, match="Blocked hostname"):
        validate_public_http_url("http://localhost:8000/admin")


def test_rejects_loopback_ip_literal():
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_public_http_url("http://127.0.0.1:8000/admin")


def test_rejects_private_rfc1918_ip_literal():
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_public_http_url("http://10.0.0.5/internal")
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_public_http_url("http://192.168.1.1/router")


def test_rejects_cloud_metadata_link_local_ip():
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_public_http_url("http://169.254.169.254/latest/meta-data/")


def test_allows_a_real_public_ip_literal():
    # 8.8.8.8 (Google DNS) is a genuinely public, non-loopback/private address --
    # this only exercises the ipaddress classification, no actual HTTP request.
    assert validate_public_http_url("http://8.8.8.8/") == "http://8.8.8.8/"


def test_safe_fetch_text_revalidates_final_url_after_redirect(monkeypatch):
    """A redirect chain landing on a private address must still be blocked,
    even though the original URL was public."""
    import httpx

    class FakeResponse:
        def __init__(self, url):
            self.url = url

        def iter_text(self):
            yield "should never be read"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def stream(self, method, url, headers=None):
            return FakeResponse("http://127.0.0.1:9000/internal-after-redirect")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(httpx, "Client", FakeClient)

    with pytest.raises(UnsafeURLError, match="non-public"):
        safe_fetch_text("https://example.com/redirects-to-internal")


def test_safe_fetch_text_returns_capped_text(monkeypatch):
    import httpx

    class FakeResponse:
        def __init__(self, url):
            self.url = url

        def iter_text(self):
            yield "a" * 40
            yield "b" * 40

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def stream(self, method, url, headers=None):
            return FakeResponse("https://example.com/")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(httpx, "Client", FakeClient)

    result = safe_fetch_text("https://example.com/", max_bytes=50)
    assert len(result) == 50
