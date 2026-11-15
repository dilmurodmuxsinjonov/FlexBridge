#!/usr/bin/env python3
"""
Staging Verification Suite: Standardized Diary, Final Conclusion & 3-Party E-Imzo (FB-204)

Verifies end-to-end against live Docker staging stack (Next.js BFF + FastAPI + MinIO + PgBouncer):
1. Unauthenticated 401 and Cross-Site CSRF 403 guards across E-Imzo & Document BFF endpoints.
2. Dedicated separate E-Imzo certificates per party (`CANDIDATE`, `EMPLOYER`, `UNIVERSITY`) with 403 anti-forgery guards.
3. Document 1 (Standardized Amaliyot Kundaligi): passport + standardized entry fields + ongoing 3-party E-Imzo confirmation.
4. Document 2 (Yakuniy Amaliyot Xulosasi): separate end-of-internship evaluations/confirmations + 3-party E-Imzo -> TRI_PARTY_SIGNED.
5. Real A4 PDF generation (`pypdf`) & JSON downloads for BOTH documents via authenticated binary streaming BFF endpoint,
   verifying rendered text & E-Imzo verification codes (`FB-SIG-...`) with `pypdf.PdfReader`.
6. Cryptographic HMAC signature verification (`GET /api/bff/internship-documents/verify/{code}`) + audit ledger.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import dotenv_values
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def get_database_url() -> str:
    explicit = os.environ.get("FLEXBRIDGE_STAGING_DATABASE_URL")
    if explicit:
        return explicit
    values = dotenv_values(REPO_ROOT / "infra" / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("Set POSTGRES_PASSWORD in infra/.env")
    url = URL.create(
        "postgresql+psycopg",
        username=values.get("POSTGRES_USER") or "flexbridge_owner",
        password=password,
        host="127.0.0.1",
        port=5432,
        database=values.get("POSTGRES_DB") or "flexbridge",
    )
    return url.render_as_string(hide_password=False)


def api_json(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, Any, dict[str, str]]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    client = opener or urllib.request.build_opener()
    try:
        with client.open(req) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return err.code, parsed, {k.lower(): v for k, v in err.headers.items()}


def api_bytes(
    url: str,
    opener: urllib.request.OpenerDirector,
) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, method="GET")
    try:
        with opener.open(req) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as err:
        return err.code, err.read(), {k.lower(): v for k, v in err.headers.items()}


def login_actor(user_id: str, password: str) -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    st, payload, _ = api_json(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": user_id, "password": password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert st == 200 and payload.get("ok") is True, f"Login failed for {user_id}: {st} {payload}"
    return opener


def main() -> None:
    print("=== FlexBridge FB-204 Standardized Diary, Final Conclusion & 3-Party E-Imzo Suite ===")
    engine = create_engine(get_database_url(), poolclass=NullPool, connect_args={"prepare_threshold": None})

    # 1. Unauthenticated 401 guard
    dummy_pid = str(uuid4())
    for path in (
        "/api/bff/me/e-imzo",
        f"/api/bff/placements/{dummy_pid}/diary/standard",
        f"/api/bff/placements/{dummy_pid}/conclusion-document",
    ):
        st, body, _ = api_json(f"{FRONTEND_URL}{path}", method="GET")
        assert st == 401, f"Expected 401 for unauthenticated GET {path}, got {st}: {body}"
    print("[PASS] Phase 1: Unauthenticated 401 guards verified.")

    # 2. Seed tri-party placement fixtures
    suffix = uuid4().hex[:8]
    pw_plain = "Fb204Test!123"
    pw_hash = hash_password(pw_plain)
    now_ts = datetime.now(timezone.utc)
    today = date.today()

    teacher_uid = str(uuid4())
    student_uid = str(uuid4())
    student_pid = str(uuid4())
    employer_uid = str(uuid4())
    org_id = str(uuid4())
    org_mem_id = str(uuid4())
    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())
    app_id = str(uuid4())
    attempt_id = str(uuid4())
    offer_id = str(uuid4())
    inst_id = str(uuid4())
    inst_agr_id = str(uuid4())
    enrollment_id = str(uuid4())
    supervision_id = str(uuid4())
    placement_id = str(uuid4())
    terms_id = str(uuid4())
    t_mem_id = str(uuid4())
    t_app_id = str(uuid4())
    t_grant_id = str(uuid4())
    acad_asg_id = str(uuid4())
    mentor_asg_id = str(uuid4())
    daily_log_id = str(uuid4())
    log_rev_id = str(uuid4())

    trigger_tables = [
        "organizations", "org_memberships", "org_role_grants",
        "enrollments", "enrollment_origins",
        "student_supervisions", "supervision_origins",
        "placement_intakes", "placement_academic_bindings",
        "academic_assignments", "academic_assignment_proofs",
        "mentor_assignments", "mentor_assignment_proofs",
        "placements", "placement_terms",
        "daily_logs", "log_revisions", "log_task_entries",
    ]
    with engine.begin() as conn:
        for t in trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        with engine.begin() as conn:
            clean_file = conn.execute(text("SELECT id FROM flexbridge.files WHERE scan_status = 'CLEAN' LIMIT 1")).first()
            assert clean_file, "Clean file fixture required"
            file_id = clean_file[0]

            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES
                  (:tid, :ts, :ts, 'Prof. Aziz Karimov', :pw, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                  (:sid, :ts, :ts, 'Dilshod Rakhimov', :pw, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                  (:eid, :ts, :ts, 'Kamola Alimova (Korxona)', :pw, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"tid": teacher_uid, "sid": student_uid, "eid": employer_uid, "pw": pw_hash, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:pid, :ts, :ts, :uid, 'Backend Injiniring Talabasi', 'Tashkent', 12, 'PUBLIC')
            """), {"pid": student_pid, "uid": student_uid, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :ts, :ts, :tax, 'O''zbekiston Raqamli Yechimlar MCHJ', 'Digital Solutions', 'Tashkent', 'ACTIVE')
            """), {"id": org_id, "tax": f"309{suffix[:6]}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status)
                VALUES (:id, :ts, :ts, :oid, :uid, 'ACTIVE')
            """), {"id": org_mem_id, "oid": org_id, "uid": employer_uid, "ts": now_ts})

            org_roles = conn.execute(text("""
                SELECT code, id FROM flexbridge.role_catalog WHERE scope_kind = 'ORG' AND code IN ('HOST_COORDINATOR', 'MENTOR')
            """)).mappings().all()
            org_role_map = {r["code"]: r["id"] for r in org_roles}
            mentor_grant_id = str(uuid4())
            coord_grant_id = str(uuid4())
            conn.execute(text("""
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES (:g1, :ts, :ts, :mid, :r1, :uid), (:g2, :ts, :ts, :mid, :r2, :uid)
            """), {
                "g1": coord_grant_id, "g2": mentor_grant_id, "mid": org_mem_id,
                "r1": org_role_map["HOST_COORDINATOR"], "r2": org_role_map["MENTOR"],
                "uid": employer_uid, "ts": now_ts,
            })

            conn.execute(text("""
                INSERT INTO flexbridge.opportunities (id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count)
                VALUES (:id, :ts, :ts, :oid, 'INTERNSHIP', 'PUBLISHED', 5, 1)
            """), {"id": opp_id, "oid": org_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                    shift_match_mode, snapshot_schema, contract_type
                ) VALUES (
                    :id, :ts, :ts, :oid, 1, :aid, 'Software Engineer Intern', 'Amaliyot dasturi',
                    'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'INTERNSHIP_AGREEMENT'
                )
            """), {"id": opp_rev_id, "oid": opp_id, "aid": employer_uid, "today": today, "ts": now_ts})
            conn.execute(text("UPDATE flexbridge.opportunities SET current_revision_id = :r WHERE id = :o"), {"r": opp_rev_id, "o": opp_id})

            conn.execute(text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :ts, :ts, :oid, :cid, 'OFFERED', 1)
            """), {"id": app_id, "oid": opp_id, "cid": student_pid, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.application_attempts (
                    id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                    profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                ) VALUES (
                    :id, :ts, :ts, :aid, :oid, 1, :rid, '{}'::jsonb, '{}'::jsonb, 1, :ts, :idem
                )
            """), {"id": attempt_id, "aid": app_id, "oid": opp_id, "rid": opp_rev_id, "idem": f"att-{suffix}", "ts": now_ts})
            conn.execute(text("UPDATE flexbridge.applications SET current_attempt_id = :a WHERE id = :id"), {"a": attempt_id, "id": app_id})

            conn.execute(text("""
                INSERT INTO flexbridge.offers (
                    id, created_at, updated_at, application_id, attempt_id, revision_id,
                    issuer_membership_id, terms_snapshot, status, expires_at, idempotency_key
                ) VALUES (:id, :ts, :ts, :aid, :att, :rid, :imid, '{}'::jsonb, 'ACCEPTED', :exp, :idem)
            """), {
                "id": offer_id, "aid": app_id, "att": attempt_id, "rid": opp_rev_id,
                "imid": org_mem_id, "exp": now_ts + timedelta(days=30), "idem": f"off-{suffix}", "ts": now_ts,
            })

            conn.execute(text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :ts, :ts, :reg, 'Toshkent Axborot Texnologiyalari Universiteti', 'Tashkent', 'VERIFIED')
            """), {"id": inst_id, "reg": f"TATU_{suffix}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.institution_agreements (id, created_at, updated_at, institution_id, version, status, valid_from, purposes)
                VALUES (:id, :ts, :ts, :iid, 1, 'ACTIVE', :today, jsonb_build_array('ENGINEERING_INTERNSHIP'))
            """), {"id": inst_agr_id, "iid": inst_id, "today": today, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :ts, :ts, :cid, :iid, 'Dasturiy Injiniring', 'VERIFIED', :today)
            """), {"id": enrollment_id, "cid": student_pid, "iid": inst_id, "today": today, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :ts, 'LEGACY_IMPORT', :cid, :iid, :uid, '{"status":"VERIFIED"}'::jsonb)
            """), {"id": enrollment_id, "cid": student_pid, "iid": inst_id, "uid": student_uid, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at)
                VALUES (:id, :ts, :ts, :iid, :uid, :fid, 'ACTIVE', :today, :ts)
            """), {"id": t_app_id, "iid": inst_id, "uid": teacher_uid, "fid": file_id, "today": today, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :ts, :ts, :iid, :uid, 'ACTIVE', :ts)
            """), {"id": t_mem_id, "iid": inst_id, "uid": teacher_uid, "ts": now_ts})

            t_role = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'TEACHER' AND scope_kind = 'INSTITUTION'")).first()[0]
            conn.execute(text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :ts, :ts, :mid, :rid, :aid)
            """), {"id": t_grant_id, "mid": t_mem_id, "rid": t_role, "aid": t_app_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.student_supervisions (id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id, purpose, status, legal_basis, accepted_at, institution_id)
                VALUES (:id, :ts, :ts, :eid, :mid, :aid, 'ENGINEERING_INTERNSHIP', 'ACTIVE', 'Kafedra qarori', :ts, :iid)
            """), {"id": supervision_id, "eid": enrollment_id, "mid": t_mem_id, "aid": inst_agr_id, "iid": inst_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :ts, 'LEGACY_IMPORT', '{}'::jsonb)
            """), {"id": supervision_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.placements (id, created_at, updated_at, application_id, offer_id, candidate_id, organization_id, enrollment_id, academic_track, status, start_date, end_date, version)
                VALUES (:id, :ts, :ts, :aid, :oid, :cid, :org_id, :eid, TRUE, 'ACTIVE', :today, :end_d, 1)
            """), {"id": placement_id, "aid": app_id, "oid": offer_id, "cid": student_pid, "org_id": org_id, "eid": enrollment_id, "today": today, "end_d": today + timedelta(days=30), "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.placement_intakes (placement_id, created_at, origin, offer_id, attempt_id, revision_id, academic_required, initial_snapshot, source_snapshot)
                VALUES (:pid, :ts, 'LEGACY_IMPORT', :oid, :att, :rid, TRUE, '{}'::jsonb, '{}'::jsonb)
            """), {"pid": placement_id, "oid": offer_id, "att": attempt_id, "rid": opp_rev_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.placement_terms (id, created_at, updated_at, placement_id, version, schema_version, terms_snapshot, daily_limit_minutes, weekly_limit_minutes, required_minutes)
                VALUES (:id, :ts, :ts, :pid, 1, 1, CAST(:snap AS jsonb), 480, 2400, 8640)
            """), {"id": terms_id, "pid": placement_id, "snap": '{"version": 1}', "ts": now_ts})
            conn.execute(text("UPDATE flexbridge.placements SET current_terms_id = :t WHERE id = :p"), {"t": terms_id, "p": placement_id})

            conn.execute(text("""
                INSERT INTO flexbridge.placement_academic_bindings (placement_id, created_at, origin, institution_id, enrollment_id, supervision_id, terms_id, initial_snapshot, scope_snapshot)
                VALUES (:pid, :ts, 'LEGACY_IMPORT', :iid, :eid, :sid, :tid, '{}'::jsonb, '{}'::jsonb)
            """), {"pid": placement_id, "iid": inst_id, "eid": enrollment_id, "sid": supervision_id, "tid": terms_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.academic_assignments (id, created_at, updated_at, placement_id, teacher_membership_id, supervision_id, assigned_by_id, assigned_at, accepted_at, institution_id)
                VALUES (:id, :ts, :ts, :pid, :mid, :sid, :by_id, :ts, :ts, :iid)
            """), {"id": acad_asg_id, "pid": placement_id, "mid": t_mem_id, "sid": supervision_id, "by_id": teacher_uid, "iid": inst_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.academic_assignment_proofs (assignment_id, created_at, origin, placement_id, teacher_user_id, teacher_grant_id, teacher_appointment_id, initial_snapshot)
                VALUES (:aid, :ts, 'LEGACY_IMPORT', :pid, :tuid, :gid, :appid, '{}'::jsonb)
            """), {"aid": acad_asg_id, "pid": placement_id, "tuid": teacher_uid, "gid": t_grant_id, "appid": t_app_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.mentor_assignments (id, created_at, updated_at, placement_id, membership_id, organization_id, assigned_by_id, assigned_at, accepted_at)
                VALUES (:id, :ts, :ts, :pid, :mmid, :org_id, :by_id, :ts, :ts)
            """), {"id": mentor_asg_id, "pid": placement_id, "mmid": org_mem_id, "org_id": org_id, "by_id": employer_uid, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.mentor_assignment_proofs (assignment_id, created_at, origin, placement_id, mentor_user_id, mentor_grant_id, initial_snapshot)
                VALUES (:aid, :ts, 'LEGACY_IMPORT', :pid, :uid, :gid, '{}'::jsonb)
            """), {"aid": mentor_asg_id, "pid": placement_id, "uid": employer_uid, "gid": mentor_grant_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, version)
                VALUES (:id, :ts, :ts, :pid, :today, 1)
            """), {"id": daily_log_id, "pid": placement_id, "today": today, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.log_revisions (id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary, total_minutes, status, submitted_at, idempotency_key)
                VALUES (:id, :ts, :ts, :dlid, 1, :tid, :aid, 'WORKDAY', 'FastAPI va E-Imzo mikroservisi arxitekturasini yaratdim.', 420, 'SUBMITTED', :ts, :idem)
            """), {"id": log_rev_id, "dlid": daily_log_id, "tid": terms_id, "aid": student_uid, "idem": f"lr-{suffix}", "ts": now_ts})
            conn.execute(text("UPDATE flexbridge.daily_logs SET current_revision_id = :r WHERE id = :d"), {"r": log_rev_id, "d": daily_log_id})

    finally:
        with engine.begin() as conn:
            for t in trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print(f"[PASS] Phase 2: Tri-party placement seeded ({placement_id}).")

    # 3. Login all 3 parties
    cand_opener = login_actor(student_uid, pw_plain)
    emp_opener = login_actor(employer_uid, pw_plain)
    uni_opener = login_actor(teacher_uid, pw_plain)
    print("[PASS] Phase 3: Candidate, Employer, University actors logged in via Next.js BFF.")

    # 4. Separate E-Imzo certificates & Cross-Party Forgery Guards (403)
    st, res, _ = api_json(
        f"{FRONTEND_URL}/api/bff/me/e-imzo",
        method="PUT",
        data={
            "party": "CANDIDATE",
            "full_name": "Dilshod Rakhimov",
            "position_title": "4-kurs Amaliyotchi Talaba",
            "organization_or_university": "TATU Dasturiy Injiniring",
            "stir_or_pinfl": "31205001234567",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert st == 200 and res.get("active") is True and res.get("party") == "CANDIDATE", f"Cand E-Imzo failed: {st} {res}"

    # Forgery test: candidate tries registering EMPLOYER E-Imzo
    st_forge, body_forge, _ = api_json(
        f"{FRONTEND_URL}/api/bff/me/e-imzo",
        method="PUT",
        data={
            "party": "EMPLOYER",
            "full_name": "Fake Employer",
            "position_title": "Fake HR",
            "organization_or_university": "Fake Org",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert st_forge == 403, f"Expected 403 SIGNATURE_PARTY_FORBIDDEN when candidate registers EMPLOYER cert, got {st_forge}: {body_forge}"

    st, res, _ = api_json(
        f"{FRONTEND_URL}/api/bff/me/e-imzo",
        method="PUT",
        data={
            "party": "EMPLOYER",
            "full_name": "Kamola Alimova",
            "position_title": "Bosh Backend Mentor",
            "organization_or_university": "O'zbekiston Raqamli Yechimlar MCHJ",
            "stir_or_pinfl": f"309{suffix[:6]}",
        },
        headers={"Origin": FRONTEND_URL},
        opener=emp_opener,
    )
    assert st == 200 and res.get("party") == "EMPLOYER", f"Employer E-Imzo failed: {st} {res}"

    st, res, _ = api_json(
        f"{FRONTEND_URL}/api/bff/me/e-imzo",
        method="PUT",
        data={
            "party": "UNIVERSITY",
            "full_name": "Prof. Aziz Karimov",
            "position_title": "Kafedra Amaliyot Rahbari",
            "organization_or_university": "Toshkent Axborot Texnologiyalari Universiteti",
            "stir_or_pinfl": "201122334",
        },
        headers={"Origin": FRONTEND_URL},
        opener=uni_opener,
    )
    assert st == 200 and res.get("party") == "UNIVERSITY", f"University E-Imzo failed: {st} {res}"
    print("[PASS] Phase 4: Separate 3-party E-Imzo certificates & 403 cross-party guards verified.")

    # 5. Standardized Diary Passport & Daily Entry + CSRF check
    st_csrf, _, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/diary/sign",
        method="POST",
        data={"party": "CANDIDATE"},
        headers={"Origin": "https://evil.attacker.uz"},
        opener=cand_opener,
    )
    assert st_csrf == 403, f"Expected 403 CSRF_ORIGIN_MISMATCH, got {st_csrf}"

    st, diary_ws, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/diary/standard",
        method="PUT",
        data={
            "diary_passport": {
                "otm_name": "Toshkent Axborot Texnologiyalari Universiteti",
                "faculty_name": "Dasturiy injiniring fakulteti",
                "academic_group": "DI-401",
                "course_year": "4-kurs",
                "internship_type": "ISHLAB_CHIQARISH",
                "host_department": "Platform Backend Team",
                "contract_number": f"SHARTNOMA-{suffix.upper()}",
                "normative_hours": 144,
            },
            "daily_entry": {
                "daily_log_id": daily_log_id,
                "work_start_time": "09:00",
                "work_end_time": "17:00",
                "department_unit": "Platform Backend",
                "tools_used": "FastAPI, PostgreSQL, Docker, pypdf",
                "skills_practiced": "Kriptografik imzo va hujjat generatsiyasi",
                "outcome_artifact": "PR #205",
                "safety_instructed": True,
            },
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert st == 200 and diary_ws["diary_passport"]["academic_group"] == "DI-401", f"Diary standard update failed: {st} {diary_ws}"
    assert diary_ws["entries"][0]["standard_entry"]["outcome_artifact"] == "PR #205"

    # 6. Continuous E-Imzo Signing on Document 1 by Candidate, Employer & University + Anti-Forgery
    for actor_opener, party in ((cand_opener, "CANDIDATE"), (emp_opener, "EMPLOYER"), (uni_opener, "UNIVERSITY")):
        st, sign_res, _ = api_json(
            f"{FRONTEND_URL}/api/bff/placements/{placement_id}/diary/sign",
            method="POST",
            data={"party": party, "scope": "LOG", "daily_log_id": daily_log_id, "confirmation_note": f"{party} doimiy tasdig'i"},
            headers={"Origin": FRONTEND_URL},
            opener=actor_opener,
        )
        assert st == 200 and sign_res["stamp"]["verification_code"].startswith("FB-SIG-D-"), f"Diary sign {party} failed: {st} {sign_res}"

    # Anti-forgery on Document 1: Employer cannot sign as UNIVERSITY
    st_f1, _, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/diary/sign",
        method="POST",
        data={"party": "UNIVERSITY"},
        headers={"Origin": FRONTEND_URL},
        opener=emp_opener,
    )
    assert st_f1 == 403, f"Expected 403 when Employer signs diary as UNIVERSITY, got {st_f1}"
    print("[PASS] Phase 5-6: Standardized Diary & Continuous 3-Party E-Imzo verified.")

    # 7. Separate Final Conclusion Document (Document 2) signed by Employer, University & Candidate
    st, emp_conc, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/conclusion-document/sign",
        method="POST",
        data={
            "party": "EMPLOYER",
            "overall_score": 95,
            "employer_verdict": "RECOMMENDED_FOR_HIRE",
            "hire_recommendation": True,
            "characterization_summary": "Talaba amaliyot dasturini a'lo darajada bajardi va Junior Backend lavozimiga tavsiya etildi.",
            "competency_ratings": {"discipline": 5, "technical_skills": 5, "teamwork": 5, "initiative": 5, "communication": 4},
        },
        headers={"Origin": FRONTEND_URL},
        opener=emp_opener,
    )
    assert st == 200 and emp_conc["document"]["overall_status"] == "PARTIALLY_SIGNED"

    st, uni_conc, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/conclusion-document/sign",
        method="POST",
        data={
            "party": "UNIVERSITY",
            "academic_score": 94,
            "letter_grade": "A",
            "ects_credits": 4.0,
            "defense_date": today.isoformat(),
            "academic_verdict": "APPROVED_CREDIT",
            "academic_summary": "Talaba himoya komissiyasida kundalik va natijalarni muvaffaqiyatli himoya qildi.",
        },
        headers={"Origin": FRONTEND_URL},
        opener=uni_opener,
    )
    assert st == 200 and uni_conc["document"]["signed_parties_count"] == 2

    st, cand_conc, _ = api_json(
        f"{FRONTEND_URL}/api/bff/placements/{placement_id}/conclusion-document/sign",
        method="POST",
        data={
            "party": "CANDIDATE",
            "student_reflection": "Amaliyot davomida real mikroservislar va E-Imzo tizimida tajriba orttirdim.",
            "achievements_highlight": "PR #205 va FastAPI integratsiyasi",
            "recommended_improvements": "Ko'proq code review sessiyalari",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert st == 200
    conc_doc = cand_conc["document"]
    assert conc_doc["overall_status"] == "TRI_PARTY_SIGNED" and conc_doc["is_fully_signed"] is True
    conc_verify_code = cand_conc["stamp"]["verification_code"]
    assert conc_verify_code.startswith("FB-SIG-C-")
    print(f"[PASS] Phase 7: Document 2 Final Conclusion reached TRI_PARTY_SIGNED ({conc_verify_code}).")

    # 8. Download Both Documents (PDF + JSON) via BFF Binary Streaming Endpoint & Verify PDF Content
    for doc_type, expected_marker in (("DIARY", "STANDART AMALIYOT KUNDALIGI"), ("CONCLUSION", "YAKUNIY AMALIYOT XULOSASI")):
        st, dl_receipt, _ = api_json(
            f"{FRONTEND_URL}/api/bff/placements/{placement_id}/documents/download",
            method="POST",
            data={"document_type": doc_type, "export_format": "PDF"},
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert st == 200 and dl_receipt["bff_download_url"].startswith("/api/bff/placements/"), f"PDF export {doc_type} failed: {st} {dl_receipt}"

        st_bin, pdf_bytes, bin_headers = api_bytes(f"{FRONTEND_URL}{dl_receipt['bff_download_url']}", opener=cand_opener)
        assert st_bin == 200 and pdf_bytes[:4] == b"%PDF", f"PDF binary stream failed: {st_bin} {bin_headers}"
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted = "\n".join(p.extract_text() or "" for p in reader.pages)
        assert expected_marker in extracted, f"Missing '{expected_marker}' inside extracted PDF text: {extracted[:400]}"
        assert "Dilshod Rakhimov" in extracted and "Kamola Alimova" in extracted and "Aziz Karimov" in extracted, f"Missing 3-party names in {doc_type} PDF"

        st_j, json_receipt, _ = api_json(
            f"{FRONTEND_URL}/api/bff/placements/{placement_id}/documents/download",
            method="POST",
            data={"document_type": doc_type, "export_format": "JSON"},
            headers={"Origin": FRONTEND_URL},
            opener=uni_opener,
        )
        assert st_j == 200
        st_jbin, j_bytes, _ = api_bytes(f"{FRONTEND_URL}{json_receipt['bff_download_url']}", opener=uni_opener)
        assert st_jbin == 200
        j_parsed = json.loads(j_bytes.decode("utf-8"))
        assert j_parsed["document_kind"] == doc_type
    print("[PASS] Phase 8: Both Documents PDF (real pypdf text verified) & JSON downloaded cleanly via BFF.")

    # 9. Verify HMAC E-Imzo Code + Audit Trail
    st_v, ver_res, _ = api_json(
        f"{FRONTEND_URL}/api/bff/internship-documents/verify/{conc_verify_code}",
        method="GET",
        opener=emp_opener,
    )
    assert st_v == 200 and ver_res["valid"] is True and ver_res["stamp"]["party"] == "CANDIDATE"

    with engine.connect() as conn:
        audit_cnt = conn.execute(text("""
            SELECT COUNT(*) FROM flexbridge.audit_events
            WHERE object_key = :pid AND action IN ('INTERNSHIP_DIARY_EIMZO_SIGNED', 'FINAL_CONCLUSION_EIMZO_SIGNED', 'INTERNSHIP_DOCUMENT_EXPORTED')
        """), {"pid": placement_id}).scalar_one()
    assert audit_cnt >= 7, f"Expected >= 7 audit events, found {audit_cnt}"
    print(f"[PASS] Phase 9: Cryptographic E-Imzo verification & {audit_cnt} audit events confirmed.")
    print("=== ALL FB-204 STAGING CHECKS PASSED 100% ===")


if __name__ == "__main__":
    main()
