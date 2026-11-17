"""Contract tests for Mutual Double-Blind Engagement Ratings (API-047 / CAP-027 / AC-024 / DB-064..066)
and Academic Placement Acceptance (API-048 / CAP-018 / DB-049..052).

Verifies:
1. Canonical contract API-047 (`POST /api/v1/engagements/{id}/ratings`): initial submission enters PENDING_BLIND (AC-024).
2. Bilateral mutual submission triggers instant publication (status: PUBLISHED, double_blind_active: False).
3. Idempotent replay: identical resubmission returns 200/201 with idempotent_replay=True.
4. Conflicting resubmission rejected with 409 RATING_ALREADY_SUBMITTED.
5. Incomplete engagement rejection: engagements not in COMPLETED status rejected with 409 ENGAGEMENT_NOT_COMPLETED.
6. Rubric validation: missing required criteria or score out of bounds rejected with 422.
7. Surfacing in API-057 (`GET /api/v1/me/ratings`): submissions_given and submissions_received updated cleanly.
8. Canonical contract API-048 (`POST /api/v1/placements/{id}/accept`): returns contract_id: "API-048".
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_candidate import published_fixture
from test_academic_admission import pending_http, plan, terms_request, post


def _create_test_rubric(status: str = "ACTIVE") -> tuple[str, list[dict]]:
    """Create a test rubric version with criteria summing to 100%."""
    rubric_id = str(uuid4())
    crit_punct_id = str(uuid4())
    crit_tech_id = str(uuid4())
    now_ts = now()
    with transaction() as conn:
        insert_row(
            conn,
            "rubric_versions",
            id=rubric_id,
            family="WORKPLACE_JOB",
            version=1,
            status=status,
            scale_min=1,
            scale_max=5,
            published_at=now_ts,
        )
        insert_row(
            conn,
            "rubric_criteria",
            id=crit_punct_id,
            rubric_id=rubric_id,
            code="PUNCTUALITY",
            title="Punctuality & Reliability",
            weight=40,
            required=True,
        )
        insert_row(
            conn,
            "rubric_criteria",
            id=crit_tech_id,
            rubric_id=rubric_id,
            code="TECHNICAL_EXECUTION",
            title="Technical Skills & Execution",
            weight=60,
            required=True,
        )

        crits = conn.execute(
            select(table("rubric_criteria")).where(table("rubric_criteria").c.rubric_id == rubric_id)
        ).mappings().all()

    return rubric_id, [dict(c) for c in crits]


def _setup_completed_job_engagement(client, owner, candidate, org_id):
    """Publish opportunity, apply, offer, accept, start-confirm, and end-confirm to reach COMPLETED status."""
    rev = published_fixture(owner, org_id)
    opp_id = rev["opportunity_id"]

    # Ensure PART_TIME kind
    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(kind="PART_TIME", capacity=5, occupied_count=0)
        )

    # 1. Candidate applies
    res_app = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Part-time job application"},
    )
    assert res_app.status_code == 201, res_app.text
    app_id = res_app.json()["id"]

    # 2. Host issues offer
    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Backend Developer", "salary_hourly": 60000}},
    )
    assert res_off.status_code in (200, 201), res_off.text
    offer_id = res_off.json()["id"]

    # 3. Candidate accepts offer
    res_acc = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_acc.status_code == 200, res_acc.text

    # 4. Fetch created engagement
    with transaction() as conn:
        t_je = table("job_engagements")
        row = conn.execute(select(t_je).where(t_je.c.offer_id == offer_id)).mappings().one()
        eng_id = str(row["id"])

    # 5. Dual CONFIRM_START
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START", "party": "CANDIDATE"},
    )
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_START", "party": "EMPLOYER"},
    )

    # 6. Dual CONFIRM_END -> reaches COMPLETED
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_END", "party": "CANDIDATE"},
    )
    res_end2 = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_END", "party": "EMPLOYER"},
    )
    assert res_end2.status_code == 200, res_end2.text
    assert res_end2.json()["status"] == "COMPLETED"

    return opp_id, app_id, offer_id, eng_id


def test_api047_candidate_rating_initial_submission_held_in_double_blind(client, identities, organization):
    """AC-024: Candidate rates employer on COMPLETED engagement -> held in PENDING_BLIND with 14-day window."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores_payload = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    payload = {
        "rubric_id": rubric_id,
        "scores": scores_payload,
        "comment": "Tashkilotda ajoyib muhit va sharoitlar yaratilgan.",
        "idempotency_key": f"key-{uuid4()}",
    }

    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json=payload,
    )
    assert res.status_code in (200, 201), res.text
    data = res.json()

    assert data["contract_id"] == "API-047"
    assert data["engagement_id"] == eng_id
    assert data["rater_role"] == "CANDIDATE"
    assert data["target_org_id"] == organization
    assert data["target_user_id"] is None
    assert data["status"] == "PENDING_BLIND"
    assert data["double_blind_active"] is True
    assert data["idempotent_replay"] is False
    assert "publish_after" in data and data["publish_after"] is not None


