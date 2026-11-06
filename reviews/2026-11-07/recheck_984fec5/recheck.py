"""REV-002: independent local verification of commit 984fec5.

Run from repository root: python reviews/2026-11-07/recheck_984fec5/recheck.py
Uses a new isolated SQLite file per execution; no external calls or application edits.
"""
from __future__ import annotations

import importlib.util
import dataclasses
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
scratch = ROOT / "backend/.data" / f"rev002_{uuid4().hex}.sqlite3"
os.environ["FLEXBRIDGE_DATABASE_URL"] = "sqlite:///" + scratch.as_posix()
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from argon2 import PasswordHasher
from argon2.low_level import Type, hash_secret_raw
from app.main import app
from app.api.v1.billing import billing_service
from app.api.v1.operations import operations_service
from app.db.storage import get_engine, get_database_url, sessions_table
from app.services.auth import auth_service, hash_password
from app.services.availability import CandidateAvailabilityService
from app.services.files_quarantine import file_quarantine_service
from app.services.internship_logs import internship_log_service
from app.services.opportunities import OpportunityMatchingService, opportunity_service
from app.services.placements import placement_service

client = TestClient(app, raise_server_exceptions=False)
results = []


def record(name, observed, kind="defect", **evidence):
    results.append({"name": name, "kind": kind, "observed": bool(observed), "evidence": evidence})


def child(code, *, env=None):
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT / "backend",
        env=env or dict(os.environ, PYTHONPATH=str(ROOT / "backend")),
        capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()


def order(org):
    return client.post("/api/v1/billing/orders", json={
        "organization_id": org, "plan_code": "ORG_PLAN_30D", "created_by": "synthetic-actor",
    }).json()


def pay(invoice, key, *, confirmed=False):
    return client.post("/api/v1/billing/payments/attempts", json={
        "invoice_id": invoice, "idempotency_key": key, "amount_uzs": 599000,
        "actor_user_id": "synthetic-actor", "provider_confirmed": confirmed,
    })


reg = client.post("/api/v1/auth/register", json={"display_name": "Review Candidate",
    "password": "Synthetic-Review-987!", "adult_confirmed": True}).json()
login = client.post("/api/v1/auth/login", json={"user_id": reg["id"], "password": "Synthetic-Review-987!"}).json()
headers = {"Authorization": "Bearer " + login["session_id"]}
forbidden = client.post("/api/v1/auth/register", json={"display_name": "Review Admin",
    "password": "Synthetic-Review-987!", "adult_confirmed": True, "roles": ["SUPER_ADMIN"]})
record("super_admin_registration_blocked", forbidden.status_code == 403, kind="improvement", status=forbidden.status_code)

support = client.post("/api/v1/auth/register", json={"display_name": "Review Support",
    "password": "Synthetic-Review-987!", "adult_confirmed": True, "roles": ["SUPPORT"]})
record("canonical_support_role_self_assigned", support.status_code == 201,
       status=support.status_code, assigned_roles=support.json().get("roles"))

o1 = order("review-direct-pay")
confirmed = pay(o1["invoice_id"], "review-direct-pay-key", confirmed=True)
record("client_provider_confirmed_bypasses_payment", confirmed.status_code == 200 and confirmed.json().get("status") == "SUCCEEDED",
       http_status=confirmed.status_code, payment_status=confirmed.json().get("status"), authorization_header=False)

refund_statuses = []
for _ in range(2):
    response = client.post("/api/v1/billing/refunds", json={"invoice_id":o1["invoice_id"],
        "amount_uzs":599000,"reason":"Synthetic regression check", "requested_by":"synthetic-a",
        "approved_by":"synthetic-b","second_approver_id":"synthetic-c"})
    refund_statuses.append(response.status_code)
record("sequential_cumulative_refund_ceiling", refund_statuses == [201,409], kind="improvement", statuses=refund_statuses)

