"""Contract and verification tests for Placement Plan & Assignment Canonicalization (API-050, API-051, API-030 / CAP-018, CAP-022)."""

from uuid import uuid4

import pytest

from test_academic_authority import academic_fixture, actor
from test_organizations import actor as org_actor
from app.services.internship_logs import internship_log_service as log_service
from app.services.placement_admission import admission_service
from app.db.storage import transaction
from app.services.placements import get_row


def test_placement_plan_api050_returns_contract_id(client, identities, organization):
    """API-050: Candidate and owner view placement plan with contract_id API-050."""
    f = academic_fixture(identities, organization)
    placement_id = f["placement"]["id"]

    # Candidate view
    res = client.get(f"/api/v1/placements/{placement_id}/plan", headers=f["candidate"]["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-050"
    assert data["placement_id"] == placement_id
    assert "tasks" in data
    assert "version" in data

    # Owner view
    res_owner = client.get(f"/api/v1/placements/{placement_id}/plan", headers=f["owner"]["headers"])
    assert res_owner.status_code == 200, res_owner.text
    assert res_owner.json()["contract_id"] == "API-050"


def test_placement_plan_api050_unauthorized_uniform_404(client, identities, organization):
    """API-050 IDOR: Third party receives uniform 404 PLACEMENT_NOT_FOUND."""
    f = academic_fixture(identities, organization)
    placement_id = f["placement"]["id"]
    outsider = identities()

    res = client.get(f"/api/v1/placements/{placement_id}/plan", headers=outsider["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "PLACEMENT_NOT_FOUND"


def test_mentor_assignment_accept_api051_contract_id(client, identities, organization):
    """API-051: Personally accepted mentor assignment returns receipt stamped with API-051."""
    f = academic_fixture(identities, organization)
    p_id = f["placement"]["id"]
    with transaction() as conn:
        p = get_row(conn, "placements", p_id)
        terms = get_row(conn, "placement_terms", p["current_terms_id"])

    # Nominate owner as mentor
    mentor = admission_service.nominate_mentor(
        actor=org_actor(f["owner"]),
        placement_id=p_id,
        organization_id=organization,
        mentor_id=f["owner"]["user_id"],
        idempotency_key=str(uuid4()),
    )

    payload = {
        "terms_id": terms["id"],
        "version": terms["version"],
        "idempotency_key": str(uuid4()),
        "assignment_kind": "MENTOR",
    }

    res = client.post(
        f"/api/v1/placements/{p_id}/assignments/{mentor['id']}/accept",
        json=payload,
        headers=f["owner"]["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-051"
    assert data["placement_id"] == p_id
    assert data["side"] == "MENTOR"
    assert "consent_id" in data


def test_teacher_assignment_accept_api051_contract_id(client, identities, organization):
    """API-051: Personally accepted academic teacher assignment returns receipt stamped with API-051."""
    f = academic_fixture(identities, organization)
    p_id = f["placement"]["id"]

    assignment = log_service.create_academic_assignment(
        actor=actor(f["coord"]),
        placement_id=p_id,
        institution_id=f["inst"]["id"],
        supervisor_id=f["teacher_member"]["id"],
        supervision_id=f["supervision"]["id"],
        idempotency_key=str(uuid4()),
    )

    with transaction() as conn:
        p = get_row(conn, "placements", p_id)
        terms = get_row(conn, "placement_terms", p["current_terms_id"])

    payload = {
        "terms_id": terms["id"],
        "version": terms["version"],
        "idempotency_key": str(uuid4()),
        "assignment_kind": "TEACHER",
    }

    res = client.post(
        f"/api/v1/placements/{p_id}/assignments/{assignment['id']}/accept",
        json=payload,
        headers=f["teacher"]["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-051"
    assert data["placement_id"] == p_id
    assert "consent_id" in data


def test_own_placements_api030_contract_id(client, identities, organization):
    """API-030: Candidate listing their own placements receives contract_id API-030."""
    f = academic_fixture(identities, organization)

    res = client.get("/api/v1/me/placements", headers=f["candidate"]["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-030"
    assert "items" in data
    assert any(item["id"] == f["placement"]["id"] for item in data["items"])