def test_api047_mutual_rating_triggers_immediate_unblinding(client, identities, organization):
    """AC-024: When both candidate and employer submit ratings, both transition to PUBLISHED immediately."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    # 1. Candidate rates employer -> PENDING_BLIND
    cand_scores = [{"criterion_id": str(c["id"]), "score": 4} for c in crits]
    res1 = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": cand_scores, "comment": "Yaxshi jamoa"},
    )
    assert res1.status_code in (200, 201), res1.text
    assert res1.json()["status"] == "PENDING_BLIND"
    cand_sub_id = res1.json()["submission_id"]

    # 2. Employer rates candidate -> triggers mutual unblinding!
    emp_scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    res2 = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=owner["headers"],
        json={"rubric_id": rubric_id, "scores": emp_scores, "comment": "Ajoyib mutaxassis"},
    )
    assert res2.status_code in (200, 201), res2.text
    emp_data = res2.json()

    assert emp_data["contract_id"] == "API-047"
    assert emp_data["rater_role"] == "EMPLOYER"
    assert emp_data["target_user_id"] == cand_user["user_id"]
    assert emp_data["status"] == "PUBLISHED"
    assert emp_data["double_blind_active"] is False

    # 3. Verify candidate's submission in DB is now also PUBLISHED
    with transaction() as conn:
        t_sub = table("rating_submissions")
        sub_row = conn.execute(select(t_sub).where(t_sub.c.id == cand_sub_id)).mappings().one()
        assert sub_row["status"] == "PUBLISHED"


def test_api047_idempotent_replay(client, identities, organization):
    """Submitting the exact same rating returns 200/201 with idempotent_replay=True."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    payload = {"rubric_id": rubric_id, "scores": scores, "comment": "A'lo darajada"}

    res1 = client.post(f"/api/v1/engagements/{eng_id}/ratings", headers=cand_user["headers"], json=payload)
    assert res1.status_code in (200, 201)
    assert res1.json()["idempotent_replay"] is False

    # Exact replay
    res2 = client.post(f"/api/v1/engagements/{eng_id}/ratings", headers=cand_user["headers"], json=payload)
    assert res2.status_code in (200, 201)
    assert res2.json()["idempotent_replay"] is True
    assert res2.json()["submission_id"] == res1.json()["submission_id"]


def test_api047_conflicting_resubmission_rejected(client, identities, organization):
    """AC-022: Candidate cannot submit a second conflicting rating for the same engagement (409 RATING_ALREADY_SUBMITTED)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores1 = [{"criterion_id": str(c["id"]), "score": 4} for c in crits]
    res1 = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores1, "comment": "Birinchi fikr"},
    )
    assert res1.status_code in (200, 201)

    # Conflicting scores
    scores2 = [{"criterion_id": str(c["id"]), "score": 1} for c in crits]
    res2 = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores2, "comment": "O'zgartirilgan fikr"},
    )
    assert res2.status_code == 409, res2.text
    assert res2.json()["detail"]["code"] == "RATING_ALREADY_SUBMITTED"


def test_api047_cannot_rate_uncompleted_engagement(client, identities, organization):
    """AC-022: Rating is strictly forbidden on non-completed engagements (409 ENGAGEMENT_NOT_COMPLETED)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()

    # Create engagement only up to start confirmation (ACTIVE, not COMPLETED)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]
    with transaction() as conn:
        conn.execute(table("opportunities").update().where(table("opportunities").c.id == opp_id).values(kind="PART_TIME"))

    res_app = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand_user["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Application"},
    )
    app_id = res_app.json()["id"]

    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Tester"}},
    )
    offer_id = res_off.json()["id"]

    client.post(f"/api/v1/offers/{offer_id}/respond", headers=cand_user["headers"], json={"decision": "ACCEPT"})

    with transaction() as conn:
        eng_id = str(conn.execute(select(table("job_engagements").c.id).where(table("job_engagements").c.offer_id == offer_id)).scalar_one())

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]

    # Attempt rating on PENDING_START_CONFIRMATION
    res_unstarted = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores},
    )
    assert res_unstarted.status_code == 409, res_unstarted.text
    assert res_unstarted.json()["detail"]["code"] == "ENGAGEMENT_NOT_COMPLETED"


def test_api047_rubric_validation_missing_criteria_and_bounds(client, identities, organization):
    """AC-021: Scores must cover all required criteria and respect scale bounds (1..5)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    # 1. Missing required criterion
    partial_scores = [{"criterion_id": str(crits[0]["id"]), "score": 5}]
    res_missing = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": partial_scores},
    )
    assert res_missing.status_code == 422, res_missing.text
    assert res_missing.json()["detail"]["code"] == "MISSING_REQUIRED_CRITERIA"

    # 2. Score out of bounds (> 5)
    bad_score = [{"criterion_id": str(crits[0]["id"]), "score": 9}, {"criterion_id": str(crits[1]["id"]), "score": 5}]
    res_bound = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": bad_score},
    )
    assert res_bound.status_code == 422, res_bound.text


def test_api047_ratings_reflected_in_me_ratings_api057(client, identities, organization):
    """Submissions surface correctly in API-057 (GET /api/v1/me/ratings)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": "Ajoyib kompaniya"},
    )

    # Check candidate me/ratings
    res_me = client.get("/api/v1/me/ratings", headers=cand_user["headers"])
    assert res_me.status_code == 200
    data_me = res_me.json()
    assert any(g["engagement_id"] == eng_id for g in data_me["submissions_given"])


def test_api048_placement_acceptance_contract_id(client, identities, organization):
    """Canonical API-048 (POST /api/v1/placements/{id}/accept): receipt contains contract_id: 'API-048'."""
    f = pending_http(client, identities, organization)
    p = plan(client, f)
    res = client.post(
        f"/api/v1/placements/{f['placement']['id']}/accept",
        headers=f["candidate"]["headers"],
        json=terms_request(p),
    )
    assert res.status_code in (200, 201), res.text
    data = res.json()
    assert data.get("contract_id") == "API-048"
    assert data["side"] == "CANDIDATE"
    assert data["placement_id"] == f["placement"]["id"]
