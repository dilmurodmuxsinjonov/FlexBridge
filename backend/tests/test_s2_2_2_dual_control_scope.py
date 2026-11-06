"""Automated test suite for S2.2.2 & FIX-03/04: Dual-Control (`INV-11`), Server-Side `ActorContext` Scope (`INV-12`, `R-01`), Canonical `API-060`/`API-061`, and Moderation (`AC-041`)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import auth_service
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
    """Verify server-side `ActorContext` (`R-01`), institution/supervisor scope (`AC-041`), and canonical `API-060`/`API-061`."""
    sup = governance_service.register_student_supervision(
        institution_id="inst-tuit",
        student_id="student-1",
        supervisor_id="teacher-tuit-1",
    )

    teacher_tuit_token = auth_service.seed_privileged_actor_session(
        user_id="teacher-tuit-1",
        roles=["ACADEMIC_SUPERVISOR"],
        institution_id="inst-tuit",
    )
    coord_tuit_token = auth_service.seed_privileged_actor_session(
        user_id="coord-tuit-1",
        roles=["INST_INTERNSHIP_COORDINATOR"],
        institution_id="inst-tuit",
    )
    teacher_inha_token = auth_service.seed_privileged_actor_session(
        user_id="teacher-inha-1",
        roles=["ACADEMIC_SUPERVISOR"],
        institution_id="inst-inha",
    )

    # Unauthenticated call without Authorization header must fail with 401 AUTH_REQUIRED (R-01)
    unauth_resp = client.post(
        "/api/v1/internships/academic-assignments",
        json={
            "actor_id": "invented-admin",
            "actor_role": "SUPER_ADMIN",
            "institution_id": "inst-tuit",
            "placement_id": "placement-1",
            "supervision_id": sup["id"],
            "supervisor_id": "teacher-tuit-1",
        },
    )
    assert unauth_resp.status_code == 401

    # Called by authenticated ACADEMIC_SUPERVISOR must be rejected with 403
    forbidden_060 = client.post(
        "/api/v1/internships/academic-assignments",
        headers={"Authorization": f"Bearer {teacher_tuit_token}"},
        json={
            "actor_institution_id": "inst-tuit",
            "institution_id": "inst-tuit",
            "placement_id": "placement-1",
            "supervision_id": sup["id"],
            "supervisor_id": "teacher-tuit-1",
        },
    )
    assert forbidden_060.status_code == 403
    assert forbidden_060.json()["detail"]["code"] == "FORBIDDEN_ROLE_FOR_API_060"

    # Called by authenticated INST_INTERNSHIP_COORDINATOR of the same institution succeeds
    ok_060 = client.post(
        "/api/v1/internships/academic-assignments",
        headers={"Authorization": f"Bearer {coord_tuit_token}"},
        json={
            "actor_institution_id": "inst-tuit",
            "institution_id": "inst-tuit",
            "placement_id": "placement-1",
            "supervision_id": sup["id"],
            "supervisor_id": "teacher-tuit-1",
        },
    )
    assert ok_060.status_code == 201
    assignment_id = ok_060.json()["id"]

    # Called by a supervisor from another institution (`inst-inha`) fails with 403 SCOPE_VIOLATION
    cross_inst_061 = client.patch(
        f"/api/v1/internships/academic-assignments/{assignment_id}",
        headers={"Authorization": f"Bearer {teacher_inha_token}"},
        json={
            "actor_institution_id": "inst-inha",
            "evaluation_note": "Begona oliygoh kirishi",
        },
    )
    assert cross_inst_061.status_code == 403
    assert cross_inst_061.json()["detail"]["code"] == "SCOPE_VIOLATION"

    # Called by the assigned supervisor (`teacher-tuit-1`) of `inst-tuit` succeeds
    ok_061 = client.patch(
        f"/api/v1/internships/academic-assignments/{assignment_id}",
        headers={"Authorization": f"Bearer {teacher_tuit_token}"},
        json={
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
