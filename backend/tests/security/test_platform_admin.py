"""Security & contract tests for Super Admin, bootstrap CLI, directories, feature-flags read, and recovery/privacy queues (API-126..API-135)."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.storage import now, save_domain_record, table, transaction
from app.services.auth import generate_totp_code
from app.services.platform_admin import SYSTEM_AUTHORITY_USER_ID
from test_iam import delivery, proof  # noqa: F401
from test_institution_recovery import verified_student
from test_invitations import contact

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.bootstrap_super_admin import BootstrapError, bootstrap_super_admin, main as bootstrap_cli_main  # noqa: E402


def _age_challenges() -> None:
    with transaction() as conn:
        conn.execute(table("auth_challenges").update().values(created_at=now() - timedelta(seconds=61)))


def _grant_platform_role_in_db(user_id: str, role_code: str, granted_by_id: str, *, days: int = 3650) -> str:
    with transaction() as conn:
        roles = table("role_catalog")
        role_row = conn.execute(select(roles.c.id).where(roles.c.code == role_code, roles.c.scope_kind == "PLATFORM")).first()
        if role_row is None:
            rid = str(uuid4())
            conn.execute(
                roles.insert().values(
                    id=rid,
                    created_at=now(),
                    updated_at=now(),
                    code=role_code,
                    scope_kind="PLATFORM",
                    description=role_code,
                )
            )
        else:
            rid = str(role_row[0])
        gid = str(uuid4())
        conn.execute(
            table("platform_role_grants").insert().values(
                id=gid,
                created_at=now(),
                updated_at=now(),
                user_id=user_id,
                role_id=rid,
                granted_by_id=granted_by_id,
                expires_at=now() + timedelta(days=days),
                revoked_at=None,
            )
        )
        return gid


def test_bootstrap_super_admin_idempotency_anchor_and_mfa_login(client, monkeypatch, capsys):
    email = f"super.{uuid4().hex[:8]}@flexbridge.test"
    monkeypatch.setenv("TEST_BOOTSTRAP_ADMIN_PW", "Super-Admin-Bootstrap-Pass-2026!")

    # First run via CLI main(): creates user, non-login System Authority anchor, ADMIN grant, and TOTP.
    rc1 = bootstrap_cli_main(
        [
            "--email",
            email,
            "--create",
            "--display-name",
            "Root Super Admin",
            "--password-env",
            "TEST_BOOTSTRAP_ADMIN_PW",
            "--days",
            "3650",
            "--enroll-totp",
        ]
    )
    assert rc1 == 0
    out1 = json.loads(capsys.readouterr().out)
    assert out1["ok"] is True
    assert out1["created_user"] is True
    assert out1["grant_created"] is True
    assert out1["idempotent_noop"] is False
    assert out1["system_authority_id"] == SYSTEM_AUTHORITY_USER_ID
    assert out1["otpauth_uri"].startswith("otpauth://totp/")

    # Extract TOTP secret from otpauth URI only to verify real MFA login works.
    secret = parse_qs(urlparse(out1["otpauth_uri"]).query)["secret"][0]

    # Second run (idempotent): does not create duplicate grant, does not re-print otpauth URI, does not duplicate audit.
    rc2 = bootstrap_cli_main(
        [
            "--email",
            email,
            "--create",
            "--display-name",
            "Root Super Admin",
            "--password-env",
            "TEST_BOOTSTRAP_ADMIN_PW",
            "--enroll-totp",
        ]
    )
    assert rc2 == 0
    out2 = json.loads(capsys.readouterr().out)
    assert out2["ok"] is True
    assert out2["created_user"] is False
    assert out2["grant_created"] is False
    assert out2["idempotent_noop"] is True
    assert out2["totp_already_enrolled"] is True
    assert "otpauth_uri" not in out2
    assert out2["grant_id"] == out1["grant_id"]

    # Verify non-login System Authority anchor invariants and single grant/audit row.
    with transaction() as conn:
        anchor = conn.execute(select(table("users")).where(table("users").c.id == SYSTEM_AUTHORITY_USER_ID)).mappings().one()
        assert anchor["status"] == "LIMITED"
        assert anchor["password_hash"] is None
        assert anchor["display_name"] == "FlexBridge System Authority"

        grants = conn.execute(
            select(table("platform_role_grants")).where(table("platform_role_grants").c.user_id == out1["user_id"])
        ).mappings().all()
        assert len(grants) == 1
        assert str(grants[0]["granted_by_id"]) == SYSTEM_AUTHORITY_USER_ID

        audits = conn.execute(
            select(table("audit_events")).where(table("audit_events").c.action == "SUPER_ADMIN_BOOTSTRAPPED")
        ).all()
        assert len(audits) == 1

    # System Authority anchor can NEVER authenticate.
    anchor_login = client.post(
        "/api/v1/auth/login",
        json={"user_id": SYSTEM_AUTHORITY_USER_ID, "password": "Super-Admin-Bootstrap-Pass-2026!"},
    )
    assert anchor_login.status_code == 401

    # Bootstrapped admin authenticates via channel/destination + password + TOTP and accesses API-126.
    logged = client.post(
        "/api/v1/auth/login",
        json={
            "channel": "EMAIL",
            "destination": email,
            "password": "Super-Admin-Bootstrap-Pass-2026!",
            "totp_code": generate_totp_code(secret),
        },
    )
    assert logged.status_code == 200, logged.text
    admin_headers = {"Authorization": "Bearer " + logged.json()["access_token"]}
    res = client.get("/api/v1/operator/staff-grants", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json()["contract_id"] == "API-126"
    assert any(g["user_id"] == out1["user_id"] and g["is_permanent"] is True for g in res.json()["active_grants"])

    # Cannot bootstrap the System Authority anchor itself.
    with pytest.raises(BootstrapError):
        bootstrap_super_admin(user_id=SYSTEM_AUTHORITY_USER_ID)


def test_bootstrap_without_enroll_totp_never_prints_otpauth(identities, capsys):
    user = identities()
    rc = bootstrap_cli_main(["--user-id", user["user_id"]])
    assert rc == 0
    raw = capsys.readouterr().out
    assert "otpauth://" not in raw
    parsed = json.loads(raw)
    assert "otpauth_uri" not in parsed
    assert parsed["grant_created"] is True


def test_staff_grants_lifecycle_self_guards_last_admin_and_non_admin_403(client, identities):
    admin1 = identities("ADMIN")
    target = identities()
    email = f"staff.{uuid4().hex[:8]}@flexbridge.test"
    contact(target, value=email, channel="EMAIL")
    sec_lead = identities("SECURITY_LEAD")
    moderator = identities("MODERATOR")
    candidate = identities()

    # Unauthenticated -> 401
    assert client.get("/api/v1/operator/staff-grants").status_code == 401
    assert client.post("/api/v1/operator/staff-grants", json={}).status_code == 401

    # Non-admin (candidate / moderator) -> 403
    for u in (candidate, moderator):
        assert client.get("/api/v1/operator/staff-grants", headers=u["headers"]).status_code == 403
        assert (
            client.post(
                "/api/v1/operator/staff-grants",
                headers=u["headers"],
                json={"user_id": target["user_id"], "role_code": "OPERATIONS", "reason": "Unauthorized role attempt"},
            ).status_code
            == 403
        )

    # SECURITY_LEAD can read staff-grants (200) but cannot grant or revoke (403)
    sec_read = client.get("/api/v1/operator/staff-grants", headers=sec_lead["headers"])
    assert sec_read.status_code == 200, sec_read.text
    assert sec_read.headers["cache-control"] == "no-store"
    assert (
        client.post(
            "/api/v1/operator/staff-grants",
            headers=sec_lead["headers"],
            json={"user_id": target["user_id"], "role_code": "OPERATIONS", "reason": "Security lead cannot grant"},
        ).status_code
        == 403
    )

    # Self-grant forbidden (403 SELF_ROLE_GRANT_FORBIDDEN)
    self_grant = client.post(
        "/api/v1/operator/staff-grants",
        headers=admin1["headers"],
        json={"user_id": admin1["user_id"], "role_code": "OPERATIONS", "reason": "Trying to self-grant operations"},
    )
    assert self_grant.status_code == 403
    assert self_grant.json()["detail"]["code"] == "SELF_ROLE_GRANT_FORBIDDEN"

    # Non-ACTIVE user rejected (409 TARGET_USER_NOT_ACTIVE)
    suspended = identities()
    with transaction() as conn:
        conn.execute(table("users").update().where(table("users").c.id == suspended["user_id"]).values(status="SUSPENDED"))
    susp_grant = client.post(
        "/api/v1/operator/staff-grants",
        headers=admin1["headers"],
        json={"user_id": suspended["user_id"], "role_code": "OPERATIONS", "reason": "Suspended accounts cannot get roles"},
    )
    assert susp_grant.status_code == 409
    assert susp_grant.json()["detail"]["code"] == "TARGET_USER_NOT_ACTIVE"

    # Password-only session without MFA for an ADMIN is blocked (403)
    pw_only_admin = identities()
    pw_grant_id = _grant_platform_role_in_db(pw_only_admin["user_id"], "ADMIN", admin1["user_id"])
    no_mfa_res = client.post(
        "/api/v1/operator/staff-grants",
        headers=pw_only_admin["headers"],
        json={"user_id": target["user_id"], "role_code": "OPERATIONS", "reason": "MFA required for all admin grants"},
    )
    assert no_mfa_res.status_code == 403
    # Remove temporary pw_only_admin grant so admin1 is genuinely the sole active ADMIN
    with transaction() as conn:
        conn.execute(table("platform_role_grants").delete().where(table("platform_role_grants").c.id == pw_grant_id))

    # Grant OPERATIONS (standing 3650d) -> 201
    granted = client.post(
        "/api/v1/operator/staff-grants",
        headers=admin1["headers"],
        json={
            "user_id": target["user_id"],
            "role_code": "OPERATIONS",
            "reason": "Appointed primary platform operations engineer",
            "duration_days": 3650,
        },
    )
    assert granted.status_code == 201, granted.text
    gdata = granted.json()
    assert gdata["ok"] is True
    assert gdata["role_code"] == "OPERATIONS"

    # Duplicate active grant -> 409 GRANT_ALREADY_ACTIVE
    dup = client.post(
        "/api/v1/operator/staff-grants",
        headers=admin1["headers"],
        json={
            "user_id": target["user_id"],
            "role_code": "OPERATIONS",
            "reason": "Duplicate grant should be rejected cleanly",
        },
    )
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "GRANT_ALREADY_ACTIVE"

    # Verify API-126 response structure (masked contact, is_permanent, role_matrix, granter)
    listing = client.get("/api/v1/operator/staff-grants", headers=admin1["headers"])
    assert listing.status_code == 200
    body = listing.json()
    assert body["ok"] is True
    assert body["contract_id"] == "API-126"
    assert len(body["roles_catalog"]) >= 8
    assert len(body["role_matrix"]) >= 16
    ops_grant = next(g for g in body["active_grants"] if g["id"] == gdata["grant_id"])
    assert ops_grant["is_permanent"] is True
    assert "***" in ops_grant["masked_contact"]
    assert email not in listing.text

    # Last active ADMIN cannot be revoked -> 409 LAST_ADMIN_CANNOT_BE_REVOKED
    with transaction() as conn:
        admin1_grant_id = str(
            conn.execute(
                select(table("platform_role_grants").c.id)
                .select_from(
                    table("platform_role_grants").join(
                        table("role_catalog"), table("platform_role_grants").c.role_id == table("role_catalog").c.id
                    )
                )
                .where(
                    table("platform_role_grants").c.user_id == admin1["user_id"],
                    table("role_catalog").c.code == "ADMIN",
                    table("platform_role_grants").c.revoked_at.is_(None),
                )
            ).scalar_one()
        )

    last_revoke = client.post(
        f"/api/v1/operator/staff-grants/{admin1_grant_id}/revoke",
        headers=admin1["headers"],
        json={"reason": "Attempt to revoke the very last active ADMIN"},
    )
    assert last_revoke.status_code == 409, last_revoke.text
    assert last_revoke.json()["detail"]["code"] == "LAST_ADMIN_CANNOT_BE_REVOKED"

    # Add a second active ADMIN (admin2) -> now 2 active ADMIN grants exist
    admin2 = identities("ADMIN")
    with transaction() as conn:
        admin2_grant_id = str(
            conn.execute(
                select(table("platform_role_grants").c.id)
                .select_from(
                    table("platform_role_grants").join(
                        table("role_catalog"), table("platform_role_grants").c.role_id == table("role_catalog").c.id
                    )
                )
                .where(
                    table("platform_role_grants").c.user_id == admin2["user_id"],
                    table("role_catalog").c.code == "ADMIN",
                    table("platform_role_grants").c.revoked_at.is_(None),
                )
            ).scalar_one()
        )

    # With 2 active ADMINs, admin1 attempting to revoke OWN active ADMIN grant -> 403 SELF_ADMIN_REVOKE_FORBIDDEN
    self_revoke = client.post(
        f"/api/v1/operator/staff-grants/{admin1_grant_id}/revoke",
        headers=admin1["headers"],
        json={"reason": "Attempt to revoke own active ADMIN grant"},
    )
    assert self_revoke.status_code == 403, self_revoke.text
    assert self_revoke.json()["detail"]["code"] == "SELF_ADMIN_REVOKE_FORBIDDEN"

    # admin1 revokes admin2's ADMIN grant -> 200 OK; admin2 immediately loses access; admin1 is last admin again
    revoked = client.post(
        f"/api/v1/operator/staff-grants/{admin2_grant_id}/revoke",
        headers=admin1["headers"],
        json={"reason": "Role rotation completed by primary super admin"},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "REVOKED"
    assert client.get("/api/v1/operator/staff-grants", headers=admin2["headers"]).status_code == 403

    # Verify recent_revoked + audit events
    after_listing = client.get("/api/v1/operator/staff-grants", headers=admin1["headers"]).json()
    assert any(r["id"] == admin2_grant_id for r in after_listing["recent_revoked"])
    with transaction() as conn:
        actions = list(conn.execute(select(table("audit_events").c.action)).scalars())
        assert "PLATFORM_ROLE_GRANTED" in actions
        assert "PLATFORM_ROLE_REVOKED" in actions

    # Existing MODERATOR-only guards on KYC/moderation endpoints stay intact (ADMIN without MODERATOR gets 403)
    assert client.get("/api/v1/operator/verification-cases", headers=admin1["headers"]).status_code == 403


def test_parallel_staff_grants_are_serialized_without_duplicate_active(client, identities):
    admin = identities("ADMIN")
    target = identities()

    def do_grant():
        return client.post(
            "/api/v1/operator/staff-grants",
            headers=admin["headers"],
            json={
                "user_id": target["user_id"],
                "role_code": "AUDITOR",
                "reason": "Concurrent role grant serialization test",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result(timeout=15) for f in (pool.submit(do_grant), pool.submit(do_grant))]

    assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]


def test_directories_search_and_zero_secret_leak(client, identities, organization):
    admin = identities("ADMIN")
    auditor = identities("AUDITOR")
    finance = identities("FINANCE")
    candidate = identities()
    email = f"dir.user.{uuid4().hex[:8]}@flexbridge.test"
    phone = "+998907778899"
    contact(candidate, value=email, channel="EMAIL")
    contact(admin, value=phone, channel="PHONE")

    # Create a real verified institution, active coordinator staff, and verified student enrollment
    _student, inst_id, _coordinator, _student_email = verified_student(client, identities)
    save_domain_record(
        "institution_directory_profile",
        inst_id,
        {"official_name": "Muhammad al-Xorazmiy nomidagi TATU", "short_name": "TATU", "tax_id": "200123456"},
    )

    # Guard enforcement
    assert client.get("/api/v1/operator/directory/users", headers=candidate["headers"]).status_code == 403
    assert client.get("/api/v1/operator/directory/users", headers=finance["headers"]).status_code == 403
    assert client.get("/api/v1/operator/directory/organizations", headers=finance["headers"]).status_code == 403
    assert client.get("/api/v1/operator/directory/institutions", headers=finance["headers"]).status_code == 403

    # Users directory: allowed for AUDITOR/ADMIN, masked contacts only, no secrets
    users_res = client.get(f"/api/v1/operator/directory/users?q={email}", headers=auditor["headers"])
    assert users_res.status_code == 200, users_res.text
    assert email not in users_res.text
    assert "password_hash" not in users_res.text
    assert "totp_secret" not in users_res.text
    assert "secret_encrypted" not in users_res.text
    [u_item] = users_res.json()["items"]
    assert u_item["id"] == candidate["user_id"]
    assert "***" in u_item["masked_contact"]

    admins_res = client.get("/api/v1/operator/directory/users?role=ADMIN", headers=admin["headers"])
    assert admins_res.status_code == 200
    assert any(i["id"] == admin["user_id"] and "ADMIN" in i["platform_roles"] and i["mfa_enabled"] is True for i in admins_res.json()["items"])
    assert all(i["id"] != SYSTEM_AUTHORITY_USER_ID for i in admins_res.json()["items"])

    # Organizations directory
    orgs_res = client.get("/api/v1/operator/directory/organizations?status=VERIFIED", headers=auditor["headers"])
    assert orgs_res.status_code == 200, orgs_res.text
    assert any(o["id"] == organization and o["verification_status"] == "VERIFIED" for o in orgs_res.json()["items"])

    # Institutions directory
    inst_res = client.get("/api/v1/operator/directory/institutions?q=TATU", headers=auditor["headers"])
    assert inst_res.status_code == 200, inst_res.text
    [inst_item] = inst_res.json()["items"]
    assert inst_item["id"] == inst_id
    assert inst_item["short_name"] == "TATU"
    assert inst_item["tax_id"] == "200123456"
    assert inst_item["verified_students_count"] == 1
    assert inst_item["active_staff_count"] == 1


def test_feature_flags_get_matches_patch_if_match_and_protects_locked_flags(client, identities):
    admin = identities("ADMIN")
    auditor = identities("AUDITOR")
    moderator = identities("MODERATOR")

    assert client.get("/api/v1/operator/feature-flags", headers=moderator["headers"]).status_code == 403

    initial = client.get("/api/v1/operator/feature-flags", headers=auditor["headers"])
    assert initial.status_code == 200, initial.text
    by_code = {item["code"]: item for item in initial.json()["items"]}

    assert by_code["R1_PART_TIME_JOBS"]["version"] == 0
    assert by_code["R1_PART_TIME_JOBS"]["enabled"] is False
    assert by_code["R1_PART_TIME_JOBS"]["mutable"] is True
    assert by_code["R1_PART_TIME_JOBS"]["category"] == "R1"

    # Protected & R2 flags stay disabled & non-mutable
    for locked_code in ("ratings", "academic_official_export", "WhatsApp", "paid_checkout", "R2_FREELANCE_MARKETPLACE"):
        assert by_code[locked_code]["enabled"] is False
        assert by_code[locked_code]["mutable"] is False
        assert by_code[locked_code]["disable_only"] is True
    assert by_code["R1_PAID_ORG_PLANS"]["alias_of"] == "paid_checkout"

    # Cannot enable protected or R2 flags via PATCH
    assert (
        client.patch(
            "/api/v1/operator/feature-flags/paid_checkout",
            headers={**admin["headers"], "Idempotency-Key": str(uuid4()), "If-Match": '"0"'},
            json={"enabled": True, "reason": "Attempting to enable protected checkout flag"},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            "/api/v1/operator/feature-flags/R2_FREELANCE_MARKETPLACE",
            headers={**admin["headers"], "Idempotency-Key": str(uuid4()), "If-Match": '"0"'},
            json={"enabled": True, "reason": "Attempting to enable R2 marketplace flag"},
        ).status_code
        == 409
    )
    # Disabling paid_checkout records version 1 while keeping enabled=False
    dis_paid = client.patch(
        "/api/v1/operator/feature-flags/paid_checkout",
        headers={**admin["headers"], "Idempotency-Key": str(uuid4()), "If-Match": f'"{by_code["paid_checkout"]["version"]}"'},
        json={"enabled": False, "reason": "Explicitly confirm paid checkout disabled in R1"},
    )
    assert dis_paid.status_code == 200, dis_paid.text
    after_paid = {i["code"]: i for i in client.get("/api/v1/operator/feature-flags", headers=auditor["headers"]).json()["items"]}
    assert after_paid["paid_checkout"]["version"] == 1
    assert after_paid["paid_checkout"]["enabled"] is False

    # PATCH R1_PART_TIME_JOBS using version from GET (0 -> 1 -> 2)
    p1 = client.patch(
        "/api/v1/operator/feature-flags/R1_PART_TIME_JOBS",
        headers={**admin["headers"], "Idempotency-Key": str(uuid4()), "If-Match": f'"{by_code["R1_PART_TIME_JOBS"]["version"]}"'},
        json={"enabled": True, "reason": "Enable R1 part-time jobs for pilot launch"},
    )
    assert p1.status_code == 200, p1.text

    after1 = {i["code"]: i for i in client.get("/api/v1/operator/feature-flags", headers=admin["headers"]).json()["items"]}
    assert after1["R1_PART_TIME_JOBS"]["version"] == 1
    assert after1["R1_PART_TIME_JOBS"]["enabled"] is True

    p2 = client.patch(
        "/api/v1/operator/feature-flags/R1_PART_TIME_JOBS",
        headers={**admin["headers"], "Idempotency-Key": str(uuid4()), "If-Match": f'"{after1["R1_PART_TIME_JOBS"]["version"]}"'},
        json={"enabled": False, "reason": "Disable R1 part-time jobs after smoke check"},
    )
    assert p2.status_code == 200, p2.text

    after2 = {i["code"]: i for i in client.get("/api/v1/operator/feature-flags", headers=admin["headers"]).json()["items"]}
    assert after2["R1_PART_TIME_JOBS"]["version"] == 2
    assert after2["R1_PART_TIME_JOBS"]["enabled"] is False


def test_privacy_requests_operator_list(client, identities):
    candidate = identities()
    compliance = identities("COMPLIANCE")
    auditor = identities("AUDITOR")

    created = client.post(
        "/api/v1/me/privacy-requests",
        headers=candidate["headers"],
        json={"kind": "EXPORT", "reason": "Personal archive copy"},
    )
    assert created.status_code in (200, 201), created.text

    assert client.get("/api/v1/operator/privacy-requests", headers=auditor["headers"]).status_code == 403
    assert client.get("/api/v1/operator/privacy-requests", headers=candidate["headers"]).status_code == 403

    listed = client.get("/api/v1/operator/privacy-requests?status=PENDING", headers=compliance["headers"])
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == created.json()["id"]
    assert items[0]["user_id"] == candidate["user_id"]
    assert items[0]["kind"] == "EXPORT"
    assert items[0]["status"] == "PENDING"


def test_operator_recovery_requests_exclude_self_approve_and_identity_72h_consume(client, identities, delivery):
    support = identities("SUPPORT")
    admin = identities("ADMIN")
    moderator = identities("MODERATOR")
    student = identities()

    student_email = f"student.rec.{uuid4().hex[:8]}@flexbridge.test"
    support_email = f"support.rec.{uuid4().hex[:8]}@flexbridge.test"
    contact(student, value=student_email, channel="EMAIL")
    contact(support, value=support_email, channel="EMAIL")

    # Student submits OTP-only recovery -> PENDING_REVIEW
    s_token = proof(client, delivery, purpose="RECOVERY", destination=student_email, channel="EMAIL")
    s_req = client.post("/api/v1/auth/recovery", json={"verification_token": s_token})
    assert s_req.status_code == 202, s_req.text
    student_rid = s_req.json()["recovery_id"]

    # Support operator also submits own recovery -> must be hidden from Support's own queue & blocked from self-decide
    sup_token = proof(client, delivery, purpose="RECOVERY", destination=support_email, channel="EMAIL")
    sup_req = client.post("/api/v1/auth/recovery", json={"verification_token": sup_token})
    assert sup_req.status_code == 202, sup_req.text
    support_rid = sup_req.json()["recovery_id"]

    # Non-SUPPORT/ADMIN role forbidden
    assert client.get("/api/v1/operator/recovery-requests", headers=moderator["headers"]).status_code == 403

    # Support sees student request, NOT own request; contacts are masked
    queue = client.get("/api/v1/operator/recovery-requests?status=PENDING_REVIEW", headers=support["headers"])
    assert queue.status_code == 200, queue.text
    ids = [i["id"] for i in queue.json()["items"]]
    assert student_rid in ids
    assert support_rid not in ids
    assert student_email not in queue.text
    [item] = [i for i in queue.json()["items"] if i["id"] == student_rid]
    assert "***" in item["masked_contacts"][0]["masked"]

    # Self-review attempt by Support on support_rid -> 403 SELF_REVIEW_FORBIDDEN
    self_decide = client.post(
        f"/api/v1/operator/recovery-requests/{support_rid}/decide",
        headers=support["headers"],
        json={"decision": "APPROVE", "reason": "Self-review attempt should never be permitted"},
    )
    assert self_decide.status_code == 403
    assert self_decide.json()["detail"]["code"] == "SELF_REVIEW_FORBIDDEN"

    # Admin approves student recovery request -> APPROVED + valid_until (72h)
    decided = client.post(
        f"/api/v1/operator/recovery-requests/{student_rid}/decide",
        headers=admin["headers"],
        json={"decision": "APPROVE", "reason": "Verified applicant identity via official support call"},
    )
    assert decided.status_code == 200, decided.text
    ddata = decided.json()
    assert ddata["ok"] is True
    assert ddata["status"] == "APPROVED"
    assert ddata["valid_until"] is not None

    # Audit event recorded
    with transaction() as conn:
        audit_row = conn.execute(
            select(table("audit_events")).where(
                table("audit_events").c.action == "ACCOUNT_RECOVERY_APPROVED_BY_OPERATOR",
                table("audit_events").c.object_key == student_rid,
            )
        ).mappings().first()
        assert audit_row is not None

    # Student restarts recovery with same contact within 72h -> identity.request_recovery consumes approval -> READY_TO_RESET
    _age_challenges()
    token2 = proof(client, delivery, purpose="RECOVERY", destination=student_email, channel="EMAIL")
    ready = client.post("/api/v1/auth/recovery", json={"verification_token": token2})
    assert ready.status_code == 202, ready.text
    assert ready.json()["status"] == "READY_TO_RESET"
    assert ready.json()["reset_token"]

    new_pw = "Operator-Recovered-Student-2026!"
    done = client.post(
        f"/api/v1/auth/recovery/{ready.json()['recovery_id']}/complete",
        json={"reset_token": ready.json()["reset_token"], "new_password": new_pw},
    )
    assert done.status_code == 200, done.text
    assert client.post("/api/v1/auth/login", json={"user_id": student["user_id"], "password": new_pw}).status_code == 200

    # Approval was single-use (CONSUMED)
    with transaction() as conn:
        st = conn.execute(select(table("recovery_requests").c.status).where(table("recovery_requests").c.id == student_rid)).scalar_one()
        assert st == "CONSUMED"

    # REJECT decision sets REJECTED and does not unlock recovery
    _age_challenges()
    tok_rej = proof(client, delivery, purpose="RECOVERY", destination=student_email, channel="EMAIL")
    rej_req = client.post("/api/v1/auth/recovery", json={"verification_token": tok_rej})
    assert rej_req.status_code == 202
    rej_id = rej_req.json()["recovery_id"]
    rejected = client.post(
        f"/api/v1/operator/recovery-requests/{rej_id}/decide",
        headers=support["headers"],
        json={"decision": "REJECT", "reason": "Applicant failed secondary ownership verification"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["valid_until"] is None
    _age_challenges()
    tok_after_rej = proof(client, delivery, purpose="RECOVERY", destination=student_email, channel="EMAIL")
    after_rej = client.post("/api/v1/auth/recovery", json={"verification_token": tok_after_rej})
    assert after_rej.json()["status"] == "PENDING_REVIEW"
