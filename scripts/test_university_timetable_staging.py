#!/usr/bin/env python3
"""
Staging Verification Suite: University Class Timetable Manual Entry & Template Upload/Import (FB-202)

Contracts & Capabilities Verified:
1. API-098-TIMETABLE (Manual Class Timetable Entry & Retrieval):
   - GET /api/bff/university/institutions/{inst}/timetables
   - PUT /api/bff/university/institutions/{inst}/timetables (REPLACE, APPEND, DELETE_SLOT)
   - Automatic computation of free work windows (`computed_free_windows`) outside class hours + commute buffer
   - Automatic synchronization of `flexbridge.availability_rules` for enrolled students (`student_enrollments`)
   - Intra-group time conflict detection (`422 TIMETABLE_SLOT_OVERLAP`)
2. API-098-TIMETABLE-TEMPLATE (Official CSV & JSON Template Specification):
   - GET /api/bff/university/institutions/{inst}/timetables/template?format=CSV
   - GET /api/bff/university/institutions/{inst}/timetables/template?format=JSON
3. API-098-TIMETABLE-IMPORT (Template File Upload/Import):
   - POST /api/bff/university/institutions/{inst}/timetables/import (CSV & JSON content and Base64)
4. Cross-Institution IDOR & CSRF Guards + Audit Trail:
   - 401/403 CSRF & unauthenticated rejection
   - 403 INSTITUTION_SCOPE_FORBIDDEN for outside institution staff
   - Audit events: INSTITUTION_TIMETABLE_MANUAL_SAVE, INSTITUTION_TIMETABLE_TEMPLATE_IMPORT
"""

import base64
import json
import os
import sys
from datetime import date, datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4

from dotenv import dotenv_values
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


def api_request(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    opener=None,
) -> Tuple[int, Any]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = Request(url, data=body, headers=req_headers, method=method)
    active_opener = opener or build_opener()

    try:
        with active_opener.open(req) as resp:
            code = resp.status
            content = resp.read().decode("utf-8")
            try:
                payload = json.loads(content)
            except Exception:
                payload = content
            return code, payload
    except HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            payload = json.loads(content)
        except Exception:
            payload = content
        return e.code, payload


