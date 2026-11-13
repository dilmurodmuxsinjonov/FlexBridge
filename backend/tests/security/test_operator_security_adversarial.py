"""Adversarial security and invariant penetration tests for Operator Security & Operations (API-118..124).

Coverage:
- Authentication & RBAC boundary penetration (401, 403)
- Dual-control bypass and self-approval prevention (API-119 / 403)
- Privilege escalation prevention: Auditor cannot mutate operational state (403)
- Uniform 404 IDOR defense for nonexistent user and commander targets
- Severity schema constraint enforcement (422)
- Zero Customer PII leakage audit
- Malformed cursor and inverted date range handling (422)
"""

from uuid import uuid4
import pytest
from app.db.storage import now, table, transaction


PROHIBITED_PII_FIELDS = {
    "email", "phone", "first_name", "last_name", "full_name",
    "passport", "pan", "cvv", "card_number", "ssn", "pinfl",
}


def test_adversarial_unauthenticated_requests_denied_401(client):
    endpoints = [
        ("GET", "/api/v1/operator/audit-events"),
        ("POST", "/api/v1/operator/access-requests", {"target_user_id": str(uuid4()), "role_code": "OPERATIONS", "reason": "test", "independent_approver_id": str(uuid4())}),
        ("POST", f"/api/v1/operator/users/{uuid4()}/revoke-sessions", {"reason": "test"}),
        ("POST", "/api/v1/operator/incidents", {"severity": "P1", "title": "test incident", "commander_id": str(uuid4())}),
        ("GET", "/api/v1/operator/restore-runs"),
        ("GET", "/api/v1/operator/analytics"),
    ]

    for item in endpoints:
        method = item[0]
        url = item[1]
        payload = item[2] if len(item) > 2 else None

        if method == "GET":
            res = client.get(url)
        else:
            res = client.post(url, json=payload or {})

        assert res.status_code == 401, f"{method} {url} returned {res.status_code} instead of 401: {res.text}"


def test_adversarial_non_admin_forbidden_403(client, identities):
    user = identities()  # Regular user without platform roles

    endpoints = [
        ("GET", "/api/v1/operator/audit-events"),
        ("POST", "/api/v1/operator/access-requests", {"target_user_id": str(uuid4()), "role_code": "OPERATIONS", "reason": "test reason", "independent_approver_id": str(uuid4())}),
        ("POST", f"/api/v1/operator/users/{uuid4()}/revoke-sessions", {"reason": "test reason"}),
        ("POST", "/api/v1/operator/incidents", {"severity": "P1", "title": "test incident", "commander_id": str(uuid4())}),
        ("GET", "/api/v1/operator/restore-runs"),
        ("GET", "/api/v1/operator/analytics"),
    ]

    for item in endpoints:
        method = item[0]
        url = item[1]
        payload = item[2] if len(item) > 2 else None

        if method == "GET":
            res = client.get(url, headers=user["headers"])
        else:
            res = client.post(url, json=payload or {}, headers=user["headers"])

        assert res.status_code == 403, f"{method} {url} returned {res.status_code} instead of 403: {res.text}"
        detail = res.json().get("detail", {})
        code = detail.get("code") if isinstance(detail, dict) else ""
        assert code in {"PERMISSION_DENIED", "INSUFFICIENT_PERMISSIONS", "FORBIDDEN"}


def test_adversarial_auditor_cannot_mutate_403(client, identities):
    auditor = identities("AUDITOR")

    mutations = [
        ("POST", "/api/v1/operator/access-requests", {"target_user_id": str(uuid4()), "role_code": "OPERATIONS", "reason": "test reason", "independent_approver_id": str(uuid4())}),
        ("POST", f"/api/v1/operator/users/{uuid4()}/revoke-sessions", {"reason": "test reason"}),
        ("POST", "/api/v1/operator/incidents", {"severity": "P1", "title": "test incident", "commander_id": str(uuid4())}),
    ]

    for method, url, payload in mutations:
        res = client.post(url, json=payload, headers=auditor["headers"])
        assert res.status_code == 403, f"AUDITOR unexpectedly succeeded at mutating {url}: {res.status_code}"


