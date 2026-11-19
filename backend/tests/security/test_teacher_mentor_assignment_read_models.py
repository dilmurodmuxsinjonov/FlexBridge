"""Security & contract tests for employer placement creation read model and university teacher assignment flow."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.enrollments import enrollment_service
from app.services.opportunities import opportunity_service
from app.services.placements import placement_service
from test_academic_authority import academic_fixture
from test_candidate import cv_fixture
from test_institution_authority import setup_scope
from test_institution_onboarding import first_claim, submit as submit_institution_claim
from test_organizations import actor


def test_hr_detail_exposes_latest_offer_and_placement_id(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()

    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Academic internship",
        opportunity_kind="ACADEMIC_INTERNSHIP",
        contract_type="ACADEMIC_TRIPARTITE",
        compensation_type="UNPAID_ACADEMIC",
        actor_user_id=owner["user_id"],
    )
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == rev["opportunity_id"])
            .values(status="PUBLISHED")
        )

    app = placement_service.create_application(
        opportunity_id=rev["opportunity_id"],
        candidate_id=candidate["candidate_id"],
        actor_user_id=candidate["user_id"],
    )
    placement_service.create_application_attempt(
        application_id=app["id"],
        opportunity_id=rev["opportunity_id"],
        actor_user_id=candidate["user_id"],
    )

    before_offer = client.get(f"/api/v1/applications/{app['id']}/hr", headers=owner["headers"])
    assert before_offer.status_code == 200, before_offer.text
    assert before_offer.json()["latest_offer"] is None
    assert before_offer.json()["placement_id"] is None

    offer = placement_service.create_offer(
        application_id=app["id"],
        opportunity_id=rev["opportunity_id"],
        candidate_id=candidate["candidate_id"],
        offered_by=owner["user_id"],
    )
    after_offer = client.get(f"/api/v1/applications/{app['id']}/hr", headers=owner["headers"])
    assert after_offer.status_code == 200, after_offer.text
    assert after_offer.json()["latest_offer"] == {"id": offer["id"], "status": "PENDING"}
    assert after_offer.json()["placement_id"] is None

    placement_service.respond_to_offer_api_043(
        offer_id=offer["id"],
        candidate_id=candidate["candidate_id"],
        decision="ACCEPT",
    )
    after_accept = client.get(f"/api/v1/applications/{app['id']}/hr", headers=owner["headers"])
    assert after_accept.status_code == 200, after_accept.text
    assert after_accept.json()["latest_offer"] == {"id": offer["id"], "status": "ACCEPTED"}
    assert after_accept.json()["placement_id"] is None

    plc_res = client.post(
        "/api/v1/placements",
        headers=owner["headers"],
        json={
            "application_id": app["id"],
            "offer_id": offer["id"],
            "opportunity_id": rev["opportunity_id"],
            "candidate_id": candidate["candidate_id"],
            "organization_id": organization,
            "idempotency_key": str(uuid4()),
        },
    )
    assert plc_res.status_code == 201, plc_res.text
    plc = plc_res.json()

    after_plc = client.get(f"/api/v1/applications/{app['id']}/hr", headers=owner["headers"])
    assert after_plc.status_code == 200, after_plc.text
    assert after_plc.json()["placement_id"] == plc["id"]


def test_coordinator_supervision_and_teacher_assignment_http_flow(client, identities, organization):
    f = academic_fixture(identities, organization, make_supervision=False)
    plc = f["placement"]

    req_res = client.post(
        f"/api/v1/placements/{plc['id']}/academic-requests",
        headers=f["candidate"]["headers"],
        json={
            "enrollment_id": f["enrollment"]["id"],
            "terms_id": plc["current_terms_id"],
            "version": plc["version"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert req_res.status_code == 201, req_res.text

    q_res = client.get(
        f"/api/v1/institutions/{f['inst']['id']}/assignment-queue",
        headers=f["coord"]["headers"],
    )
    assert q_res.status_code == 200, q_res.text
    queue_item = next(it for it in q_res.json()["items"] if it["placement_id"] == plc["id"])
    assert queue_item["id"] != plc["id"]

    sup_res = client.post(
        "/api/v1/student-supervisions",
        headers=f["coord"]["headers"],
        json={
            "institution_id": f["inst"]["id"],
            "enrollment_id": queue_item["enrollment_id"],
            "agreement_id": f["agreement"]["id"],
            "purpose": "ACADEMIC_VIEW",
            "legal_basis": "OTM akademik amaliyot rahbarligi tayinlovi",
            "idempotency_key": str(uuid4()),
        },
    )
    assert sup_res.status_code == 201, sup_res.text
    sup_id = sup_res.json()["id"]

    asg_res = client.post(
        f"/api/v1/placements/{plc['id']}/academic-assignments",
        headers=f["coord"]["headers"],
        json={
            "institution_id": f["inst"]["id"],
            "supervisor_id": f["teacher_member"]["id"],
            "supervision_id": sup_id,
            "idempotency_key": str(uuid4()),
        },
    )
    assert asg_res.status_code == 201, asg_res.text

    own_res = client.get("/api/v1/me/academic-assignments", headers=f["teacher"]["headers"])
    assert own_res.status_code == 200, own_res.text
    assert any(item["id"] == asg_res.json()["id"] for item in own_res.json()["items"])


def test_verified_enrollment_allows_academic_internship_application(client, identities, organization):
    _, _, inst, _, _, _, _ = setup_scope(identities)
    owner = identities("OWNER", organization)
    reviewer = identities("MODERATOR")
    unenrolled = identities()
    student = identities()
    today = now().astimezone(TASHKENT).date()

    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Academic dual opportunity",
        opportunity_kind="ACADEMIC_INTERNSHIP",
        contract_type="ACADEMIC_TRIPARTITE",
        compensation_type="UNPAID_ACADEMIC",
        actor_user_id=owner["user_id"],
    )
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == rev["opportunity_id"])
            .values(status="PUBLISHED")
        )

    blocked = client.post(
        f"/api/v1/opportunities/{rev['opportunity_id']}/applications",
        headers=unenrolled["headers"] | {"Idempotency-Key": f"idem-blocked-{uuid4()}"},
        json={},
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["detail"]["code"] == "STUDENT_ENROLLMENT_REQUIRED"

    proof = cv_fixture(student)
    enr_req = enrollment_service.create(
        actor(student),
        institution_id=inst["id"],
        idempotency_key=f"enr-{uuid4()}",
        program="Software Engineering",
        start_date=today - timedelta(days=30),
        file_ids=[proof["id"]],
        evidence_note="Verified active student enrollment certificate from university.",
    )
    enrollment_service.claim(actor(reviewer), enr_req["case_id"])
    enrollment_service.decide(
        actor(reviewer),
        enr_req["case_id"],
        decision="APPROVE",
        expected_revision=1,
        reason="Official university enrollment document verified by moderator.",
    )

    allowed = client.post(
        f"/api/v1/opportunities/{rev['opportunity_id']}/applications",
        headers=student["headers"] | {"Idempotency-Key": f"idem-ok-{uuid4()}"},
        json={"enrollment_id": enr_req["id"]},
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["status"] == "SUBMITTED"


def test_operator_verification_queue_includes_institution_appointment_metadata(client, identities):
    flow = first_claim(identities)
    created = submit_institution_claim(client, flow)
    assert created.status_code == 202, created.text
    case_id = created.json()["case_id"]

    moderator = identities("MODERATOR")
    queue = client.get("/api/v1/operator/verification-cases?unassigned=true", headers=moderator["headers"])
    assert queue.status_code == 200, queue.text
    item = next(row for row in queue.json()["items"] if row["id"] == case_id)
    assert item["kind"] == "INSTITUTION_APPOINTMENT"
    assert item["institution_name"] == "Reviewed Academic Institution"
    assert item["current_revision"] == 1
    assert item["assigned_reviewer_id"] is None


def test_plan_read_model_exposes_candidate_and_host_acceptance_timestamps(client, identities, organization):
    from test_admission_lifecycle import planned, publish, terms_request

    candidate, host, mentor, p, assignment = planned(client, identities, organization)
    plan_v2 = publish(client, host, p)

    before = client.get(f"/api/v1/placements/{p['id']}/plan", headers=candidate["headers"])
    assert before.status_code == 200, before.text
    assert before.json()["candidate_accepted_at"] is None
    assert before.json()["host_accepted_at"] is None

    acc = client.post(
        f"/api/v1/placements/{p['id']}/accept",
        headers=candidate["headers"],
        json=terms_request(plan_v2),
    )
    assert acc.status_code == 200, acc.text

    after_cand = client.get(f"/api/v1/placements/{p['id']}/plan", headers=candidate["headers"])
    assert after_cand.status_code == 200, after_cand.text
    assert after_cand.json()["candidate_accepted_at"] is not None
    assert after_cand.json()["host_accepted_at"] is None

    m_acc = client.post(
        f"/api/v1/placements/{p['id']}/assignments/{assignment['id']}/accept",
        headers=mentor["headers"],
        json=terms_request(plan_v2),
    )
    assert m_acc.status_code == 200, m_acc.text
    h_act = client.post(
        f"/api/v1/placements/{p['id']}/host-decisions",
        headers=host["headers"],
        json={**terms_request(plan_v2), "action": "ACTIVATE"},
    )
    assert h_act.status_code == 200, h_act.text

    after_host = client.get(f"/api/v1/placements/{p['id']}/plan", headers=candidate["headers"])
    assert after_host.status_code == 200, after_host.text
    assert after_host.json()["host_accepted_at"] is not None


def test_mentor_and_teacher_assignments_track_consented_current_terms_across_versions(client, identities, organization):
    from test_academic_admission import nominate, pending_http
    from test_admission_lifecycle import publish, terms_request

    f = pending_http(client, identities, organization)
    plc = f["placement"]
    teacher_asg = nominate(client, f)

    mentor_user = identities("MENTOR", organization)
    mentor_asg = client.post(
        f"/api/v1/placements/{plc['id']}/mentor-assignments",
        headers=f["owner"]["headers"],
        json={"mentor_id": mentor_user["user_id"], "idempotency_key": str(uuid4())},
    )
    assert mentor_asg.status_code == 201, mentor_asg.text
    mentor_asg_id = mentor_asg.json()["id"]

    plan_v2 = client.get(f"/api/v1/placements/{plc['id']}/plan", headers=mentor_user["headers"]).json()
    assert plan_v2["version"] == 2

    assert client.post(
        f"/api/v1/placements/{plc['id']}/assignments/{mentor_asg_id}/accept",
        headers=mentor_user["headers"],
        json=terms_request(plan_v2),
    ).status_code == 200
    assert client.post(
        f"/api/v1/placements/{plc['id']}/assignments/{teacher_asg['id']}/accept",
        headers=f["teacher"]["headers"],
        json={**terms_request(plan_v2), "assignment_kind": "TEACHER"},
    ).status_code == 200

    m_list_v2 = client.get("/api/v1/me/mentor-assignments", headers=mentor_user["headers"]).json()["items"]
    t_list_v2 = client.get("/api/v1/me/academic-assignments", headers=f["teacher"]["headers"]).json()["items"]
    assert next(x for x in m_list_v2 if x["id"] == mentor_asg_id)["consented_current_terms"] is True
    assert next(x for x in t_list_v2 if x["id"] == teacher_asg["id"])["consented_current_terms"] is True

    # Publishing a revised learning plan bumps terms to v3 and requires re-consent from both sides
    plan_v3 = publish(
        client,
        f["owner"],
        {"id": plc["id"], "current_terms_id": plan_v2["terms_id"], "version": plan_v2["version"]},
    )
    assert plan_v3["version"] == 3

    m_list_v3 = client.get("/api/v1/me/mentor-assignments", headers=mentor_user["headers"]).json()["items"]
    t_list_v3 = client.get("/api/v1/me/academic-assignments", headers=f["teacher"]["headers"]).json()["items"]
    m_item_v3 = next(x for x in m_list_v3 if x["id"] == mentor_asg_id)
    t_item_v3 = next(x for x in t_list_v3 if x["id"] == teacher_asg["id"])
    assert m_item_v3["consented_current_terms"] is False
    assert m_item_v3["current_terms_version"] == 3
    assert t_item_v3["consented_current_terms"] is False
    assert t_item_v3["current_terms_version"] == 3

    # Re-accepting v3 flips consented_current_terms back to True
    assert client.post(
        f"/api/v1/placements/{plc['id']}/assignments/{mentor_asg_id}/accept",
        headers=mentor_user["headers"],
        json=terms_request(plan_v3),
    ).status_code == 200
    assert client.post(
        f"/api/v1/placements/{plc['id']}/assignments/{teacher_asg['id']}/accept",
        headers=f["teacher"]["headers"],
        json={**terms_request(plan_v3), "assignment_kind": "TEACHER"},
    ).status_code == 200

    m_list_ok = client.get("/api/v1/me/mentor-assignments", headers=mentor_user["headers"]).json()["items"]
    t_list_ok = client.get("/api/v1/me/academic-assignments", headers=f["teacher"]["headers"]).json()["items"]
    assert next(x for x in m_list_ok if x["id"] == mentor_asg_id)["consented_current_terms"] is True
    assert next(x for x in t_list_ok if x["id"] == teacher_asg["id"])["consented_current_terms"] is True


def test_own_and_host_placements_expose_academic_track_and_display_metadata(client, identities, organization):
    from test_academic_admission import nominate, pending_http
    from test_admission_lifecycle import planned

    # 1. Non-academic placement (academic_track=False)
    cand1, host1, _, p_non_acad, _ = planned(client, identities, organization)
    own1_res = client.get("/api/v1/me/placements", headers=cand1["headers"])
    assert own1_res.status_code == 200, own1_res.text
    own1 = next(row for row in own1_res.json()["items"] if row["id"] == p_non_acad["id"])
    assert own1["academic_track"] is False
    assert own1["organization_id"] == p_non_acad["organization_id"]
    assert isinstance(own1["organization_name"], str) and own1["organization_name"].strip()
    assert own1["opportunity_id"]
    assert isinstance(own1["opportunity_title"], str) and own1["opportunity_title"].strip()
    assert own1["created_at"]

    host1_res = client.get(
        f"/api/v1/organizations/{p_non_acad['organization_id']}/placements",
        headers=host1["headers"],
    )
    assert host1_res.status_code == 200, host1_res.text
    h1 = next(row for row in host1_res.json()["items"] if row["id"] == p_non_acad["id"])
    assert h1["academic_track"] is False
    assert h1["application_id"] == p_non_acad["application_id"]
    assert h1["offer_id"] == p_non_acad["offer_id"]
    assert h1["organization_id"] == p_non_acad["organization_id"]
    assert h1["enrollment_id"] is None
    assert isinstance(h1["opportunity_title"], str) and h1["opportunity_title"].strip()
    assert h1["created_at"]

    # 2. Academic-bound placement (academic_track=True after nominate binds supervision)
    acad = pending_http(client, identities, organization)
    nominate(client, acad)
    p_acad = acad["placement"]
    own2_res = client.get("/api/v1/me/placements", headers=acad["candidate"]["headers"])
    assert own2_res.status_code == 200, own2_res.text
    own2 = next(row for row in own2_res.json()["items"] if row["id"] == p_acad["id"])
    assert own2["academic_track"] is True
    assert own2["organization_name"]
    assert own2["opportunity_id"]
    assert own2["opportunity_title"]
    assert own2["created_at"]

    host2_res = client.get(
        f"/api/v1/organizations/{p_acad['organization_id']}/placements",
        headers=acad["owner"]["headers"],
    )
    assert host2_res.status_code == 200, host2_res.text
    h2 = next(row for row in host2_res.json()["items"] if row["id"] == p_acad["id"])
    assert h2["academic_track"] is True
    assert h2["application_id"] == p_acad["application_id"]
    assert h2["offer_id"] == p_acad["offer_id"]
    assert h2["organization_id"] == p_acad["organization_id"]
    assert h2["enrollment_id"] is not None
    assert h2["opportunity_title"]
    assert h2["created_at"]


def test_academic_review_queue_excludes_already_reviewed_revisions(client, identities, organization):
    from test_academic_admission import pending_http, post
    from test_academic_views import active_revision

    f = pending_http(client, identities, organization)
    assignment, draft = active_revision(client, f)
    post(client, f"/api/v1/logs/{draft['id']}/submit", f["candidate"], {}, 200)
    rev_id = draft["current_revision_id"]

    # Before academic review: revision is visible in both canonical & alias queues
    for actor_key in ("teacher", "coord"):
        q1 = client.get("/api/v1/me/academic-review-queue", headers=f[actor_key]["headers"])
        q2 = client.get("/api/v1/me/teacher-review-queue", headers=f[actor_key]["headers"])
        assert q1.status_code == 200 and q2.status_code == 200
        assert any(item["id"] == rev_id for item in q1.json()["items"])
        assert any(item["id"] == rev_id for item in q2.json()["items"])

    rev_res = client.post(
        f"/api/v1/log-revisions/{rev_id}/academic-reviews",
        headers=f["teacher"]["headers"],
        json={
            "academic_assignment_id": assignment["id"],
            "decision": "REVIEWED",
            "comment": "Akademik talablarga muvofiq tekshirildi.",
            "idempotency_key": str(uuid4()),
        },
    )
    assert rev_res.status_code == 201, rev_res.text

    # After academic review: revision is removed from both queues for teacher and coordinator
    for actor_key in ("teacher", "coord"):
        q1_after = client.get("/api/v1/me/academic-review-queue", headers=f[actor_key]["headers"])
        q2_after = client.get("/api/v1/me/teacher-review-queue", headers=f[actor_key]["headers"])
        assert q1_after.status_code == 200 and q2_after.status_code == 200
        assert all(item["id"] != rev_id for item in q1_after.json()["items"])
        assert all(item["id"] != rev_id for item in q2_after.json()["items"])



