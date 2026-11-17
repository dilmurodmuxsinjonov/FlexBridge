"""Unit and contract tests for Public Catalog & CMS Policies (API-011, API-012, API-013, API-014).

Invariants:
- API-011 (GET /api/v1/services/public):
  * Public offerings catalog.
  * Clearly designates stage 1 vs stage 2 services.
- API-012 (GET /api/v1/prices/public):
  * Listing fee rules, pilot free tier, and prorated refund policy.
- API-013 (GET /api/v1/help/{document}):
  * Markdown content, versioning, sections.
  * Uniform 404 DOCUMENT_NOT_FOUND for unknown document.
- API-014 (GET /api/v1/policies/{document}):
  * Versioned legal policies (terms, privacy, cookies, acceptable-use, rating-guidelines).
  * Uniform 404 POLICY_NOT_FOUND for unknown document.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_api011_public_services_catalog(client: TestClient):
    resp = client.get("/api/v1/services/public")
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_id"] == "API-011"
    assert data["currency"] == "UZS"
    services = data["services"]
    assert len(services) >= 4

    svc_by_code = {s["code"]: s for s in services}
    assert "ACADEMIC_INTERNSHIP" in svc_by_code
    assert svc_by_code["ACADEMIC_INTERNSHIP"]["is_active"] is True
    assert svc_by_code["ACADEMIC_INTERNSHIP"]["stage"] == 1

    assert "PART_TIME_EMPLOYMENT" in svc_by_code
    assert svc_by_code["PART_TIME_EMPLOYMENT"]["is_active"] is True

    assert "DOUBLE_BLIND_EVALUATION" in svc_by_code
    assert svc_by_code["DOUBLE_BLIND_EVALUATION"]["is_active"] is True

    # Freelance marketplace Stage 2 hook
    assert "FREELANCE_MARKETPLACE" in svc_by_code
    assert svc_by_code["FREELANCE_MARKETPLACE"]["is_active"] is False
    assert svc_by_code["FREELANCE_MARKETPLACE"]["stage"] == 2


def test_api012_public_prices_and_refund_policy(client: TestClient):
    resp = client.get("/api/v1/prices/public")
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_id"] == "API-012"
    assert data["currency"] == "UZS"
    assert data["pricing_model"] == "SUBSCRIPTION_AND_LISTING"
    plans = data["plans"]
    assert len(plans) >= 2

    tiers = {p["tier"]: p for p in plans}
    assert "PILOT_FREE" in tiers
    assert tiers["PILOT_FREE"]["price_uzs"] == 0
    assert tiers["PILOT_FREE"]["duration_days"] == 30

    assert "SINGLE_POST_30D" in tiers
    assert tiers["SINGLE_POST_30D"]["price_uzs"] == 149000
    assert tiers["SINGLE_POST_30D"]["duration_days"] == 30

    assert "ORG_PLAN_30D" in tiers
    assert tiers["ORG_PLAN_30D"]["price_uzs"] == 599000
    assert tiers["ORG_PLAN_30D"]["opportunity_slots"] == 5

    # Refund policy verification
    refund = data["refund_policy"]
    assert refund["policy"] == "PRORATED_BEFORE_FIRST_APPLICATION"
    assert refund["full_refund_window_hours"] == 24
    assert refund["circuit_breaker_guarantee"] is True


def test_api013_public_help_documents_success_and_404(client: TestClient):
    # Test valid help documents
    for slug in ("faq", "getting-started", "candidate-guide", "employer-guide", "academic-guide", "schedule-matching"):
        resp = client.get(f"/api/v1/help/{slug}")
        assert resp.status_code == 200, f"Expected 200 for help/{slug}"
        data = resp.json()
        assert data["contract_id"] == "API-013"
        assert data["slug"] == slug
        assert len(data["title"]) > 0
        assert len(data["version"]) > 0
        assert len(data["content_markdown"]) > 0
        assert len(data["sections"]) > 0

    # Test unknown document returns 404
    resp_404 = client.get("/api/v1/help/non-existent-guide")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"


def test_api014_public_policy_documents_success_and_404(client: TestClient):
    # Test valid policy documents
    for doc in ("terms", "privacy", "cookies", "acceptable-use", "rating-guidelines"):
        resp = client.get(f"/api/v1/policies/{doc}")
        assert resp.status_code == 200, f"Expected 200 for policies/{doc}"
        data = resp.json()
        assert data["contract_id"] == "API-014"
        assert data["document"] == doc
        assert len(data["title"]) > 0
        assert len(data["version"]) > 0
        assert len(data["content_markdown"]) > 0
        assert len(data["clauses"]) > 0
        assert "contact_email" in data

    # Test unknown policy returns 404
    resp_404 = client.get("/api/v1/policies/super-secret-policy")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"]["code"] == "POLICY_NOT_FOUND"