expiry_order = order("review-expiry")
expiry_payment = pay(expiry_order["invoice_id"], "review-expiry-key", confirmed=True).json()
entitlement_id = expiry_payment["entitlement_id"]
billing_service._entitlements[entitlement_id] = dataclasses.replace(billing_service._entitlements[entitlement_id],
    valid_until=datetime.now(timezone.utc)-timedelta(days=1))
expiry_publish = client.post("/api/v1/billing/slots/publish",json={"organization_id":"review-expiry",
    "opportunity_id":"synthetic-expired-opportunity","actor_user_id":"synthetic"})
record("active_but_expired_entitlement_rejected", expiry_publish.status_code==409 and "EXPIRED" in str(expiry_publish.json()),
    kind="improvement",status=expiry_publish.status_code,fixture="ACTIVE entitlement, expiry yesterday")

o2 = order("review-webhook")
pending = pay(o2["invoice_id"], "review-webhook-key")
record("payment_defaults_pending", pending.status_code == 200 and pending.json().get("status") == "PENDING_PROVIDER",
       kind="improvement", status=pending.json().get("status"))
mismatch = client.post("/api/v1/billing/payments/attempts",json={"invoice_id":o2["invoice_id"],
    "idempotency_key":"review-webhook-key","amount_uzs":1,"actor_user_id":"synthetic-actor"})
record("idempotency_payload_mismatch_rejected",mismatch.status_code==409 and "IDEMPOTENCY_CONFLICT" in str(mismatch.json()),
    kind="improvement",status=mismatch.status_code)
callback = client.post("/api/v1/webhooks/payments/PAYME", json={
    "provider_event_id": "review-unsigned", "idempotency_key": "review-webhook-key", "amount_uzs": 599000})
record("webhook_without_signature_activates_tariff", callback.status_code == 200 and callback.json().get("status") == "SUCCEEDED",
       status=callback.status_code, payment_status=callback.json().get("status"), signature_supplied=False)

stub = client.post("/api/v1/operator/refunds/does-not-exist/approve", json={}, headers=headers)
record("candidate_gets_ok_from_nonexistent_refund_approval", stub.status_code == 200 and stub.json().get("status") == "OK",
       status=stub.status_code, response=stub.json(), note="False-success placeholder; no actual refund executed.")

security = client.patch("/api/v1/me/security", json={"enable_totp": True, "step_up_totp_code": "000000"}, headers=headers)
record("fake_step_up_and_no_totp_update", security.status_code == 200 and security.json().get("step_up_verified") is True
       and auth_service._load_user(reg["id"]).get("totp_secret") is None,
       status=security.status_code, claimed_verified=security.json().get("step_up_verified"),
       claimed_totp_enabled=security.json().get("totp_enabled"), persisted_totp_enabled=False)

with get_engine().begin() as conn:
    conn.execute(sessions_table.update().where(sessions_table.c.session_id == login["session_id"]).values(
        expires_at=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()))
expired = client.get("/api/v1/auth/me", headers=headers)
record("expired_session_accepted", expired.status_code == 200, status=expired.status_code, fixture="expiry yesterday in SQL")

up = client.post("/api/v1/files/upload-init", json={"owner_id": "victim-owner", "filename": "private.pdf"}).json()
scan = client.post(f"/api/v1/files/{up['id']}/complete-scan", json={"content_sample": "%PDF-1.7 broken non-PDF body"})
download = client.get(f"/api/v1/files/{up['id']}/download", params={"requester_id": "victim-owner"})
record("invalid_pdf_header_only_clean", scan.json().get("scan_status") == "CLEAN",
       status=scan.status_code, scan_status=scan.json().get("scan_status"), object_uploaded=False)
record("spoofed_owner_query_gets_private_url", download.status_code == 200,
       status=download.status_code, authorization_header=False, requester_id_is_unverified_query=True)

publish_statuses = []
for i in range(5):
    r = client.post("/api/v1/opportunities/revisions", json={"organization_id": "review-no-tariff",
        "title": f"Synthetic role {i}", "contract_type": "LABOR_PART_TIME", "hourly_pay": 10000})
    publish_statuses.append(r.status_code)