def main():
    print("=" * 84)
    print("FLEXBRIDGE 1.4 STAGING SUITE: University Class Timetable Manual & Template Import (FB-202)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print("Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 84)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_password = "StagingTimetablePassword!2026"
    pw_hash = hash_password(test_password)
    now_dt = datetime.now(timezone.utc)
    today = date.today()
    suffix = uuid4().hex[:8]

    univ_user_id = str(uuid4())
    outsider_user_id = str(uuid4())
    student_user_id = str(uuid4())
    candidate_id = str(uuid4())
    inst_id = str(uuid4())
    outsider_inst_id = str(uuid4())
    inst_membership_id = str(uuid4())
    outsider_membership_id = str(uuid4())
    enrollment_id = str(uuid4())

    origin_headers = {"Origin": FRONTEND_URL}

    try:
        # ------------------------------------------------------------------
        # PHASE 1: Unauthenticated & CSRF Guards
        # ------------------------------------------------------------------
        print("\n[Phase 1] Verifying Unauthenticated & CSRF Guards...")
        c1, _ = api_request(f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables")
        assert c1 == 401, f"Expected 401 on unauthenticated GET timetable, got {c1}"

        c2, _ = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            method="PUT",
            data={"mode": "REPLACE", "slots": []},
            headers={"Origin": "https://evil.example.com"},
        )
        assert c2 == 403, f"Expected 403 on forged Origin PUT timetable, got {c2}"

        c3, _ = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables/import",
            method="POST",
            data={"format": "CSV", "content": ""},
            headers={"Origin": "https://evil.example.com"},
        )
        assert c3 == 403, f"Expected 403 on forged Origin POST import, got {c3}"
        print("  -> Unauthenticated (401) and CSRF Origin (403) guards PASSED.")

        # ------------------------------------------------------------------
        # PHASE 2: Seed University, Staff, Outsider Staff & Enrolled Student
        # ------------------------------------------------------------------
        print("\n[Phase 2] Seeding University Institution, Staff & Enrolled Student...")
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE flexbridge.auth_rate_limits"))
            for uid, dname in [
                (univ_user_id, f"Prof. Timetable {suffix}"),
                (outsider_user_id, f"Prof. Outsider {suffix}"),
                (student_user_id, f"Talaba {suffix}"),
            ]:
                conn.execute(
                    text(
                        """
                        INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                        VALUES (:id, :now, :now, :dname, :pw, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
                        """
                    ),
                    {"id": uid, "dname": dname, "pw": pw_hash, "now": now_dt},
                )

            conn.execute(
                text(
                    """
                    INSERT INTO flexbridge.candidate_profiles (
                        id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility
                    ) VALUES (
                        :id, :now, :now, :uid, '4-kurs DI-21-01 Talabasi', 'Toshkent shahri', 'Timetable test student', 12, 'PUBLIC'
                    )
                    """
                ),
                {"id": candidate_id, "uid": student_user_id, "now": now_dt},
            )

            for iid, name, code in [
                (inst_id, f"TUIT Timetable University {suffix}", f"OTM-TT1-{suffix}"),
                (outsider_inst_id, f"Outsider University {suffix}", f"OTM-TT2-{suffix}"),
            ]:
                conn.execute(
                    text(
                        """
                        INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                        VALUES (:id, :now, :now, :code, :name, 'Toshkent', 'VERIFIED')
                        """
                    ),
                    {"id": iid, "code": code, "name": name, "now": now_dt},
                )

            conn.execute(
                text(
                    """
                    INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                    VALUES
                        (:mid1, :now, :now, :iid1, :uid1, 'ACTIVE', :now),
                        (:mid2, :now, :now, :iid2, :uid2, 'ACTIVE', :now)
                    """
                ),
                {
                    "mid1": inst_membership_id,
                    "iid1": inst_id,
                    "uid1": univ_user_id,
                    "mid2": outsider_membership_id,
                    "iid2": outsider_inst_id,
                    "uid2": outsider_user_id,
                    "now": now_dt,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO flexbridge.enrollments (
                        id, created_at, updated_at, candidate_id, institution_id, program, start_date, end_date, status
                    ) VALUES (
                        :id, :now, :now, :cid, :iid, 'Dasturiy injiniring DI-21-01', :today, NULL, 'PENDING_VERIFICATION'
                    )
                    """
                ),
                {"id": enrollment_id, "cid": candidate_id, "iid": inst_id, "today": today, "now": now_dt},
            )

        def login_session(uid: str, role: str):
            cj = CookieJar()
            op = build_opener(HTTPCookieProcessor(cj))
            code, body = api_request(
                f"{FRONTEND_URL}/api/auth/login",
                method="POST",
                data={"user_id": uid, "password": test_password, "roles": [role]},
                headers=origin_headers,
                opener=op,
            )
            assert code == 200, f"Login failed for {uid}: {code} {body}"
            return op

        univ_opener = login_session(univ_user_id, "UNIVERSITY_REPRESENTATIVE")
        outsider_opener = login_session(outsider_user_id, "UNIVERSITY_REPRESENTATIVE")
        print("  -> University staff, outsider staff, and enrolled student seeded and authenticated.")

        # ------------------------------------------------------------------
        # PHASE 3: Official Template Specification Download (CSV & JSON)
        # ------------------------------------------------------------------
        print("\n[Phase 3] Verifying Official CSV & JSON Timetable Templates...")
        t_code, t_csv = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables/template?format=CSV",
            opener=univ_opener,
        )
        assert t_code == 200 and t_csv.get("ok") is True, f"CSV template fetch failed: {t_code} {t_csv}"
        assert t_csv.get("contract_id") == "API-098-TIMETABLE-TEMPLATE"
        assert "group_code,program_name,study_year,weekday" in t_csv.get("csv_template", "")
        assert len(t_csv.get("para_presets", [])) == 7

        t_jcode, t_json = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables/template?format=JSON",
            opener=univ_opener,
        )
        assert t_jcode == 200 and t_json.get("filename") == "flexbridge_otm_dars_jadvali_shablon.json"
        print("  -> Official CSV & JSON template downloads PASSED.")

        # ------------------------------------------------------------------
        # PHASE 4: Manual Class Timetable Entry (REPLACE, APPEND & DELETE_SLOT)
        # ------------------------------------------------------------------
        print("\n[Phase 4] Verifying Manual Class Timetable Entry & Student Sync...")
        m_code, m_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            method="PUT",
            data={
                "mode": "REPLACE",
                "academic_semester": "2026-2027 Kuzgi semestr",
                "commute_buffer_minutes": 30,
                "slots": [
                    {
                        "group_code": "DI-21-01",
                        "program_name": "Dasturiy injiniring",
                        "study_year": "4-kurs",
                        "weekday": 1,
                        "para_number": 1,
                        "start_time": "08:30",
                        "end_time": "09:50",
                        "subject_name": "Sun'iy intellekt tizimlari",
                        "lesson_type": "MA'RUZA",
                        "room": "A-201",
                        "teacher_name": "Prof. R. Rahimov",
                    },
                    {
                        "group_code": "DI-21-01",
                        "program_name": "Dasturiy injiniring",
                        "study_year": "4-kurs",
                        "weekday": 1,
                        "para_number": 2,
                        "start_time": "10:00",
                        "end_time": "11:20",
                        "subject_name": "Bulutli hisoblash",
                        "lesson_type": "AMALIYOT",
                        "room": "Lab-104",
                        "teacher_name": "Dots. S. Karimov",
                    },
                ],
            },
            headers=origin_headers,
            opener=univ_opener,
        )
        assert m_code == 200 and m_body.get("ok") is True, f"Manual REPLACE failed: {m_code} {m_body}"
        assert m_body.get("total_slots") == 2
        assert m_body.get("students_synced_count") == 1, f"Expected 1 synced student, got {m_body}"
        assert "DI-21-01" in m_body.get("computed_free_windows", {})

        # Append a 3rd slot via mode="APPEND"
        app_code, app_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            method="PUT",
            data={
                "mode": "APPEND",
                "slot": {
                    "group_code": "DI-21-01",
                    "program_name": "Dasturiy injiniring",
                    "study_year": "4-kurs",
                    "weekday": 2,
                    "para_number": 1,
                    "start_time": "08:30",
                    "end_time": "09:50",
                    "subject_name": "Axborot xavfsizligi",
                    "lesson_type": "SEMINAR",
                    "room": "B-305",
                    "teacher_name": "K. O'rinov",
                },
            },
            headers=origin_headers,
            opener=univ_opener,
        )
        assert app_code == 200 and app_body.get("total_slots") == 3, f"Manual APPEND failed: {app_code} {app_body}"
        print(f"  -> Manual entry (REPLACE + APPEND) PASSED: {app_body.get('total_slots')} slots saved.")

        # ------------------------------------------------------------------
        # PHASE 5: Overlap Detection (422 TIMETABLE_SLOT_OVERLAP) & DELETE_SLOT
        # ------------------------------------------------------------------
        print("\n[Phase 5] Verifying Overlap Rejection (422) & Slot Deletion...")
        ov_code, ov_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            method="PUT",
            data={
                "mode": "APPEND",
                "slot": {
                    "group_code": "DI-21-01",
                    "weekday": 1,
                    "para_number": 1,
                    "start_time": "09:00",
                    "end_time": "10:30",
                    "subject_name": "To'qnashuvchi dars",
                    "lesson_type": "MA'RUZA",
                },
            },
            headers=origin_headers,
            opener=univ_opener,
        )
        assert ov_code == 422, f"Expected 422 on overlapping class slot, got {ov_code} {ov_body}"

        slot_to_delete = app_body["slots"][-1]["id"]
        del_code, del_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            method="PUT",
            data={"mode": "DELETE_SLOT", "slot_id": slot_to_delete},
            headers=origin_headers,
            opener=univ_opener,
        )
        assert del_code == 200 and del_body.get("total_slots") == 2, f"DELETE_SLOT failed: {del_code} {del_body}"
        print("  -> Intra-group time overlap guard (422 TIMETABLE_SLOT_OVERLAP) & DELETE_SLOT PASSED.")

        # ------------------------------------------------------------------
        # PHASE 6: Template Upload/Import (CSV & JSON) + Student Availability DB Verification
        # ------------------------------------------------------------------
        print("\n[Phase 6] Verifying CSV & JSON Template Import + Student Availability DB Sync...")
        csv_upload_text = t_csv["csv_template"]
        imp_code, imp_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables/import",
            method="POST",
            data={
                "format": "CSV",
                "replace_existing": True,
                "academic_semester": "2026-2027 Kuzgi semestr",
                "commute_buffer_minutes": 30,
                "content": csv_upload_text,
            },
            headers=origin_headers,
            opener=univ_opener,
        )
        assert imp_code in (200, 201) and imp_body.get("ok") is True, f"CSV import failed: {imp_code} {imp_body}"
        assert imp_body.get("imported_count") == 4
        assert imp_body.get("total_slots") == 4
        assert imp_body.get("students_synced_count") == 1

        # Also test JSON template import via base64 content
        json_b64 = base64.b64encode(t_json["json_template"].encode("utf-8")).decode("ascii")
        jimp_code, jimp_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables/import",
            method="POST",
            data={
                "format": "JSON",
                "replace_existing": True,
                "content_base64": json_b64,
            },
            headers=origin_headers,
            opener=univ_opener,
        )
        assert jimp_code in (200, 201) and jimp_body.get("total_slots") == 4, f"JSON import failed: {jimp_code} {jimp_body}"

        # Verify student's availability_rules rows in PostgreSQL
        with engine.connect() as conn:
            rules_count = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM flexbridge.availability_rules
                    WHERE candidate_id = :cid
                    """
                ),
                {"cid": candidate_id},
            ).scalar()
            assert rules_count and rules_count >= 6, f"Expected >= 6 availability_rules for enrolled student, got {rules_count}"
        print(f"  -> CSV & JSON template imports PASSED ({rules_count} free work windows synced to availability_rules).")

        # ------------------------------------------------------------------
        # PHASE 7: Cross-Institution IDOR Guard & Audit Trail
        # ------------------------------------------------------------------
        print("\n[Phase 7] Verifying Cross-Institution IDOR Guard (403) & Audit Trail...")
        idor_code, idor_body = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/timetables",
            opener=outsider_opener,
        )
        assert idor_code == 403, f"Expected 403 for outsider university staff, got {idor_code} {idor_body}"

        with engine.connect() as conn:
            audit_rows = conn.execute(
                text(
                    """
                    SELECT action FROM flexbridge.audit_events
                    WHERE actor_id = :uid
                      AND action IN ('INSTITUTION_TIMETABLE_MANUAL_SAVE', 'INSTITUTION_TIMETABLE_TEMPLATE_IMPORT')
                    """
                ),
                {"uid": univ_user_id},
            ).scalars().all()
            assert "INSTITUTION_TIMETABLE_MANUAL_SAVE" in audit_rows
            assert "INSTITUTION_TIMETABLE_TEMPLATE_IMPORT" in audit_rows
        print("  -> Cross-institution IDOR guard (403) & Audit Trail PASSED.")

        print("\n" + "=" * 84)
        print("ALL UNIVERSITY TIMETABLE MANUAL & TEMPLATE IMPORT TESTS PASSED (100% GREEN)!")
        print("=" * 84)

    finally:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE flexbridge.auth_rate_limits"))


if __name__ == "__main__":
    main()
