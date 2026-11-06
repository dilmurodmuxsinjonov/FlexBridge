"""Automated test suite for S2.2.2: Dual-Control (`INV-11`), Scope Authorization (`INV-12`), `API-060`/`API-061`, and Moderation (`AC-041`)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.governance import governance_service

client = TestClient(app)


def test_inv_11_dual_control_blocks_self_approval_and_cross_org_scope() -> None:
    """Verify `INV-11` rejects self-approval (`409 SELF_APPROVAL_FORBIDDEN`) and `INV-12` blocks cross-org approval (`403 SCOPE_VIOLATION`)."""
    create_resp = client.post(
        "/api/v1/organizations/org-alpha/members",
        json={
            "user_id": "recruiter-candidate-1",
            "role_code": "ORG_RECRUITER",
            "created_by": "admin-alpha-1",
        },
    )
    assert create_resp.status_code == 201
    member_id = create_resp.json()["id"]

    # 1. Self-approval by `admin-alpha-1` must fail with 409 SELF_APPROVAL_FORBIDDEN
    self_app = client.post(
        f"/api/v1/organizations/org-alpha/members/{member_id}/approve",
        json={"approved_by": "admin-alpha-1", "approver_org_id": "org-alpha"},
    )
    assert self_app.status_code == 409
    assert self_app.json()["detail"]["code"] == "SELF_APPROVAL_FORBIDDEN"

    # 2. Cross-org approval by an admin of `org-beta` must fail with 403 SCOPE_VIOLATION
    cross_org = client.post(
        f"/api/v1/organizations/org-alpha/members/{member_id}/approve",
        json={"approved_by": "admin-beta-1", "approver_org_id": "org-beta"},
    )
    assert cross_org.status_code == 403
    assert cross_org.json()["detail"]["code"] == "SCOPE_VIOLATION"

    # 3. Approval by a second admin of `org-alpha` (`admin-alpha-2`) succeeds
    ok_app = client.post(
        f"/api/v1/organizations/org-alpha/members/{member_id}/approve",
        json={"approved_by": "admin-alpha-2", "approver_org_id": "org-alpha"},
    )
    assert ok_app.status_code == 200
    assert ok_app.json()["status"] == "ACTIVE"
    assert ok_app.json()["approved_by"] == "admin-alpha-2"


def test_api_060_and_api_061_role_and_institution_scope_ac_041() -> None:
    """Verify `API-060` rejects `ACADEMIC_SUPERVISOR` (`403`) and `API-061` enforces institution/supervisor scope (`AC-041`)."""
    sup = governance_service.register_student_supervision(
        institution_id="inst-tuit",
        student_id="student-1",
        supervisor_id="teacher-tuit-1",
    )

    # API-060 called by ACADEMIC_SUPERVISOR must be rejected per 1.4 PDF section 4
    forbidden_060 = client.post(
        "/api/v1/internships/academic-assignments",
        json={
            "actor_id": "teacher-tuit-1",
            "actor_role": "ACADEMIC_SUPERVISOR",
            "actor_institution_id": "inst-tuit",
            "institution_id": "inst-tuit",
            "placement_id": "placement-1",
            "supervision_id": sup["id"],
            "supervisor_id": "teacher-tuit-1",
        },
    )
    assert forbidden_060.status_code == 403
    assert forbidden_060.json()["detail"]["code"] == "FORBIDDEN_ROLE_FOR_API_060"

    # API-060 called by INST_INTERNSHIP_COORDINATOR of the same institution succeeds
    ok_060 = client.post(
        "/api/v1/internships/academic-assignments",
        json={
            "actor_id": "coord-tuit-1",
            "actor_role": "INST_INTERNSHIP_COORDINATOR",
            "actor_institution_id": "inst-tuit",
            "institution_id": "inst-tuit",
            "placement_id": "placement-1",
            "supervision_id": sup["id"],
            "supervisor_id": "teacher-tuit-1",
        },
    )
    assert ok_060.status_code == 201
    assignment_id = ok_060.json()["id"]

    # API-061 called by a supervisor from another institution (`inst-inha`) fails with 403 SCOPE_VIOLATION
    cross_inst_061 = client.patch(
        f"/api/v1/internships/academic-assignments/{assignment_id}",
        json={
            "actor_id": "teacher-inha-1",
            "actor_role": "ACADEMIC_SUPERVISOR",
            "actor_institution_id": "inst-inha",
            "evaluation_note": "Begona oliygoh kirishi",
        },
    )
    assert cross_inst_061.status_code == 403
    assert cross_inst_061.json()["detail"]["code"] == "SCOPE_VIOLATION"

    # API-061 called by the assigned supervisor (`teacher-tuit-1`) of `inst-tuit` succeeds
    ok_061 = client.patch(
        f"/api/v1/internships/academic-assignments/{assignment_id}",
        json={
            "actor_id": "teacher-tuit-1",
            "actor_role": "ACADEMIC_SUPERVISOR",
            "actor_institution_id": "inst-tuit",
            "status": "COMPLETED",
            "evaluation_note": "Talaba akademik amaliyot rejasini to'liq bajardi.",
        },
    )
    assert ok_061.status_code == 200
    assert ok_061.json()["status"] == "COMPLETED"


def test_moderation_action_requires_policy_reason_and_justification_ac_041() -> None:
    """Verify `AC-041` rejects moderation actions without policy_code, reason_code, or >=15 char justification."""
    bad_mod = client.post(
        "/api/v1/moderation/actions",
        json={
            "actor_id": "mod-1",
            "target_entity_type": "opportunity",
            "target_entity_id": "opp-1",
            "action_type": "REJECT",
            "policy_code": "POL-JOB-01",
            "reason_code": "FAKE_SALARY",
            "justification": "Qisqa izoh",
        },
    )
    assert bad_mod.status_code == 422
    assert bad_mod.json()["detail"]["code"] == "MODERATION_JUSTIFICATION_REQUIRED"

    ok_mod = client.post(
        "/api/v1/moderation/actions",
        json={
            "actor_id": "mod-1",
            "target_entity_type": "opportunity",
            "target_entity_id": "opp-1",
            "action_type": "REJECT",
            "policy_code": "POL-JOB-01",
            "reason_code": "FAKE_SALARY",
            "justification": "E'londa ko'rsatilgan maosh va smena shartlari POL-JOB-01 qoidasiga zid.",
        },
    )
    assert ok_mod.status_code == 201
    assert ok_mod.json()["policy_code"] == "POL-JOB-01"
