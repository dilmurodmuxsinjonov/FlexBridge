"""Adversarial and security tests for Institution Summary Report Exports (API-100)."""

from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.storage import table, transaction
from test_academic_admission import pending_http
from test_academic_authority import academic_fixture
from test_candidate import cv_fixture
from test_institution_authority import setup_scope


def test_adversarial_unauthenticated_denied(client, organization, identities):
    """Anonymous requests without credentials return 401."""
    f = academic_fixture(identities, organization)
    inst_id = f["inst"]["id"]

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        json={"format": "JSON", "idempotency_key": "inst-unauth-12345"},
    )
    assert res.status_code == 401, res.text


def test_adversarial_unauthorized_member_forbidden(client, identities, organization):
    """TEACHER cannot perform institutional coordinator exports -> 403 INSTITUTION_SCOPE_FORBIDDEN."""
    f = academic_fixture(identities, organization)
    inst_id = f["inst"]["id"]
    teacher = f["teacher"]

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=teacher["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-teacher-{uuid4()}"},
    )
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["code"] == "INSTITUTION_SCOPE_FORBIDDEN"


def test_adversarial_cross_tenant_denied_uniform_404(client, identities, organization):
    """Coordinator from Institution A cannot access Institution B -> 404 (anti-enumeration)."""
    f_a = academic_fixture(identities, organization)
    f_b = academic_fixture(identities, organization)

    inst_b_id = f_b["inst"]["id"]
    coord_a = f_a["coord"]

    res = client.post(
        f"/api/v1/institutions/{inst_b_id}/exports",
        headers=coord_a["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-cross-{uuid4()}"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "INSTITUTION_NOT_FOUND"


def test_adversarial_nonexistent_or_unverified_uniform_404(client, identities, organization):
    """Random nonexistent institution UUID returns uniform 404."""
    f = academic_fixture(identities, organization)
    coord = f["coord"]
    fake_inst_id = str(uuid4())

    res = client.post(
        f"/api/v1/institutions/{fake_inst_id}/exports",
        headers=coord["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-fake-{uuid4()}"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "INSTITUTION_NOT_FOUND"


def test_adversarial_candidate_denied_uniform_404(client, identities, organization):
    """Candidate/student cannot export institutional summary -> 404 (cross-tenant anti-enumeration)."""
    f = academic_fixture(identities, organization)
    inst_id = f["inst"]["id"]
    candidate = f["candidate"]

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=candidate["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-cand-{uuid4()}"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "INSTITUTION_NOT_FOUND"


def test_adversarial_host_employer_denied_uniform_404(client, identities, organization):
    """Host employer owner cannot export institutional summary -> 404 (cross-tenant anti-enumeration)."""
    f = academic_fixture(identities, organization)
    inst_id = f["inst"]["id"]
    owner = f["owner"]

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=owner["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-owner-{uuid4()}"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "INSTITUTION_NOT_FOUND"


def test_adversarial_non_mfa_coordinator_step_up_required(client, identities, organization):
    """Coordinator session without MFA step-up assurance is rejected with 403 MFA_REQUIRED."""
    f = academic_fixture(identities, organization)
    inst_id = f["inst"]["id"]
    coord = f["coord"]

    # Downgrade session assurance to PASSWORD
    with transaction() as conn:
        conn.execute(
            text("UPDATE flexbridge.sessions SET assurance = 'PASSWORD' WHERE id = :sid"),
            {"sid": coord["session_id"]},
        )

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-nomfa-{uuid4()}"},
    )
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["code"] == "MFA_REQUIRED"


def test_adversarial_invalid_format_and_idempotency_key(client, identities, organization):
    """Invalid format returns 422; invalid key length returns 422."""
    f = academic_fixture(identities, organization)
    coord = f["coord"]
    inst_id = f["inst"]["id"]

    # Invalid format (e.g. CSV)
    res_fmt = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "CSV", "idempotency_key": f"inst-key-{uuid4()}"},
    )
    assert res_fmt.status_code == 422, res_fmt.text

    # Too short idempotency key (<8 chars)
    res_short = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "JSON", "idempotency_key": "short"},
    )
    assert res_short.status_code == 422, res_short.text


def test_adversarial_idempotency_actor_mismatch(client, identities, organization):
    """Different coordinator attempting to reuse another coordinator's idempotency key receives 403."""
    f = academic_fixture(identities, organization)
    coord1 = f["coord"]
    inst_id = f["inst"]["id"]

    # Setup second coordinator with valid cv file in files table
    coord2, _, _, _, _, _, _ = setup_scope(identities)
    doc_file = cv_fixture(coord2)

    with transaction() as conn:
        from test_academic_authority import insert_row
        tm = insert_row(
            conn,
            "institution_memberships",
            institution_id=inst_id,
            user_id=coord2["user_id"],
            status="ACTIVE",
            accepted_at=text("clock_timestamp()"),
        )
        ta = insert_row(
            conn,
            "institution_appointments",
            institution_id=inst_id,
            user_id=coord2["user_id"],
            document_file_id=doc_file["id"],
            status="ACTIVE",
            valid_from=text("CURRENT_DATE - 30"),
            valid_to=text("CURRENT_DATE + 30"),
            accepted_at=text("clock_timestamp()"),
        )
        roles = table("role_catalog")
        rid = conn.execute(
            select(roles.c.id).where(
                roles.c.code == "COORDINATOR",
                roles.c.scope_kind == "INSTITUTION",
            )
        ).scalar_one()
        insert_row(
            conn,
            "institution_role_grants",
            membership_id=tm["id"],
            role_id=rid,
            appointment_id=ta["id"],
        )

    key = f"inst-shared-key-{uuid4()}"
    # Coordinator 1 creates export
    res1 = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord1["headers"],
        json={"format": "JSON", "idempotency_key": key},
    )
    assert res1.status_code == 201, res1.text

    # Coordinator 2 attempts to use same key -> 403 IDEMPOTENCY_ACTOR_MISMATCH
    res2 = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord2["headers"],
        json={"format": "JSON", "idempotency_key": key},
    )
    assert res2.status_code == 403, res2.text
    assert res2.json()["detail"]["code"] == "IDEMPOTENCY_ACTOR_MISMATCH"
