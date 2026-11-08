"""REV-003: local, independent checks on 1460ab8; unique synthetic DB each run."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
db_path = ROOT / "backend/.data" / f"rev003_{uuid4().hex}.sqlite3"
os.environ["FLEXBRIDGE_DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, str(ROOT / "backend"))

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from app.main import app
from app.api.v1.billing import billing_service
from app.db.storage import get_engine, metadata, sessions_table, save_domain_record, list_domain_records
from app.services.auth import auth_service, hash_password
from app.services.placements import placement_service
from app.services.internship_logs import internship_log_service
from app.core.circuit_breaker import shared_circuit_breaker
from app.workers.outbox import relay_pending_outbox_events

client = TestClient(app, raise_server_exceptions=False)
results = []


def record(name, observed, *, kind="defect", **evidence):
    results.append({"name":name,"kind":kind,"observed":bool(observed),"evidence":evidence})


def child(code, env=None):
    return subprocess.run([sys.executable,"-c",code],cwd=ROOT/"backend",
        env=env or dict(os.environ,PYTHONPATH=str(ROOT/"backend")),
        capture_output=True,text=True,encoding="utf-8",check=True).stdout.strip()


def register(roles=None):
    response=client.post("/api/v1/auth/register",json={"display_name":"Synthetic reviewer",
        "password":"Synthetic-review-642!","adult_confirmed":True,"roles":roles or ["CANDIDATE"]})
    if response.status_code != 201:
        return response,None,{}
    u=response.json()
    login=client.post("/api/v1/auth/login",json={"user_id":u["id"],"password":"Synthetic-review-642!"}).json()
    return response,login,{"Authorization":"Bearer "+login["session_id"]}


def create_order(org):
    return client.post("/api/v1/billing/orders",json={"organization_id":org,"plan_code":"ORG_PLAN_30D",
        "created_by":"synthetic-requester"})


def pending_payment(org,key):
    order=create_order(org).json()
    p=client.post("/api/v1/billing/payments/attempts",json={"invoice_id":order["invoice_id"],
        "idempotency_key":key,"amount_uzs":599000,"actor_user_id":"synthetic-requester",
        "provider_confirmed":True})
    return order,p


support,_,_=register(["SUPPORT"])
record("support_public_registration_blocked",support.status_code==403,kind="improvement",status=support.status_code)
reg,login,headers=register()
user_id=reg.json()["id"]
phc=str(hash_password("Synthetic-review-642!",salt="independent-salt"))
record("standard_phc_verification",PasswordHasher().verify(phc,"Synthetic-review-642!"),kind="improvement")

order,pending=pending_payment("ordinary-org-"+uuid4().hex,"pending-key")
record("client_confirmation_flag_ignored",pending.json().get("status")=="PENDING_PROVIDER",kind="improvement",status=pending.json().get("status"))
unsigned=client.post("/api/v1/webhooks/payments/PAYME",json={"provider_event_id":"unsigned-event",
    "idempotency_key":"pending-key","amount_uzs":599000})
record("missing_signature_rejected",unsigned.status_code==422,kind="improvement",status=unsigned.status_code)
literal=client.post("/api/v1/webhooks/payments/PAYME",json={"provider_event_id":"literal-event",
    "idempotency_key":"pending-key","amount_uzs":599000,"signature":"VALID_PROVIDER_WEBHOOK_SIGNATURE"})
record("public_literal_signature_still_confirms_payment",literal.status_code==200 and literal.json().get("status")=="SUCCEEDED",
    status=literal.status_code,payment_status=literal.json().get("status"),authorization_header=False,real_provider_called=False)

unpaid,unpaid_attempt=pending_payment("unpaid-org-"+uuid4().hex,"unpaid-key")
refund=client.post("/api/v1/billing/refunds",json={"invoice_id":unpaid["invoice_id"],"amount_uzs":599000,
    "reason":"Synthetic review","requested_by":"a","approved_by":"b","second_approver_id":"c"})
record("unpaid_pending_invoice_refunded",unpaid_attempt.json().get("status")=="PENDING_PROVIDER" and refund.status_code==201,
    payment_status=unpaid_attempt.json().get("status"),refund_http_status=refund.status_code,refund_status=refund.json().get("status"),authorization_header=False)

with get_engine().connect() as conn:
    stored_hash=conn.execute(select(sessions_table.c.session_id).where(sessions_table.c.user_id==user_id)).scalar_one()
hash_auth=client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+stored_hash})
record("stored_digest_accepted_as_bearer",hash_auth.status_code==200,status=hash_auth.status_code,stored_value_is_digest=stored_hash.startswith("sha256:"))

owner_up=client.post("/api/v1/files/upload-init",json={"owner_id":user_id,"filename":"renamed.pdf"}).json()
invalid=client.post(f"/api/v1/files/{owner_up['id']}/complete-scan",json={"content_sample":"%PDF-1.7\nthis has no PDF objects or trailer"})
record("renamed_invalid_pdf_still_clean",invalid.json().get("scan_status")=="CLEAN",scan_status=invalid.json().get("scan_status"),object_uploaded=False)
no_auth_download=client.get(f"/api/v1/files/{owner_up['id']}/download",params={"requester_id":user_id})
record("download_now_requires_auth",no_auth_download.status_code==401,kind="improvement",status=no_auth_download.status_code)

placement_id="victim-placement-"+uuid4().hex
placement_service.placements[placement_id]={"id":placement_id,"candidate_id":"victim-person",
    "organization_id":"unrelated-company","status":"PENDING_START_CONFIRMATION",
    "candidate_confirmed_start_at":None,"org_confirmed_start_at":None}
employer,employer_login,employer_headers=register(["EMPLOYER"])
cross_org=client.post(f"/api/v1/engagements/{placement_id}/confirmations",json={"party":"ORGANIZATION"},headers=employer_headers)
record("public_employer_confirms_unrelated_company",employer.status_code==201 and cross_org.status_code==200,
    register_status=employer.status_code,confirm_status=cross_org.status_code,org_membership_created=False)
draft=client.put(f"/api/v1/placements/{placement_id}/logs/2026-11-07",json={"total_minutes":60,"summary_text":"Synthetic"},headers=headers)
draft_result=draft.json()
submit=client.post(f"/api/v1/logs/{draft_result.get('id','missing')}/submit",headers=headers)
record("unrelated_user_creates_and_submits_victim_placement_log",draft.status_code==200 and submit.status_code==200,
    draft_status=draft.status_code,submit_status=submit.status_code,result=submit.json().get("status"),actor_is_placement_candidate=False)
legacy_statuses=[]
for party in ["CANDIDATE","ORGANIZATION"]:
    r=client.post(f"/api/v1/placements/{placement_id}/confirm-start",json={"party":party})
    legacy_statuses.append(r.status_code)
record("legacy_confirm_start_bypasses_auth",legacy_statuses==[200,200] and placement_service.placements[placement_id]["status"]=="ACTIVE",
    statuses=legacy_statuses,result=placement_service.placements[placement_id]["status"])

with get_engine().begin() as conn:
    conn.execute(sessions_table.update().where(sessions_table.c.session_id==login["session_id"]).values(
        expires_at=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()))
expired_me=client.get("/api/v1/auth/me",headers=headers)
expired_security=client.patch("/api/v1/me/security",json={"enable_totp":False,"current_password":"Synthetic-review-642!"},headers=headers)
record("auth_me_checks_expiry",expired_me.status_code==401,kind="improvement",status=expired_me.status_code)
record("dependency_accepts_same_expired_session",expired_me.status_code==401 and expired_security.status_code==200,
    me_status=expired_me.status_code,protected_write_status=expired_security.status_code,step_up_verified=expired_security.json().get("step_up_verified"))

shared_circuit_breaker.trip(actor_id="synthetic-ops",incident_id="synthetic-p1",reason_code="TEST",details="Synthetic fixture")
new_process_state=child("from app.main import app\nfrom app.core.circuit_breaker import shared_circuit_breaker\nprint(shared_circuit_breaker.state)")
record("new_process_preserves_open_breaker",new_process_state=="OPEN" and shared_circuit_breaker.state=="OPEN",kind="improvement",child_state=new_process_state)
before_count=len(list_domain_records("orders"))
blocked=create_order("ordinary-blocked-"+uuid4().hex)
after_count=len(list_domain_records("orders"))
record("blocked_order_still_writes_before_503",blocked.status_code==503 and after_count==before_count+1,
    http_status=blocked.status_code,order_count_delta=after_count-before_count,invoice_id_leaked_in_error="invoice_id" in blocked.json())
special=create_order("child-org")
record("special_org_id_resets_finance_breaker",special.status_code==201 and shared_circuit_breaker.state=="CLOSED",
    status=special.status_code,after_state=shared_circuit_breaker.state,authorization_header=False,special_input="child-org")

engine=get_engine()
inspector=inspect(engine)
pa=metadata.tables["payment_attempts"]
now=datetime.now(timezone.utc).isoformat()
with engine.begin() as conn:
    conn.execute(pa.insert().values(id=uuid4().hex,created_at=now,updated_at=now,order_id="missing-order",
        provider="SYNTHETIC",provider_transaction_id=None,amount="-1",currency="XXX",status="CAPTURED",
        requested_at=now,confirmed_at=None))
record("canonical_named_table_has_no_invariants",not inspector.get_foreign_keys("payment_attempts") and not inspector.get_check_constraints("payment_attempts"),
    runtime_table_count=len(inspector.get_table_names()),foreign_keys=len(inspector.get_foreign_keys("payment_attempts")),
    check_constraints=len(inspector.get_check_constraints("payment_attempts")),negative_orphan_payment_inserted=True,
    amount_column_type=str(next(c['type'] for c in inspector.get_columns('payment_attempts') if c['name']=='amount')))

parent_order,parent_attempt=pending_payment("payment-process-"+uuid4().hex,"cross-process-payment-key")
child_callback=json.loads(child("""import json
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
r=c.post('/api/v1/webhooks/payments/PAYME',json={'provider_event_id':'cross-event','idempotency_key':'cross-process-payment-key','amount_uzs':599000,'signature':'VALID_PROVIDER_WEBHOOK_SIGNATURE'})
print(json.dumps({'status':r.status_code,'body':r.json()}))
"""))
record("payment_attempt_not_shared_across_workers",child_callback["status"]==409 and "not found" in str(child_callback["body"]),
    child_status=child_callback["status"],response=child_callback["body"],same_database=True)

for i in range(51):
    save_domain_record("outbox_events",f"synthetic-{i:03d}",{"id":f"synthetic-{i:03d}","status":"RELAYED" if i<50 else "PENDING"})
relay_counts=[relay_pending_outbox_events(50),relay_pending_outbox_events(50)]
tail=next(x for x in list_domain_records("outbox_events") if x['id']=='synthetic-050')
record("outbox_starves_pending_after_first_batch",relay_counts==[0,0] and tail['status']=='PENDING',
    relay_counts=relay_counts,pending_tail_status=tail['status'],fixture="first 50 records already RELAYED; record 51 PENDING")

migration_path=ROOT/"backend/.data"/f"rev003_migration_{uuid4().hex}.sqlite3"
migration_env=dict(os.environ,FLEXBRIDGE_DATABASE_URL="sqlite:///"+migration_path.as_posix())
migration=subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT/"backend",env=migration_env,
    capture_output=True,text=True,encoding="utf-8")
record("alembic_success_without_applying_migrations",migration.returncode==0 and not migration_path.exists(),
    exit_code=migration.returncode,database_created=migration_path.exists(),stdout=migration.stdout,stderr=migration.stderr)

record("container_driver_and_specs_not_packaged",
    "psycopg" not in (ROOT/"backend/Dockerfile").read_text() and not (ROOT/"backend/specs").exists(),
    dockerfile_installs_psycopg=False,backend_build_context_contains_specs=False,
    note="Static build-context/dependency check, not an actual Docker build.")

report={"review":"REV-003","commit":"1460ab8","generated_at":datetime.now(timezone.utc).isoformat(),
    "environment":"new isolated SQLite, TestClient, child processes; no external integrations",
    "checks":len(results),"improvements_confirmed":sum(x['kind']=='improvement' and x['observed'] for x in results),
    "defect_scenarios_observed":sum(x['kind']=='defect' and x['observed'] for x in results),"results":results}
(OUT/"results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
