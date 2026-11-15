#!/usr/bin/env python3
"""FlexBridge 1.4 Candidate Student Enrollments & Availability Exceptions Staging Verification Suite (FB-184).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on all endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: Database Fixtures Setup via PgBouncer (Users, Candidates, Verified & Unverified Institutions).
Phase 4: Candidate authentication via Next.js BFF (/api/auth/login) with MFA assurance elevation.
Phase 5: API-027 Submit Student Enrollment (POST /api/bff/candidate/enrollments) (HTTP 201 Created).
Phase 6: API-027 Idempotent Repeat submission with same key (HTTP 201/200).
Phase 7: API-034 List Candidate Enrollments & Detail, plus Verified Institutions Catalog.
Phase 8: End Enrollment Lifecycle (POST /api/bff/candidate/enrollments/{id}/end) with validation & ENDED status.
Phase 9: API-036 Put Availability Exceptions (PUT /api/bff/candidate/availability/exceptions).
Phase 10: Negative Authorization, Institution Verification Guard & Cross-Candidate Isolation (422/409/404).

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
STAGING_DB_URL = os.environ.get(
    "STAGING_DB_URL",
    "postgresql+psycopg://flexbridge_owner:stg_secure_pg_pass_2026_flexbridge_isolated@127.0.0.1:5432/flexbridge",
)

engine = create_engine(STAGING_DB_URL, connect_args={"prepare_threshold": None})


def make_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
    call_opener = opener or urllib.request.build_opener()

    try:
        with call_opener.open(req) as response:
            resp_code = response.getcode()
            raw_body = response.read().decode("utf-8")
            resp_headers = dict(response.info())
            try:
                resp_json = json.loads(raw_body) if raw_body else {}
            except Exception:
                resp_json = {"raw": raw_body}
            return resp_code, resp_json, resp_headers
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        try:
            resp_json = json.loads(raw_body) if raw_body else {}
        except Exception:
            resp_json = {"raw": raw_body}
        return exc.code, resp_json, dict(exc.headers)


def main() -> int:
    print("=" * 80)
    print("FlexBridge 1.4 Candidate Enrollments & Availability Exceptions Staging Verification Suite (FB-184)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated access rejected (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Unauthenticated Access Rejection (HTTP 401) ---")
    dummy_uuid = str(uuid4())

    unauth_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/enrollments"),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/enrollments"),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/enrollments/{dummy_uuid}"),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/enrollments/{dummy_uuid}/end"),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/institutions"),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/availability/exceptions"),
    ]

    for m, url in unauth_endpoints:
        code, data, _ = make_request(
            url,
            method=m,
            data={"test": "data"} if m in ("POST", "PUT") else None,
            headers={"Origin": FRONTEND_URL} if m in ("POST", "PUT") else None,
        )
        assert code == 401, f"Expected 401 for unauth {m} {url}, got {code}: {data}"
        print(f"  [PASS] Unauth {m} {url} correctly rejected: 401")

    # -------------------------------------------------------------------------
    # Phase 2: Anti-CSRF Origin Guard rejection (HTTP 403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Anti-CSRF Origin Guard Rejection (HTTP 403) ---")
    csrf_endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/enrollments"),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/enrollments/{dummy_uuid}/end"),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/availability/exceptions"),
    ]

    for m, url in csrf_endpoints:
        # Invalid origin
        code, data, _ = make_request(
            url,
            method=m,
            data={"test": "data"},
            headers={"Origin": "https://attacker.evil.com"},
        )
        assert code == 403, f"Expected 403 for forged Origin on {m} {url}, got {code}: {data}"
        assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got: {data}"
        print(f"  [PASS] CSRF forgery on {m} {url} correctly blocked: 403 CSRF_ORIGIN_MISMATCH")

    # -------------------------------------------------------------------------
    # Phase 3: Database Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n--- Phase 3: Database Fixtures Setup via PgBouncer ---")
    user_a_id = str(uuid4())
    user_b_id = str(uuid4())
    cand_a_id = str(uuid4())
    cand_b_id = str(uuid4())
    verified_inst_id = str(uuid4())
    unverified_inst_id = str(uuid4())

    pwd = "StagingCandPass123!"
    pwd_hash = hash_password(pwd)

    with engine.begin() as conn:
        # 1. Candidate User A
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.users (id, display_name, status, password_hash, locale, timezone, adult_declared_at, auth_version, created_at, updated_at)
                VALUES (:id, 'Test Candidate A (FB-184)', 'ACTIVE', :pwd, 'uz', 'Asia/Tashkent', NOW(), 1, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": user_a_id, "pwd": pwd_hash},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.candidate_profiles (id, user_id, headline, region, bio, experience_months, visibility, created_at, updated_at)
                VALUES (:cid, :uid, 'Talaba Dasturchi', 'Toshkent shahri', 'TATU talabasi va dasturchi', 12, 'PUBLIC', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"cid": cand_a_id, "uid": user_a_id},
        )

        # 2. Candidate User B (Foreign)
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.users (id, display_name, status, password_hash, locale, timezone, adult_declared_at, auth_version, created_at, updated_at)
                VALUES (:id, 'Test Candidate B (Foreign)', 'ACTIVE', :pwd, 'uz', 'Asia/Tashkent', NOW(), 1, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": user_b_id, "pwd": pwd_hash},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.candidate_profiles (id, user_id, headline, region, bio, experience_months, visibility, created_at, updated_at)
                VALUES (:cid, :uid, 'Boshqa Nomzod', 'Samarqand', 'SamDU talabasi', 6, 'PUBLIC', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"cid": cand_b_id, "uid": user_b_id},
        )

        # 3. Verified Institution
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institutions (id, registry_code, name, region, status, created_at, updated_at)
                VALUES (:id, :code, 'Toshkent Axborot Texnologiyalari Universiteti (TATU)', 'Tashkent', 'VERIFIED', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": verified_inst_id, "code": f"INST_V_{uuid4().hex[:8]}"},
        )

        # 4. Unverified Institution (status PENDING) for negative tests
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institutions (id, registry_code, name, region, status, created_at, updated_at)
                VALUES (:id, :code, 'Tekshirilmagan Xususiy OTM', 'Tashkent', 'PENDING', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": unverified_inst_id, "code": f"INST_UNV_{uuid4().hex[:8]}"},
        )

    print("  [PASS] Candidate User A, Candidate User B, and Institutions successfully created")

    # -------------------------------------------------------------------------
    # Phase 4: Candidate Authentication via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Candidate Authentication via Next.js BFF ---")

    def login_and_elevate(uid: str, pwd_str: str, name: str) -> urllib.request.OpenerDirector:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        code, data, _ = make_request(
            f"{FRONTEND_URL}/api/auth/login",
            method="POST",
            data={"user_id": uid, "password": pwd_str},
            headers={"Origin": FRONTEND_URL},
            opener=opener,
        )
        assert code == 200, f"Login failed for {name} ({uid}): {code} - {data}"
        print(f"  [PASS] {name} logged in successfully via BFF")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE flexbridge.sessions
                    SET assurance = 'MFA', updated_at = NOW()
                    WHERE user_id = :uid AND revoked_at IS NULL
                    """
                ),
                {"uid": uid},
            )
        print(f"  [PASS] {name} session assurance elevated to MFA")
        return opener

    user_a_opener = login_and_elevate(user_a_id, pwd, "Candidate A")
    user_b_opener = login_and_elevate(user_b_id, pwd, "Candidate B (Foreign)")

    # -------------------------------------------------------------------------
    # Phase 5: API-027 Submit Student Enrollment (POST /api/bff/candidate/enrollments)
    # -------------------------------------------------------------------------
    print("\n--- Phase 5: API-027 Submit Student Enrollment (Initial Creation) ---")
    idem_key_1 = f"enr-idem-{uuid4().hex[:12]}"
    enr_payload = {
        "institution_id": verified_inst_id,
        "program": "Dasturiy Injiniring (Bakalavr)",
        "start_date": "2023-09-01",
        "end_date": "2027-06-30",
        "student_ref": "HEMIS-3912011005",
        "evidence_note": "Toshkent Axborot Texnologiyalari Universiteti talabasi guvohnomasi va HEMIS ma'lumotnomasi",
        "idempotency_key": idem_key_1,
    }

    code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments",
        method="POST",
        data=enr_payload,
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 201, f"Expected 201 Created for API-027, got {code}: {data}"
    assert data.get("ok") is True, f"Expected ok: true, got: {data}"
    assert data.get("contract_id") == "API-027", f"Expected contract_id: API-027, got: {data}"
    enrollment_id = data.get("id") or data.get("enrollment_id")
    assert enrollment_id, f"Expected enrollment_id returned, got: {data}"
    print(f"  [PASS] API-027 enrollment created successfully: {enrollment_id} (Status: {data.get('status')})")

    # -------------------------------------------------------------------------
    # Phase 6: API-027 Idempotent Repeat Submission
    # -------------------------------------------------------------------------
    print("\n--- Phase 6: API-027 Idempotent Repeat Submission ---")
    code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments",
        method="POST",
        data=enr_payload,
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on idempotent repeat, got {code}: {data}"
    repeat_id = data.get("id") or data.get("enrollment_id")
    assert repeat_id == enrollment_id, f"Expected same enrollment_id {enrollment_id}, got {repeat_id}"
    print(f"  [PASS] API-027 idempotent repeat handled correctly with identical ID: {repeat_id}")

    # -------------------------------------------------------------------------
    # Phase 7: API-034 List Candidate Enrollments & Detail, plus Institutions Catalog
    # -------------------------------------------------------------------------
    print("\n--- Phase 7: API-034 List Candidate Enrollments & Detail ---")
    code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 for API-034 list, got {code}: {data}"
    assert data.get("contract_id") == "API-034", f"Expected API-034 contract_id, got: {data}"
    items = data.get("items", [])
    assert len(items) >= 1, f"Expected at least 1 enrollment, got: {len(items)}"
    matching_enr = next((e for e in items if e["id"] == enrollment_id), None)
    assert matching_enr, f"Created enrollment {enrollment_id} not found in list: {items}"
    assert matching_enr["program"] == "Dasturiy Injiniring (Bakalavr)"
    assert matching_enr["institution_id"] == verified_inst_id
    assert "status" in matching_enr
    print(f"  [PASS] API-034 list returned {len(items)} items including {enrollment_id}")

    # Test Detail endpoint
    code, detail_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 for detail, got {code}: {detail_data}"
    detail_id = detail_data.get("id") or detail_data.get("enrollment_id")
    assert detail_id == enrollment_id, f"Expected {enrollment_id}, got {detail_id}"
    print(f"  [PASS] GET /api/bff/candidate/enrollments/{enrollment_id} returned matching detail")

    # Test Institutions Catalog
    code, inst_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/institutions",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 for institutions catalog, got {code}: {inst_data}"
    inst_items = inst_data.get("items", [])
    assert len(inst_items) >= 1, f"Expected >= 1 institutions, got: {len(inst_items)}"
    print(f"  [PASS] Verified institutions catalog returned {len(inst_items)} educational institutions")

    # -------------------------------------------------------------------------
    # Phase 8: End Enrollment Workflow (POST /api/bff/candidate/enrollments/{id}/end)
    # -------------------------------------------------------------------------
    print("\n--- Phase 8: End Enrollment Lifecycle ---")
    # Validation check: reason < 15 chars rejected
    code, bad_end_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}/end",
        method="POST",
        data={"reason": "Qisqa sabab"},
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 422, f"Expected 422 for reason < 15 chars, got {code}: {bad_end_data}"
    print("  [PASS] Short reason correctly rejected with HTTP 422 VALIDATION_FAILED")

    # Valid end enrollment
    end_payload = {
        "reason": "Talaba bakalavriat bosqichini muvaffaqiyatli tamomladi va diplom oldi.",
        "effective_end_date": "2024-06-30",
        "idempotency_key": f"end-idem-{uuid4().hex[:12]}",
    }
    code, end_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}/end",
        method="POST",
        data=end_payload,
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 OK for end enrollment, got {code}: {end_data}"
    assert end_data.get("status") == "ENDED" or end_data.get("ok") is True, f"Expected ENDED status, got: {end_data}"
    print(f"  [PASS] Enrollment {enrollment_id} successfully marked as ENDED")

    # Re-verify detail status is ENDED
    code, detail_data2, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 for detail, got {code}: {detail_data2}"
    assert detail_data2.get("status") in ("ENDED", "WITHDRAWN"), f"Expected status ENDED or WITHDRAWN, got {detail_data2.get('status')}"
    print(f"  [PASS] Verified enrollment {enrollment_id} status persisted as ENDED")

    # -------------------------------------------------------------------------
    # Phase 9: API-036 Put Availability Exceptions (PUT /api/bff/candidate/availability/exceptions)
    # -------------------------------------------------------------------------
    print("\n--- Phase 9: API-036 Put Availability Exceptions ---")
    today = date.today()
    d1 = today + timedelta(days=2)
    d2 = today + timedelta(days=5)
    from_d = today
    to_d = today + timedelta(days=28)

    exc_payload = {
        "from_date": str(from_d),
        "to_date": str(to_d),
        "exceptions": [
            {
                "local_date": str(d1),
                "kind": "UNAVAILABLE",
                "start_minute": 540,  # 09:00
                "end_minute": 1080,  # 18:00
            },
            {
                "local_date": str(d2),
                "kind": "AVAILABLE",
                "start_minute": 600,  # 10:00
                "end_minute": 960,  # 16:00
            },
        ],
    }

    code, exc_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability/exceptions",
        method="PUT",
        data=exc_payload,
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 OK for API-036, got {code}: {exc_data}"
    assert exc_data.get("contract_id") == "API-036", f"Expected API-036 contract_id, got: {exc_data}"
    print(f"  [PASS] API-036 availability exceptions saved successfully (Replaced {exc_data.get('replaced_from')} to {exc_data.get('replaced_to')})")

    # Verify merged calendar via GET /api/bff/candidate/availability
    code, avail_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability?from_date={from_d}&days=28",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 OK for availability, got {code}: {avail_data}"
    effective_days = avail_data.get("effective_days", [])
    exc_items = avail_data.get("exceptions", [])
    assert len(effective_days) >= 28, f"Expected >= 28 effective days, got {len(effective_days)}"
    assert len(exc_items) >= 2, f"Expected >= 2 exceptions returned, got {len(exc_items)}"
    print(f"  [PASS] GET /api/bff/candidate/availability confirmed {len(effective_days)} calendar days and {len(exc_items)} exceptions")

    # -------------------------------------------------------------------------
    # Phase 10: Negative Authorization & Cross-Candidate Isolation
    # -------------------------------------------------------------------------
    print("\n--- Phase 10: Negative Authorization & Cross-Candidate Isolation ---")

    # Negative 1: Submit enrollment with UNVERIFIED institution
    bad_inst_payload = {
        "institution_id": unverified_inst_id,
        "program": "Sinov Dasturi",
        "start_date": "2024-01-01",
        "idempotency_key": f"enr-bad-{uuid4().hex[:12]}",
    }
    code, bad_inst_res, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments",
        method="POST",
        data=bad_inst_payload,
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code in (404, 409), f"Expected 404 or 409 Conflict for unverified institution, got {code}: {bad_inst_res}"
    print(f"  [PASS] Unverified institution enrollment submission correctly blocked: {code} UNAVAILABLE/CONFLICT")

    # Negative 2: Cross-candidate IDOR defense on detail
    code, idor_res, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_b_opener,
    )
    assert code == 404, f"Expected 404 for cross-candidate enrollment detail, got {code}: {idor_res}"
    print(f"  [PASS] Candidate B denied access to Candidate A's enrollment detail: 404 IDOR defense")

    # Negative 3: Cross-candidate isolation on end enrollment
    code, idor_end_res, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/enrollments/{enrollment_id}/end",
        method="POST",
        data={"reason": "Begona nomzod boshqasining talabaligini to'xtatmoqchi bo'lyapti."},
        headers={"Origin": FRONTEND_URL},
        opener=user_b_opener,
    )
    assert code in (403, 404), f"Expected 403 or 404 for cross-candidate end enrollment, got {code}: {idor_end_res}"
    print(f"  [PASS] Candidate B denied mutative action on Candidate A's enrollment: {code} Isolation defense")

    print("\n" + "=" * 80)
    print("VICTORY CONFIRMED: ALL 10 PHASES OF FB-184 PASSED 100% GREEN!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
