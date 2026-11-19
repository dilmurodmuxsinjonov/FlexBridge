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
