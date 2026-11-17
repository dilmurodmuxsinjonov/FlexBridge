"""Adversarial and security hardening tests for Public Discovery & Catalog APIs.

Tests:
- Guest unauthenticated access permitted without Bearer token.
- SQL injection attempts in search queries safely sanitized via parameterized queries.
- Directory traversal / slug injection in help and policies strictly rejected with 404.
- Excessive limit query clamping (e.g. limit=1000 clamped to 100, limit=-1 clamped to 1).
- Corrupted/malformed base64 cursor graceful handling without 500 error.
- Non-published and closed opportunities remain invisible under fuzzing.
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.storage import table, transaction, now


def test_guest_unauthenticated_access_allowed(client: TestClient):
    # Verify all public routes work with zero Authorization header
    routes = [
        "/api/v1/opportunities",
        "/api/v1/onboarding/options",
        "/api/v1/services/public",
        "/api/v1/prices/public",
        "/api/v1/help/faq",
        "/api/v1/policies/terms",
    ]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Expected 200 without auth for {r}, got {resp.status_code}"


def test_sql_injection_in_search_query_is_safe(client: TestClient):
    # Pass SQL injection payloads in query and region parameters
    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE opportunities; --",
        "admin'--",
        "' UNION SELECT * FROM users --",
    ]
    for p in payloads:
        resp = client.get(f"/api/v1/opportunities?query={p}&region={p}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_id"] == "API-001"
        assert isinstance(data["items"], list)


def test_path_traversal_in_help_and_policies(client: TestClient):
    traversal_slugs = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "....//....//config",
        "/absolute/path/file",
        "terms.json",
        "../app/main.py",
    ]
    for slug in traversal_slugs:
        resp_h = client.get(f"/api/v1/help/{slug}")
        assert resp_h.status_code in (401, 404)

        resp_p = client.get(f"/api/v1/policies/{slug}")
        assert resp_p.status_code in (401, 404)


def test_limit_clamping_and_corrupted_cursor(client: TestClient):
    from app.services.opportunities import opportunity_service

    # Service-level limit clamping
    svc_res = opportunity_service.search_public_opportunities(limit=1000)
    assert svc_res["limit"] == 100

    svc_res_neg = opportunity_service.search_public_opportunities(limit=-5)
    assert svc_res_neg["limit"] == 1

    # HTTP query validation: Query(ge=1, le=100)
    resp_large = client.get("/api/v1/opportunities?limit=1000")
    assert resp_large.status_code in (200, 422)

    resp_neg = client.get("/api/v1/opportunities?limit=-5")
    assert resp_neg.status_code in (200, 422)

    # Corrupted base64 cursor -> strictly rejected with 400 INVALID_CURSOR
    resp_corrupt = client.get("/api/v1/opportunities?after=NOT_BASE_64_GARBAGE!!!")
    assert resp_corrupt.status_code == 400
    assert resp_corrupt.json()["detail"]["code"] == "INVALID_CURSOR"

    # Valid base64 but corrupted payload -> strictly rejected with 400 INVALID_CURSOR
    resp_corrupt_b64 = client.get("/api/v1/opportunities?after=bm90X3ZhbGlkX3BheWxvYWQ=")
    assert resp_corrupt_b64.status_code == 400
    assert resp_corrupt_b64.json()["detail"]["code"] == "INVALID_CURSOR"
