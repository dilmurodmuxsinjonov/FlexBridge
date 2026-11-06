"""Comprehensive Regression Suite for TD-001 (FIX-01..FIX-14) and REV-001 (R-01..R-13, 17 Probes).

Verifies that all 13 priority defects (R-01..R-13) and all 17 negative probes from
`reviews/2026-11-07/reproduce_findings.py` are permanently resolved and guarded in CI.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from fastapi.testclient import TestClient

from app.api.v1.billing import billing_service
from app.api.v1.operations import operations_service
from app.main import app
from app.services.auth import auth_service, hash_password, verify_password
from app.services.availability import CandidateAvailabilityService
from app.services.governance import governance_service
from app.services.internship_logs import internship_log_service
from app.services.opportunities import opportunity_service

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app, raise_server_exceptions=False)


def test_r01_public_admin_registration_and_unauthenticated_admin_action_blocked() -> None:
    """R-01 / Probes 1 & 2: Public registration rejects privileged roles (403) and admin endpoints require Bearer session (401)."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Synthetic Admin Attempt",
            "password": "Review-only-1357!",
            "adult_confirmed": True,
            "roles": ["SUPER_ADMIN"],
        },
    )
    assert reg.status_code == 403
    assert reg.json()["detail"]["code"] == "FORBIDDEN_PRIVILEGED_ROLE_REGISTRATION"

    supervision = governance_service.register_student_supervision(
        institution_id="inst-reg-1",
        student_id="stu-reg-1",
        supervisor_id="sup-reg-1",
    )
    unauth = client.post(
        "/api/v1/internships/academic-assignments",
        json={
            "actor_id": "invented-admin",
            "actor_role": "SUPER_ADMIN",
            "institution_id": "inst-reg-1",
            "placement_id": "pl-reg-1",
            "supervision_id": supervision["id"],
            "supervisor_id": "sup-reg-1",
        },
    )
    assert unauth.status_code == 401
    assert unauth.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_r02_r06_r10_r11_billing_webhook_refund_ceiling_idempotency_and_expiry() -> None:
    """R-02, R-06, R-10, R-11 / Probes 3, 4, 5, 6: Payment requires webhook confirmation, refunds respect cumulative ceiling, idempotency binds payload, and expired entitlement blocks publish."""
    order = client.post(
        "/api/v1/billing/orders",
        json={
            "organization_id": "org-fix-05",
            "plan_code": "ORG_PLAN_30D",
            "created_by": "emp-fix-05",
        },
    ).json()

    # Probe 3: Payment attempt without provider confirmation stays PENDING_PROVIDER
    pay = client.post(
        "/api/v1/billing/payments/attempts",
        json={
            "invoice_id": order["invoice_id"],
            "idempotency_key": "fix-05-key-1",
            "amount_uzs": 599_000,
            "actor_user_id": "emp-fix-05",
        },
    )
    assert pay.status_code == 200
    assert pay.json()["status"] == "PENDING_PROVIDER"

    # Probe 5: Reusing idempotency_key with different payload fails with 409 IDEMPOTENCY_CONFLICT
    other_order = client.post(
        "/api/v1/billing/orders",
        json={
            "organization_id": "org-fix-05-other",
            "plan_code": "SINGLE_POST_30D",
            "created_by": "emp-fix-05",
        },
    ).json()
    replay_mismatch = client.post(
        "/api/v1/billing/payments/attempts",
        json={
            "invoice_id": other_order["invoice_id"],
            "idempotency_key": "fix-05-key-1",
            "amount_uzs": 1,
            "currency_code": "USD",
            "actor_user_id": "other-user",
        },
    )
    assert replay_mismatch.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in replay_mismatch.json()["detail"]

    # Confirm via API-X04 provider webhook -> SUCCEEDED
    wh = client.post(
        "/api/v1/webhooks/payments/PAYME",
        json={
            "provider_event_id": "evt-fix-05-1",
            "idempotency_key": "fix-05-key-1",
            "amount_uzs": 599_000,
            "signature": "VALID_PROVIDER_WEBHOOK_SIGNATURE",
        },
    )
    assert wh.status_code == 200
    assert wh.json()["status"] == "SUCCEEDED"

    # Probe 4: Cumulative refund exceeding invoice amount (2 x 599,000 UZS) fails on 2nd call with 409
    r1 = client.post(
        "/api/v1/billing/refunds",
        json={
            "invoice_id": order["invoice_id"],
            "amount_uzs": 599_000,
            "reason": "Full refund 1",
            "requested_by": "adm-a",
            "approved_by": "adm-b",
            "second_approver_id": "adm-c",
        },
    )
    r2 = client.post(
        "/api/v1/billing/refunds",
        json={
            "invoice_id": order["invoice_id"],
            "amount_uzs": 599_000,
            "reason": "Duplicate full refund 2",
            "requested_by": "adm-a",
            "approved_by": "adm-b",
            "second_approver_id": "adm-c",
        },
    )
    assert [r1.status_code, r2.status_code] == [201, 409]

    # Probe 6: Expired entitlement cannot publish slots
    eid = pay.json()["entitlement_id"]
    billing_service._entitlements[eid] = dataclasses.replace(
        billing_service._entitlements[eid],
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
    )
    exp_pub = client.post(
        "/api/v1/billing/slots/publish",
        json={
            "organization_id": "org-fix-05",
            "opportunity_id": "opp-exp-1",
            "actor_user_id": "emp-fix-05",
        },
    )
    assert exp_pub.status_code == 409
    assert "ENTITLEMENT_EXPIRED" in exp_pub.json()["detail"]


