"""REV-001: local review probes; observed=True confirms a defect, not acceptance.

Run: python reviews/2026-11-07/reproduce_findings.py
Only fresh process memory and review output files are changed. No external services.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.billing import billing_service
from app.api.v1.operations import operations_service
from app.services.governance import governance_service
from app.services.auth import hash_password
from app.services.availability import CandidateAvailabilityService
from app.services.internship_logs import internship_log_service
from app.services.opportunities import opportunity_service

client = TestClient(app, raise_server_exceptions=False)
results = []


def record(probe, observed, **evidence):
    results.append({"probe": probe, "defect_observed": bool(observed), "evidence": evidence})


registration = client.post("/api/v1/auth/register", json={
    "display_name": "Review synthetic user", "password": "Review-only-1357!",
    "adult_confirmed": True, "roles": ["SUPER_ADMIN"],
})
record("public_admin_registration", registration.status_code == 201 and
       "SUPER_ADMIN" in registration.json().get("roles", []),
       status=registration.status_code, roles=registration.json().get("roles"))

supervision = governance_service.register_student_supervision(
    institution_id="review-institution", student_id="review-student", supervisor_id="review-supervisor")
assignment = client.post("/api/v1/internships/academic-assignments", json={
    "actor_id": "invented-admin", "actor_role": "SUPER_ADMIN",
    "institution_id": "review-institution", "placement_id": "invented-placement",
    "supervision_id": supervision["id"], "supervisor_id": "review-supervisor",
})
record("unauthenticated_admin_action", assignment.status_code == 201,
       status=assignment.status_code, authorization_header=False,
       setup="existing supervision seeded as service fixture; actor identity and role supplied only by request body")

order = client.post("/api/v1/billing/orders", json={
    "organization_id": "review-org", "plan_code": "ORG_PLAN_30D", "created_by": "invented-user",
}).json()
payment = client.post("/api/v1/billing/payments/attempts", json={
    "invoice_id": order["invoice_id"], "idempotency_key": "review-key",
    "amount_uzs": 599000, "actor_user_id": "invented-user",
})
record("payment_without_provider_confirmation", payment.status_code == 200 and
       payment.json().get("status") == "SUCCEEDED", status=payment.status_code,
       payment_status=payment.json().get("status"), provider_called=False)

refund_statuses = []
for _ in range(2):
    res = client.post("/api/v1/billing/refunds", json={
        "invoice_id": order["invoice_id"], "amount_uzs": 599000, "reason": "Review only",
        "requested_by": "invented-a", "approved_by": "invented-b", "second_approver_id": "invented-c",
    })
    refund_statuses.append(res.status_code)
record("refund_total_exceeds_payment", refund_statuses == [201, 201],
       statuses=refund_statuses, invoice_amount=599000, approved_total=1198000)

other_order = client.post("/api/v1/billing/orders", json={
    "organization_id": "review-org-other", "plan_code": "SINGLE_POST_30D", "created_by": "invented-user",
}).json()
replay = client.post("/api/v1/billing/payments/attempts", json={
    "invoice_id": other_order["invoice_id"], "idempotency_key": "review-key",
    "amount_uzs": 1, "currency_code": "USD", "actor_user_id": "invented-other-user",
})
record("idempotency_key_ignores_payload", replay.status_code == 200 and
       replay.json().get("invoice_id") != other_order["invoice_id"],
       status=replay.status_code, returned_old_invoice=replay.json().get("invoice_id") == order["invoice_id"])

eid = payment.json()["entitlement_id"]
billing_service._entitlements[eid] = dataclasses.replace(
    billing_service._entitlements[eid], valid_until=datetime.now(timezone.utc) - timedelta(days=1))
expired = client.post("/api/v1/billing/slots/publish", json={
    "organization_id": "review-org", "opportunity_id": "invented-opportunity", "actor_user_id": "invented-user",
})
record("expired_entitlement_publish", expired.status_code == 200,
       status=expired.status_code, setup="service fixture: valid_until yesterday")

revision_statuses = []
for i in range(6):
    res = client.post("/api/v1/opportunities/revisions", json={
        "organization_id": "review-unpaid-org", "title": f"Review {i}", "hourly_pay": 10000,
    })
    revision_statuses.append(res.status_code)
published_count = sum(o["organization_id"] == "review-unpaid-org" and o["status"] == "PUBLISHED"
                      for o in opportunity_service.opportunities.values())
record("publish_bypasses_quota_and_contract_required", revision_statuses == [201] * 6 and published_count == 6,
       statuses=revision_statuses, published_count=published_count, entitlement=False, contract_type_supplied=False)

upload = client.post("/api/v1/files/upload-init", json={"owner_id": "review-owner", "filename": "review.pdf"}).json()
fid = upload["id"]
bad = client.post(f"/api/v1/files/{fid}/complete-scan", json={"content_sample": "/JavaScript"})
clean = client.post(f"/api/v1/files/{fid}/complete-scan", json={"content_sample": "not even a PDF"})
record("client_can_clear_quarantine", bad.json().get("scan_status") == "QUARANTINED" and
       clean.json().get("scan_status") == "CLEAN", before=bad.json().get("scan_status"),
       after=clean.json().get("scan_status"), object_uploaded=False)
download = client.get(f"/api/v1/files/{fid}/download", params={"requester_id": "unrelated-user"})
record("unrelated_user_receives_private_url", download.status_code == 200,
       status=download.status_code, owner_equals_requester=False, authorization_header=False)

operations_service.circuit_breaker.trip(actor_id="review", incident_id="review-p1", reason_code="REVIEW", details="local fixture")
post_trip_order = client.post("/api/v1/billing/orders", json={
    "organization_id": "review-org", "plan_code": "ORG_PLAN_30D", "created_by": "review",
})
record("operations_breaker_does_not_freeze_billing", post_trip_order.status_code == 201,
       status=post_trip_order.status_code, operations_state=operations_service.circuit_breaker.state,
       billing_state=billing_service.circuit_breaker.state)
operations_service.circuit_breaker.reset(actor_id="review-a", second_approver_id="review-b", resolution_note="fixture reset")
billing_service.circuit_breaker.trip(actor_id="review", incident_id="review-p1", reason_code="REVIEW", details="local fixture")
ready = client.get("/api/v1/operations/pilot-readiness")
blocked_order = client.post("/api/v1/billing/orders", json={
    "organization_id": "review-org", "plan_code": "ORG_PLAN_30D", "created_by": "review",
})
record("pilot_ready_while_billing_frozen", ready.json().get("pilot_ready") is True,
       pilot_ready=ready.json().get("pilot_ready"), billing_state=billing_service.circuit_breaker.state)
record("circuit_open_returns_500_instead_of_503", blocked_order.status_code == 500, status=blocked_order.status_code)

diary_response = client.post("/api/v1/internship-logs/daily-logs", json={
    "placement_id": "nonexistent", "author_id": "invented", "log_date": "2026-11-07",
    "summary_text": "Review", "total_minutes": -1,
})
log = diary_response.json()
record("negative_minutes_submitted", diary_response.status_code == 201 and log["status"] == "SUBMITTED",
       http_status=diary_response.status_code, status=log["status"],
       total_minutes=internship_log_service.log_revisions[log["current_revision_id"]]["total_minutes"])

availability = CandidateAvailabilityService()
for start, end in [(540, 720), (720, 900)]:
    availability.add_availability_rule(candidate_id="review", weekday=1, start_minute=start, end_minute=end)
covered = availability.is_candidate_available_for_shift(candidate_id="review", weekday=1, start_minute=540, end_minute=900)
record("adjacent_availability_not_combined", not covered, covered=covered, intervals=[[540, 720], [720, 900]], shift=[540, 900])

digest = hash_password("Review-only-1357!", salt="fixed-review-salt")
pbkdf = hashlib.pbkdf2_hmac("sha256", b"Review-only-1357!", b"fixed-review-salt", 120000).hex()
record("pbkdf2_labeled_argon2id", digest == f"argon2id_v1$fixed-review-salt${pbkdf}", actual_algorithm="PBKDF2-HMAC-SHA256", declared_prefix=digest.split("$")[0])

child_code = """from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
u=c.post('/api/v1/auth/register',json={'display_name':'Worker fixture','password':'Review-only-1357!','adult_confirmed':True}).json()
s=c.post('/api/v1/auth/login',json={'user_id':u['id'],'password':'Review-only-1357!'}).json()
print(s['session_id'])
"""
env = dict(os.environ, PYTHONPATH=str(ROOT / "backend"))
child = subprocess.run([sys.executable, "-c", child_code], cwd=ROOT / "backend", env=env, capture_output=True, text=True, check=True)
worker_token = child.stdout.strip()
worker_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {worker_token}"})
record("session_not_shared_across_processes", worker_me.status_code == 401,
       status_in_second_process=worker_me.status_code, first_process_created_session=True)

model = json.loads((ROOT / "specs/v1_4/FlexBridge_model_1_4.json").read_text(encoding="utf-8"))
normalize = lambda path: re.sub(r"\{[^}]+\}", "{}", path)
routes = {(method.upper(), normalize(path)) for path, operations in app.openapi()["paths"].items()
          for method in operations if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}}
contracts = model["apis"] + model["helper_apis"]
matched = [a["id"] for a in contracts if (a["method"], normalize(a["path"])) in routes]
critical = [a for a in contracts if a["id"] in {"API-003", "API-060", "API-061"}]
missing = [{"id": a["id"], "method": a["method"], "path": a["path"]} for a in critical
           if (a["method"], normalize(a["path"])) not in routes]
record("canonical_critical_contracts_absent", len(missing) == 3, missing=missing,
       structural_route_matches=len(matched), canonical_contracts=len(contracts), matched_ids=matched,
       note="Route signature comparison only; includes later-release contracts and is not feature completion percentage.")

report = {"review": "REV-001", "generated_at": datetime.now(timezone.utc).isoformat(),
          "environment": "local TestClient / service fixtures, no external integrations",
          "probes": len(results), "defects_observed": sum(r["defect_observed"] for r in results), "results": results}
out = Path(__file__).with_name("probe_results.json")
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))
if not all(r["defect_observed"] for r in results):
    sys.exit(1)