actual = sum(o["organization_id"] == "review-no-tariff" and o["status"] == "PUBLISHED"
             for o in opportunity_service.opportunities.values())
record("unpaid_unauthenticated_publishing_still_allowed", publish_statuses == [201]*5 and actual == 5,
       statuses=publish_statuses, published_count=actual, entitlement_exists=False)

placement_service.placements["review-existing-placement"] = {
    "id": "review-existing-placement", "candidate_id": "victim-candidate", "organization_id": "victim-org",
    "status": "PENDING_START_CONFIRMATION", "candidate_confirmed_start_at": None, "org_confirmed_start_at": None}
confirmation_statuses = []
for party in ["CANDIDATE", "ORGANIZATION"]:
    r = client.post("/api/v1/engagements/review-existing-placement/confirmations", json={"party": party}, headers=headers)
    confirmation_statuses.append(r.status_code)
record("unrelated_candidate_confirms_both_parties", placement_service.placements["review-existing-placement"]["status"] == "ACTIVE",
       statuses=confirmation_statuses, result=placement_service.placements["review-existing-placement"]["status"],
       fixture="existing victim placement seeded; request actor is unrelated registered candidate")

zero = client.put("/api/v1/placements/review-existing-placement/logs/2026-11-07", json={
    "day_type": "WORKED", "tasks": [{"minutes": 0}], "total_minutes": 0}, headers=headers)
record("ac040_zero_minute_draft_rejected", zero.status_code == 422, status=zero.status_code, expected_status=200)
victim_log = internship_log_service.save_draft_daily_log_api_054(placement_id="review-existing-placement",
    author_id="victim-candidate", log_date="2026-11-07", summary_text="Synthetic fixture", total_minutes=60)
submit = client.post(f"/api/v1/logs/{victim_log['id']}/submit", headers=headers)
record("unrelated_candidate_submits_victim_log", submit.status_code == 200 and submit.json().get("status") == "SUBMITTED",
       status=submit.status_code, result=submit.json().get("status"))

av = CandidateAvailabilityService()
av.add_availability_rule(candidate_id="schedule-fixture", weekday=1, start_minute=540, end_minute=720)
av.add_availability_rule(candidate_id="schedule-fixture", weekday=1, start_minute=720, end_minute=900)
record("adjacent_intervals_combined", av.is_candidate_available_for_shift(candidate_id="schedule-fixture",
    weekday=1, start_minute=540, end_minute=900), kind="improvement")
matching = OpportunityMatchingService(avail_svc=av)
revision = matching.create_opportunity_revision(organization_id="schedule-org", title="Schedule fixture",
    opportunity_kind="PART_TIME_JOB", contract_type="LABOR_PART_TIME", compensation_type="HOURLY", hourly_pay=10000, published=False)
matching.opportunities[revision["opportunity_id"]]["status"] = "PUBLISHED"
for weekday in [1,2]:
    matching.add_opportunity_shift(revision_id=revision["id"], group_code="ONE_GROUP", weekday=weekday,
        start_minute=540,end_minute=600)
partial = matching.match_candidate_feed_api_003(candidate_id="schedule-fixture", schedule_match_mode="ANY_SHIFT_IN_GROUP")
record("any_still_accepts_incomplete_group", len(partial) == 1,
       matched=len(partial), required_shifts=2, covered_shifts=1, full_group_covered=False)

digest = hash_password("Synthetic-Review-987!", salt="review-fixed-salt")
raw = hash_secret_raw(secret=b"Synthetic-Review-987!", salt=b"review-fixed-salt",
    time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, type=Type.ID)
record("genuine_argon2id_computation", digest.split("$")[-1] == raw.hex(), kind="improvement")
try:
    PasswordHasher().verify(digest, "Synthetic-Review-987!")
    phc_error = None