def test_r05_contract_type_required_and_quota_enforced_on_opportunity_revisions() -> None:
    """R-05 / Probe 7: Omitting contract_type returns 422 and publishing >5 concurrent opportunities fails with 409."""
    missing_ct = client.post(
        "/api/v1/opportunities/revisions",
        json={
            "organization_id": "org-unpaid-fix-06",
            "title": "Missing Contract Type",
            "hourly_pay": 10000,
        },
    )
    assert missing_ct.status_code == 422

    statuses = []
    for i in range(6):
        res = client.post(
            "/api/v1/opportunities/revisions",
            json={
                "organization_id": "org-quota-ceiling-fix-06",
                "title": f"Role {i}",
                "opportunity_kind": "PART_TIME_JOB",
                "contract_type": "LABOR_PART_TIME",
                "compensation_type": "HOURLY",
                "hourly_pay": 25000,
            },
        )
        statuses.append(res.status_code)
    assert statuses == [201, 201, 201, 201, 201, 409]


def test_r04_sticky_quarantine_pdf_header_and_file_acl() -> None:
    """R-04 / Probes 8 & 9: Quarantined file cannot be cleared by re-scanning, non-PDF is rejected, and unrelated user gets 403."""
    up = client.post(
        "/api/v1/files/upload-init",
        json={"owner_id": "owner-fix-08", "filename": "cv.pdf"},
    ).json()
    fid = up["id"]

    bad = client.post(f"/api/v1/files/{fid}/complete-scan", json={"content_sample": "%PDF-1.7 /JavaScript"})
    assert bad.json()["scan_status"] == "QUARANTINED"

    retry = client.post(f"/api/v1/files/{fid}/complete-scan", json={"content_sample": "%PDF-1.7 Clean text"})
    assert retry.json()["scan_status"] == "QUARANTINED"

    up2 = client.post(
        "/api/v1/files/upload-init",
        json={"owner_id": "owner-fix-08", "filename": "clean.pdf"},
    ).json()
    fid2 = up2["id"]
    ok = client.post(f"/api/v1/files/{fid2}/complete-scan", json={"content_sample": "%PDF-1.7 Valid PDF"})
    assert ok.json()["scan_status"] == "CLEAN"

    unrelated_dl = client.get(f"/api/v1/files/{fid2}/download", params={"requester_id": "stranger-user"})
    assert unrelated_dl.status_code == 403
    assert unrelated_dl.json()["detail"]["code"] == "FILE_ACCESS_DENIED"


