"""Adversarial and security boundary tests for Operator Security & Operations (API-118..124)."""

from uuid import uuid4
import pytest


def test_adversarial_unauthenticated_requests_denied_401(client):
    endpoints = [
        ("GET", "/api/v1/operator/audit-events"),
        ("POST", "/api/v1/operator/access-requests"),
        ("POST", f"/api/v1/operator/users/{uuid4()}/revoke-sessions"),
        ("POST", "/api/v1/operator/incidents"),
        ("GET", "/api/v1/operator/restore-runs"),
        ("GET", "/api/v1/operator/analytics"),
    ]
    for method, path in endpoints:
        fn = getattr(client, method.lower())
        res = fn(path)
        assert res.status_code == 401, f"{method} {path} returned {res.status_code}: {res.text}"


def test_adversarial_non_admin_actors_forbidden_403(client, identities):
    candidate = identities()
    auditor = identities("AUDITOR")

    # Regular candidate forbidden from all operator endpoints
    for method, path in [
        ("GET", "/api/v1/operator/audit-events"),
        ("POST", "/api/v1/operator/access-requests"),
        ("POST", f"/api/v1/operator/users/{uuid4()}/revoke-sessions"),
        ("POST", "/api/v1/operator/incidents"),
        ("GET", "/api/v1/operator/restore-runs"),
        ("GET", "/api/v1/operator/analytics"),
    ]:
        fn = getattr(client, method.lower())
        res = fn(path, headers=candidate["headers"])
        assert res.status_code == 403, f"{method} {path} allowed candidate!"
        assert res.json()["detail"]["code"] == "PERMISSION_DENIED"

    # Auditor is permitted read-only (API-118), but forbidden from mutations (API-119, API-120)
    res_audit = client.get("/api/v1/operator/audit-events", headers=auditor["headers"])
    assert res_audit.status_code == 200, res_audit.text

    res_grant = client.post(
        "/api/v1/operator/access-requests",
        json={"target_user_id": str(uuid4()), "role_code": "SUPPORT", "reason": "Test grant", "independent_approver_id": str(uuid4())},
        headers=auditor["headers"],
    )
    assert res_grant.status_code == 403, res_grant.text
    assert res_grant.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_adversarial_dual_control_self_approval_forbidden_403(client, identities):
    admin = identities("ADMIN")
    target_user = identities()

    # Admin attempts to approve their own emergency access request
    payload = {
        "target_user_id": target_user["user_id"],
        "role_code": "SUPPORT",
        "reason": "Admin attempting to approve their own privileged role request",
        "independent_approver_id": admin["user_id"],  # Self-approval!
        "duration_minutes": 120,
    }

    res = client.post("/api/v1/operator/access-requests", json=payload, headers=admin["headers"])
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["code"] == "SELF_APPROVAL_FORBIDDEN"


def test_adversarial_access_request_excessive_duration_422(client, identities):
    admin = identities("ADMIN")
    target_user = identities()
    independent_approver = identities("ADMIN")

    payload = {
        "target_user_id": target_user["user_id"],
        "role_code": "SUPPORT",
        "reason": "Requesting 500 minutes (exceeds 240 max)",
        "independent_approver_id": independent_approver["user_id"],
        "duration_minutes": 500,  # Exceeds max 240 mins!
    }

    res = client.post("/api/v1/operator/access-requests", json=payload, headers=admin["headers"])
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "INVALID_DURATION"


def test_adversarial_user_session_revocation_nonexistent_user_404(client, identities):
    admin = identities("ADMIN")
    nonexistent_id = str(uuid4())

    payload = {
        "reason": "Revoking nonexistent user",
    }

    res = client.post(f"/api/v1/operator/users/{nonexistent_id}/revoke-sessions", json=payload, headers=admin["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_adversarial_incident_invalid_severity_422(client, identities):
    admin = identities("ADMIN")
    commander = identities()

    payload = {
        "severity": "CRITICAL",  # Must be P1, P2, P3, P4
        "summary": "Valid summary of at least 10 chars",
        "commander_id": commander["user_id"],
    }

    res = client.post("/api/v1/operator/incidents", json=payload, headers=admin["headers"])
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "INVALID_SEVERITY"


def test_adversarial_incident_nonexistent_commander_404(client, identities):
    admin = identities("ADMIN")
    nonexistent_commander = str(uuid4())

    payload = {
        "severity": "P1",
        "summary": "Valid summary of at least 10 chars",
        "commander_id": nonexistent_commander,
    }

    res = client.post("/api/v1/operator/incidents", json=payload, headers=admin["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "COMMANDER_NOT_FOUND"


def test_adversarial_audit_events_invalid_date_formats_422(client, identities):
    admin = identities("ADMIN")

    res = client.get("/api/v1/operator/audit-events?start_date=not-a-date", headers=admin["headers"])
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "INVALID_DATE_FORMAT"