def test_adversarial_api119_self_approval_forbidden_403(client, identities):
    admin = identities("ADMIN")
    target = identities()

    payload = {
        "target_user_id": target["user_id"],
        "role_code": "OPERATIONS",
        "reason": "Attempting self-approved break-glass escalation",
        "independent_approver_id": admin["user_id"],  # Self-approval exploit attempt
        "duration_minutes": 60,
    }

    res = client.post("/api/v1/operator/access-requests", json=payload, headers=admin["headers"])
    assert res.status_code == 403, res.text
    detail = res.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "SELF_APPROVAL_FORBIDDEN"


def test_adversarial_api119_excessive_duration_422(client, identities):
    admin1 = identities("ADMIN")
    admin2 = identities("ADMIN")
    target = identities()

    payload = {
        "target_user_id": target["user_id"],
        "role_code": "OPERATIONS",
        "reason": "Requesting excessive duration grant",
        "independent_approver_id": admin2["user_id"],
        "duration_minutes": 300,  # Max allowed is 240
    }

    res = client.post("/api/v1/operator/access-requests", json=payload, headers=admin1["headers"])
    assert res.status_code == 422, res.text
    detail = res.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "INVALID_DURATION"


def test_adversarial_api120_nonexistent_user_uniform_404(client, identities):
    admin = identities("ADMIN")
    random_user_id = str(uuid4())

    res = client.post(
        f"/api/v1/operator/users/{random_user_id}/revoke-sessions",
        json={"reason": "Emergency revocation for unknown user"},
        headers=admin["headers"],
    )
    assert res.status_code == 404, res.text
    detail = res.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "USER_NOT_FOUND"


def test_adversarial_api122_invalid_severity_422(client, identities):
    admin = identities("ADMIN")

    for bad_sev in ["CRITICAL", "P0", "EMERGENCY", "HIGH", ""]:
        res = client.post(
            "/api/v1/operator/incidents",
            json={"severity": bad_sev, "title": "Invalid Severity Incident", "commander_id": admin["user_id"]},
            headers=admin["headers"],
        )
        assert res.status_code == 422, f"Expected 422 for severity {bad_sev}, got {res.status_code}"
        detail = res.json().get("detail", {})
        code = detail.get("code") if isinstance(detail, dict) else ""
        assert code == "INVALID_SEVERITY"


def test_adversarial_api122_nonexistent_commander_404(client, identities):
    admin = identities("ADMIN")
    random_cmd_id = str(uuid4())

    res = client.post(
        "/api/v1/operator/incidents",
        json={"severity": "P1", "title": "Missing Commander Incident", "commander_id": random_cmd_id},
        headers=admin["headers"],
    )
    assert res.status_code == 404, res.text
    detail = res.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "COMMANDER_NOT_FOUND"


def test_adversarial_zero_customer_pii_leakage_audit(client, identities):
    admin = identities("ADMIN")

    def _check_no_pii(data, path=""):
        if isinstance(data, dict):
            for k, v in data.items():
                low_k = k.lower()
                assert low_k not in PROHIBITED_PII_FIELDS, f"Prohibited customer PII key '{k}' found at {path}"
                _check_no_pii(v, f"{path}.{k}")
        elif isinstance(data, list):
            for i, it in enumerate(data):
                _check_no_pii(it, f"{path}[{i}]")

    res_audit = client.get("/api/v1/operator/audit-events?limit=20", headers=admin["headers"])
    assert res_audit.status_code == 200
    _check_no_pii(res_audit.json())

    res_analytics = client.get("/api/v1/operator/analytics", headers=admin["headers"])
    assert res_analytics.status_code == 200
    _check_no_pii(res_analytics.json())


def test_adversarial_invalid_cursor_and_date_ranges_422(client, identities):
    admin = identities("ADMIN")

    # Inverted date range
    res_range = client.get(
        "/api/v1/operator/audit-events?start_date=2026-12-31&end_date=2026-01-01",
        headers=admin["headers"],
    )
    assert res_range.status_code == 422, res_range.text
    detail = res_range.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "INVALID_DATE_RANGE"

    # Malformed cursor
    res_cursor = client.get(
        "/api/v1/operator/audit-events?cursor=not-a-valid-base64-cursor!!!",
        headers=admin["headers"],
    )
    assert res_cursor.status_code == 422, res_cursor.text
    detail = res_cursor.json().get("detail", {})
    code = detail.get("code") if isinstance(detail, dict) else ""
    assert code == "INVALID_CURSOR"