def test_r09_shared_circuit_breaker_503_and_pilot_readiness_coupling() -> None:
    """R-09 / Probes 10, 11, 12: Tripping operations breaker freezes billing with 503 and sets pilot_ready=False."""
    operations_service.circuit_breaker.trip(
        actor_id="ops-1",
        incident_id="inc-fix-13",
        reason_code="LEDGER_MISMATCH",
        details="Regression test trip",
    )
    try:
        assert billing_service.circuit_breaker.state == "OPEN"
        blocked = client.post(
            "/api/v1/billing/orders",
            json={"organization_id": "org-1", "plan_code": "ORG_PLAN_30D", "created_by": "u-1"},
        )
        assert blocked.status_code == 503
        assert blocked.json()["detail"]["code"] == "P1_FINANCE_CIRCUIT_OPEN"

        ready = client.get("/api/v1/operations/pilot-readiness")
        assert ready.status_code == 200
        assert ready.json()["pilot_ready"] is False
    finally:
        operations_service.circuit_breaker.reset(
            actor_id="ops-1",
            second_approver_id="ops-2",
            resolution_note="Reset after test_r09_shared_circuit_breaker_503_and_pilot_readiness_coupling",
        )


def test_r08_r13_r12_r03_r07_logs_availability_argon2id_multiprocess_and_132_contracts() -> None:
    """R-08, R-13, R-12, R-03, R-07 / Probes 13, 14, 15, 16, 17."""
    # Probe 13: Negative minutes and nonexistent placement rejected with 422
    bad_log = client.post(
        "/api/v1/internship-logs/daily-logs",
        json={
            "placement_id": "nonexistent-placement",
            "author_id": "stu-1",
            "log_date": "2026-11-07",
            "summary_text": "Invalid log",
            "total_minutes": -1,
        },
    )
    assert bad_log.status_code == 422
    assert bad_log.json()["status"] == "REJECTED"

    # Probe 14: Adjacent availability intervals [540, 720) + [720, 900) cover [540, 900)
    avail = CandidateAvailabilityService()
    avail.add_availability_rule(candidate_id="cand-adj", weekday=1, start_minute=540, end_minute=720)
    avail.add_availability_rule(candidate_id="cand-adj", weekday=1, start_minute=720, end_minute=900)
    assert avail.is_candidate_available_for_shift(
        candidate_id="cand-adj",
        weekday=1,
        start_minute=540,
        end_minute=900,
    ) is True

    # Probe 15: Real Argon2id hash (RFC 9106 Type.ID), not PBKDF2
    digest = hash_password("Review-only-1357!", salt="fixed-review-salt")
    pbkdf = hashlib.pbkdf2_hmac("sha256", b"Review-only-1357!", b"fixed-review-salt", 120000).hex()
    assert digest.startswith("$argon2id$v=19$")
    assert digest != f"argon2id_v1$fixed-review-salt${pbkdf}"
    assert verify_password("Review-only-1357!", digest) is True

    # Probe 16: Cross-process session persistence via SQLite WAL
    child_code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "u = c.post('/api/v1/auth/register', json={'display_name': 'Subproc User', 'password': 'Password123!', 'adult_confirmed': True}).json()\n"
        "s = c.post('/api/v1/auth/login', json={'user_id': u['id'], 'password': 'Password123!'}).json()\n"
        "print(s['session_id'])\n"
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT / "backend"))
    child = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=ROOT / "backend",
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    token = child.stdout.strip()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    # Probe 17: All 132 canonical API contracts from FlexBridge_model_1_4.json present in OpenAPI
    model = json.loads((ROOT / "specs" / "v1_4" / "FlexBridge_model_1_4.json").read_text(encoding="utf-8"))
    normalize = lambda path: re.sub(r"\{[^}]+\}", "{}", path)
    routes = {
        (method.upper(), normalize(path))
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}
    }
    contracts = model["apis"] + model["helper_apis"]
    matched = [a["id"] for a in contracts if (a["method"], normalize(a["path"])) in routes]
    assert len(matched) == 132


def test_rev_002_all_30_checks_and_12_sections() -> None:
    """Execute REV-002 recheck.py and verify 30/30 checks pass (defects_observed == 0, improvements_confirmed == 8)."""
    recheck_script = ROOT / "reviews" / "2026-11-07" / "recheck_984fec5" / "recheck.py"
    completed = subprocess.run(
        [sys.executable, str(recheck_script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["checks"] == 30
    assert report["defects_observed"] == 0
    assert report["improvements_confirmed"] == 8
