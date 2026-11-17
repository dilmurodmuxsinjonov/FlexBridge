"""Unit and integration tests for HTTP Caching and Conditional Requests (CAP-039, FIX-HTTP-CACHE).

Verifies:
1. Public catalogs (/services/public, /prices/public, /onboarding/options) have public Cache-Control and ETag.
2. Public CMS (/help/{document}, /policies/{document}) have long-lived public Cache-Control (600s) and ETag.
3. Conditional request (If-None-Match) returns 304 Not Modified with empty body.
4. Conditional request with mismatched ETag returns 200 OK with fresh body.
5. Health checks (/health/live, /health/ready) enforce no-store and no-cache.
6. X-Content-Type-Options: nosniff security header is enforced.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_public_catalog_cache_headers_and_etag(client: TestClient):
    """Verify /services/public, /prices/public, and /onboarding/options return Cache-Control and ETag."""
    endpoints = [
        "/api/v1/services/public",
        "/api/v1/prices/public",
        "/api/v1/onboarding/options",
    ]
    for url in endpoints:
        resp = client.get(url)
        assert resp.status_code == 200
        cc = resp.headers.get("cache-control", "")
        assert "public" in cc
        assert "max-age=300" in cc
        assert "stale-while-revalidate=60" in cc
        etag = resp.headers.get("etag")
        assert etag is not None and len(etag) >= 10
        assert resp.headers.get("x-content-type-options") == "nosniff"


def test_public_cms_cache_headers(client: TestClient):
    """Verify /help/{doc} and /policies/{doc} return long-lived Cache-Control (600s) and ETag."""
    endpoints = [
        "/api/v1/help/getting-started",
        "/api/v1/policies/terms",
        "/api/v1/policies/privacy",
    ]
    for url in endpoints:
        resp = client.get(url)
        assert resp.status_code == 200
        cc = resp.headers.get("cache-control", "")
        assert "public" in cc
        assert "max-age=600" in cc
        assert "stale-while-revalidate=120" in cc
        assert resp.headers.get("etag") is not None


def test_conditional_request_304_not_modified(client: TestClient):
    """Verify If-None-Match header returns 304 Not Modified without sending body."""
    # First request: get ETag
    resp1 = client.get("/api/v1/services/public")
    assert resp1.status_code == 200
    etag = resp1.headers.get("etag")
    assert etag is not None

    # Second request: conditional If-None-Match matching etag
    resp2 = client.get("/api/v1/services/public", headers={"If-None-Match": etag})
    assert resp2.status_code == 304
    assert len(resp2.content) == 0
    assert resp2.headers.get("etag") == etag

    # Third request: weak etag matching
    resp3 = client.get("/api/v1/services/public", headers={"If-None-Match": f"W/{etag}"})
    assert resp3.status_code == 304
    assert len(resp3.content) == 0

    # Fourth request: mismatched etag returns 200
    resp4 = client.get("/api/v1/services/public", headers={"If-None-Match": '"outdated-etag-12345"'})
    assert resp4.status_code == 200
    assert len(resp4.content) > 0


def test_health_probes_enforce_no_store(client: TestClient):
    """Verify health endpoints explicitly prevent caching."""
    for url in ("/api/v1/health/live", "/api/v1/health/ready"):
        resp = client.get(url)
        assert resp.status_code in (200, 503)
        cc = resp.headers.get("cache-control", "")
        assert "no-store" in cc or "no-cache" in cc
        assert resp.headers.get("pragma") == "no-cache"