except Exception as exc:
    phc_error = type(exc).__name__
record("argon2_hash_not_standard_phc_encoding", phc_error is not None, standard_verifier_error=phc_error)

with get_engine().connect() as conn:
    stored = conn.execute(select(sessions_table.c.session_id).where(sessions_table.c.session_id==login["session_id"])).scalar_one()
record("raw_bearer_token_stored_as_primary_key", stored == login["session_id"], raw_token_equals_db_primary_key=True)

operations_service.circuit_breaker.trip(actor_id="review-ops", incident_id="review-p1", reason_code="REVIEW", details="synthetic test")
same_process = client.post("/api/v1/billing/orders", json={"organization_id":"review-breaker", "plan_code":"ORG_PLAN_30D", "created_by":"review"})
record("breaker_503_handler_works", same_process.status_code == 503, kind="improvement", status=same_process.status_code)
before = operations_service.circuit_breaker.state
after_child = child("from app.main import app\nfrom app.core.circuit_breaker import shared_circuit_breaker\nprint(shared_circuit_breaker.state)")
after = operations_service.circuit_breaker.state
record("new_process_import_resets_open_breaker", before == "OPEN" and after_child == "CLOSED" and after == "CLOSED",
       before=before, child_state=after_child, after=after)

child_order = json.loads(child("""import json
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
r=c.post('/api/v1/billing/orders',json={'organization_id':'child-org','plan_code':'ORG_PLAN_30D','created_by':'child-user'})
print(json.dumps(r.json()))
"""))
cross_payment = pay(child_order["invoice_id"], "review-cross-process-key")
record("orders_not_shared_across_processes", cross_payment.status_code == 409 and "not found" in str(cross_payment.json()),
       status=cross_payment.status_code, response=cross_payment.json(), same_sqlite_database=True)

new_login = client.post("/api/v1/auth/login",json={"user_id":reg["id"],"password":"Synthetic-Review-987!"}).json()
revoke = client.post(f"/api/v1/auth/sessions/{new_login['session_id']}/revoke",json={"actor_id":"unverified-outsider"})
revoked_me = client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+new_login["session_id"]})
record("legacy_revoke_endpoint_unauthenticated", revoke.status_code==200 and revoked_me.status_code==401,
       revoke_status=revoke.status_code, subsequent_me=revoked_me.status_code)

env = dict(os.environ, PYTHONPATH=str(ROOT / "backend"), DATABASE_URL="postgresql+psycopg://synthetic@invalid/flexbridge")
env.pop("FLEXBRIDGE_DATABASE_URL",None)
url_scheme = child("from app.db.storage import get_database_url\nprint(get_database_url().split(':',1)[0])",env=env)
record("compose_database_url_ignored", url_scheme=="sqlite", configured_variable="DATABASE_URL", resolved_scheme=url_scheme)
tables = inspect(get_engine()).get_table_names()
record("runtime_schema_not_canonical", tables==["circuit_breaker_state","domain_records","sessions","users"], tables=tables)
missing = [p for p in ["backend/Dockerfile","backend/app/workers/outbox.py","backend/alembic.ini","backend/alembic/env.py"] if not (ROOT/p).exists()]
record("compose_and_alembic_runtime_files_missing",len(missing)==4,missing=missing)

ready = client.get("/api/v1/operations/pilot-readiness")
record("pilot_ready_without_integrations", ready.status_code==200 and ready.json().get("pilot_ready") is True,
       status=ready.status_code,pilot_ready=ready.json().get("pilot_ready"), external_services_started=False)

report = {"review":"REV-002", "commit":"984fec5", "generated_at":datetime.now(timezone.utc).isoformat(),
    "environment":"isolated SQLite + local TestClient / service fixtures; no external services",
    "checks":len(results), "defects_observed":sum(r['kind']=='defect' and r['observed'] for r in results),
    "improvements_confirmed":sum(r['kind']=='improvement' and r['observed'] for r in results),"results":results}
(OUT/'recheck_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
