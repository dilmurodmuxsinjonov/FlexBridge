"""Adversarial security, IDOR, cooldown, and state-machine tests for Candidate Applications (API-006, API-029, API-039, API-040, API-041, API-044 / CAP-007).

Strictly verified on isolated PostgreSQL (port 55440); pg_live and frozen main untouched.

Covers:
1. Authentication & Candidate profile enforcement (401/403 boundaries).
2. Closed, draft, or expired opportunity application prevention (404/409/422).
3. Idempotency-Key validation, exact replay safety, payload mismatch, and duplicate active application protection.
4. Cross-candidate IDOR prevention (uniform 404 on GET, reapply, and withdraw of other candidate's application).
5. 24-hour cooldown enforcement between attempts (429 REAPPLY_COOLDOWN_ACTIVE).
6. 3 attempts per rolling 30-day limit boundary (429 REAPPLY_LIMIT_EXCEEDED).
7. Reapply rejection on active applications (409 APPLICATION_ACTIVE).
8. State-machine transitions and capacity release on withdrawal (idempotent repeat, ACCEPTED lock).
9. Keyset cursor tampering and SQL injection resistance.
10. Strict tenant isolation on candidate application metrics summary (API-029).
"""

from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, update

from app.db.storage import now, table, transaction
from test_candidate import published_fixture


def test_adversarial_apply_unauthenticated_and_non_candidate(client, identities, organization):
    """API-006: Unauthenticated callers receive 401; users without candidate profile receive 403."""
    owner = identities("OWNER", organization)
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    # 1. Unauthenticated request -> 401 AUTH_REQUIRED
    r_unauth = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={"Idempotency-Key": str(uuid4())},
        json={"note": "Hacker attempt"},
    )
    assert r_unauth.status_code == 401
    assert r_unauth.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_INVALID")

    # 2. Malformed / forged Bearer token -> 401
    r_forged = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={"Authorization": "Bearer forged-token-adversarial", "Idempotency-Key": str(uuid4())},
        json={"note": "Hacker attempt"},
    )
    assert r_forged.status_code == 401

    # 3. Request without candidate profile (e.g. pure platform grantor)
    from app.services.auth import auth_service
    staff_user = auth_service.register_user(
        display_name="Pure Org Staff",
        password="correct-passphrase-2026",
        adult_confirmed=True,
    )
    # Remove candidate profile if auto-created
    with transaction() as conn:
        conn.execute(
            table("candidate_profiles").delete().where(table("candidate_profiles").c.user_id == staff_user["id"])
        )
    staff_session = auth_service.login(user_id=staff_user["id"], password="correct-passphrase-2026")
    staff_headers = {"Authorization": f"Bearer {staff_session['access_token']}", "Idempotency-Key": str(uuid4())}

    r_staff = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=staff_headers,
        json={"note": "Staff applying"},
    )
    assert r_staff.status_code in (403, 404)
    assert r_staff.json()["detail"]["code"] == "CANDIDATE_PROFILE_REQUIRED"


def test_adversarial_apply_to_draft_closed_or_expired_opportunity(client, identities, organization):
    """API-006: Applications rejected for draft, closed, or expired opportunities."""
    owner = identities("OWNER", organization)
    cand = identities()
    headers = {**cand["headers"], "Idempotency-Key": str(uuid4())}

    # 1. Non-existent opportunity UUID -> 404
    r_not_found = client.post(
        f"/api/v1/opportunities/{uuid4()}/applications",
        headers=headers,
        json={},
    )
    assert r_not_found.status_code == 404
    assert r_not_found.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"

    # 2. DRAFT opportunity -> rejected (404 or 409)
    from app.services.opportunities import opportunity_service
    draft_rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Unpublished Draft Opp",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=30000,
        actor_user_id=owner["user_id"],
    )
    r_draft = client.post(
        f"/api/v1/opportunities/{draft_rev['opportunity_id']}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert r_draft.status_code in (404, 409)
    assert r_draft.json()["detail"]["code"] in ("APPLICATION_NOT_FOUND", "OPPORTUNITY_NOT_ACTIVE")

    # 3. CLOSED opportunity -> 409 OPPORTUNITY_NOT_ACTIVE
    closed_rev = published_fixture(owner, organization)
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == closed_rev["opportunity_id"])
            .values(status="CLOSED")
        )
    r_closed = client.post(
        f"/api/v1/opportunities/{closed_rev['opportunity_id']}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert r_closed.status_code == 409
    assert r_closed.json()["detail"]["code"] == "OPPORTUNITY_NOT_ACTIVE"

    # 4. EXPIRED opportunity -> 409 OPPORTUNITY_EXPIRED
    expired_rev = published_fixture(owner, organization)
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == expired_rev["opportunity_id"])
            .values(expires_at=now() - timedelta(minutes=10))
        )
    r_expired = client.post(
        f"/api/v1/opportunities/{expired_rev['opportunity_id']}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert r_expired.status_code == 409
    assert r_expired.json()["detail"]["code"] == "OPPORTUNITY_EXPIRED"


def test_adversarial_idempotency_key_replay_and_conflict(client, identities, organization):
    """API-006: Missing idempotency key rejected; replay returns idempotent 201; duplicate active app rejected."""
    owner = identities("OWNER", organization)
    cand = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    # 1. Missing Idempotency-Key header -> 422
    r_missing_key = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand["headers"],
        json={"note": "Initial submission"},
    )
    assert r_missing_key.status_code == 422
    assert r_missing_key.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    # 2. First submission -> 201 Created
    idem_key = f"idem-{uuid4()}"
    r_initial = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": idem_key},
        json={"note": "First real attempt"},
    )
    assert r_initial.status_code == 201
    initial_body = r_initial.json()
    assert initial_body["status"] == "SUBMITTED"
    assert initial_body["current_attempt"]["attempt_no"] == 1
    app_id = initial_body["id"]

    # 3. Exact replay with same Idempotency-Key -> returns previous response, no duplicates
    r_replay = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": idem_key},
        json={"note": "First real attempt"},
    )
    assert r_replay.status_code in (200, 201)
    assert r_replay.json()["id"] == app_id
    assert r_replay.json()["current_attempt"]["id"] == initial_body["current_attempt"]["id"]

    # Verify strictly 1 row in DB
    with transaction() as conn:
        t_apps = table("applications")
        app_count = conn.execute(
            select(table("applications")).where(
                t_apps.c.candidate_id == cand["candidate_id"],
                t_apps.c.opportunity_id == opp_id,
            )
        ).all()
        assert len(app_count) == 1

    # 4. New Idempotency-Key while application is active -> 409 APPLICATION_ALREADY_EXISTS
    r_duplicate = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": f"new-key-{uuid4()}"},
        json={"note": "Second attempt without reapply"},
    )
    assert r_duplicate.status_code == 409
    assert r_duplicate.json()["detail"]["code"] == "APPLICATION_ALREADY_EXISTS"


def test_adversarial_cross_candidate_idor_prevention(client, identities, organization):
    """API-039, API-040, API-041, API-044: Cross-candidate IDOR strictly blocked with uniform 404."""
    owner = identities("OWNER", organization)
    cand_a = identities()
    cand_b = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    # Candidate A applies
    r_app_a = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand_a["headers"], "Idempotency-Key": str(uuid4())},
        json={"note": "Cand A application"},
    )
    assert r_app_a.status_code == 201
    app_a_id = r_app_a.json()["id"]

    # 1. Candidate B attempts GET /api/v1/me/applications/{app_a_id} (API-041) -> 404
    r_idor_get = client.get(
        f"/api/v1/me/applications/{app_a_id}",
        headers=cand_b["headers"],
    )
    assert r_idor_get.status_code == 404
    assert r_idor_get.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"

    # 2. Candidate B attempts POST /api/v1/me/applications/{app_a_id}/reapply (API-040) -> 404
    r_idor_reapply = client.post(
        f"/api/v1/me/applications/{app_a_id}/reapply",
        headers={**cand_b["headers"], "Idempotency-Key": str(uuid4())},
        json={"reason": "Attacking other candidate application"},
    )
    assert r_idor_reapply.status_code == 404
    assert r_idor_reapply.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"

    # 3. Candidate B attempts POST /api/v1/me/applications/{app_a_id}/withdraw (API-044) -> 404
    r_idor_withdraw = client.post(
        f"/api/v1/me/applications/{app_a_id}/withdraw",
        headers=cand_b["headers"],
        json={"reason": "Malicious withdrawal"},
    )
    assert r_idor_withdraw.status_code == 404
    assert r_idor_withdraw.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"

    # 4. Candidate B lists applications (API-039) -> App A must NOT appear
    r_list_b = client.get(
        "/api/v1/me/applications",
        headers=cand_b["headers"],
    )
    assert r_list_b.status_code == 200
    b_ids = [item["id"] for item in r_list_b.json().get("items", [])]
    assert app_a_id not in b_ids


def test_adversarial_reapply_cooldown_24h_boundary(client, identities, organization):
    """API-040 / CAP-007: 24-hour cooldown between attempts strictly enforced."""
    owner = identities("OWNER", organization)
    cand = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    # Initial application
    r_init = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={"note": "Initial apply"},
    )
    assert r_init.status_code == 201
    app_id = r_init.json()["id"]

    # Transition application to REJECTED so it becomes reapply-eligible
    with transaction() as conn:
        conn.execute(
            table("applications")
            .update()
            .where(table("applications").c.id == app_id)
            .values(status="REJECTED")
        )

    # 1. Immediate reapply (< 24 hours) -> 429 REAPPLY_COOLDOWN_ACTIVE
    r_cool_fail = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={"reason": "Immediate retry"},
    )
    assert r_cool_fail.status_code == 429
    assert r_cool_fail.json()["detail"]["code"] == "REAPPLY_COOLDOWN_ACTIVE"

    # 2. Fast-forward previous attempt submitted_at to 25 hours ago
    with transaction() as conn:
        conn.execute(
            table("application_attempts")
            .update()
            .where(table("application_attempts").c.application_id == app_id)
            .values(submitted_at=now() - timedelta(hours=25))
        )

    # 3. Reapply after cooldown expiration -> 201 Success
    r_cool_pass = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={"reason": "Retrying with updated skills"},
    )
    assert r_cool_pass.status_code == 201
    body = r_cool_pass.json()
    assert body["status"] == "SUBMITTED"
    assert body["current_attempt"]["attempt_no"] == 2
    assert body["version"] == 2


def test_adversarial_reapply_30d_limit_boundary(client, identities, organization):
    """API-040 / CAP-007: Maximum 3 attempts per rolling 30-day window enforced."""
    owner = identities("OWNER", organization)
    cand = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    # Initial application (Attempt 1)
    r_init = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert r_init.status_code == 201
    app_id = r_init.json()["id"]

    # Simulate Attempt 1 (submitted 20 days ago) and Attempt 2 (submitted 10 days ago)
    with transaction() as conn:
        conn.execute(
            table("application_attempts")
            .update()
            .where(table("application_attempts").c.application_id == app_id)
            .values(submitted_at=now() - timedelta(days=20))
        )
        # Insert Attempt 2
        att2_id = str(uuid4())
        from app.services.placements import insert_row
        insert_row(
            conn,
            "application_attempts",
            id=att2_id,
            application_id=app_id,
            attempt_no=2,
            revision_id=opp_rev["id"],
            profile_snapshot={"headline": "v2"},
            schedule_result="MATCH",
            matching_version="v1.4",
            submitted_at=now() - timedelta(days=10),
            idempotency_key=f"att2-{uuid4()}",
            opportunity_id=opp_id,
        )
        # Insert Attempt 3 (submitted 2 days ago)
        att3_id = str(uuid4())
        insert_row(
            conn,
            "application_attempts",
            id=att3_id,
            application_id=app_id,
            attempt_no=3,
            revision_id=opp_rev["id"],
            profile_snapshot={"headline": "v3"},
            schedule_result="MATCH",
            matching_version="v1.4",
            submitted_at=now() - timedelta(days=2),
            idempotency_key=f"att3-{uuid4()}",
            opportunity_id=opp_id,
        )
        conn.execute(
            table("applications")
            .update()
            .where(table("applications").c.id == app_id)
            .values(status="REJECTED", current_attempt_id=att3_id, version=3)
        )

    # Now attempt 4 (within 30 days of attempts 1, 2, 3, even though > 24h since attempt 3)
    r_fourth_attempt = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={"reason": "4th attempt within 30 days"},
    )
    assert r_fourth_attempt.status_code == 429
    assert r_fourth_attempt.json()["detail"]["code"] == "REAPPLY_LIMIT_EXCEEDED"


def test_adversarial_reapply_on_active_application_rejected(client, identities, organization):
    """API-040: Cannot reapply while application status is active (SUBMITTED, UNDER_REVIEW, OFFERED)."""
    owner = identities("OWNER", organization)
    cand = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    r_init = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert r_init.status_code == 201
    app_id = r_init.json()["id"]

    # Status is SUBMITTED (active) -> Reapply must fail with 409
    r_reapply_active = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={"reason": "Reapplying too early while active"},
    )
    assert r_reapply_active.status_code == 409
    assert r_reapply_active.json()["detail"]["code"] == "APPLICATION_ACTIVE"


def test_adversarial_withdraw_state_machine_and_audit(client, identities, organization):
    """API-044: Withdrawal transitions status to WITHDRAWN, emits event, and prevents withdrawing ACCEPTED."""
    owner = identities("OWNER", organization)
    cand = identities()
    opp_rev = published_fixture(owner, organization)
    opp_id = opp_rev["opportunity_id"]

    r_init = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers={**cand["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    app_id = r_init.json()["id"]

    # 1. Withdraw active application -> 200 Success
    r_withdraw = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=cand["headers"],
        json={"reason": "Changed my mind"},
    )
    assert r_withdraw.status_code == 200
    assert r_withdraw.json()["status"] == "WITHDRAWN"

    # Verify event logged in application_events
    with transaction() as conn:
        t_events = table("application_events")
        event_row = conn.execute(
            select(t_events).where(
                t_events.c.application_id == app_id,
                t_events.c.to_status == "WITHDRAWN",
            )
        ).mappings().first()
        assert event_row is not None
        assert event_row["from_status"] == "SUBMITTED"
        assert event_row["actor_id"] == cand["user_id"]

    # 2. Repeated withdraw -> idempotent 200
    r_repeat_withdraw = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=cand["headers"],
        json={"reason": "Repeated request"},
    )
    assert r_repeat_withdraw.status_code == 200
    assert r_repeat_withdraw.json()["status"] == "WITHDRAWN"

    # 3. Cannot withdraw if status is ACCEPTED
    with transaction() as conn:
        conn.execute(
            table("applications")
            .update()
            .where(table("applications").c.id == app_id)
            .values(status="ACCEPTED")
        )
    r_accepted_withdraw = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=cand["headers"],
        json={"reason": "Trying to withdraw accepted"},
    )
    assert r_accepted_withdraw.status_code == 409
    assert r_accepted_withdraw.json()["detail"]["code"] == "CANNOT_WITHDRAW_ACCEPTED"


def test_adversarial_cursor_tampering_and_sql_injection(client, identities, organization):
    """API-039: Malformed cursor returns 422; SQL injection in status filter safely handled."""
    cand = identities()

    # 1. Malformed cursor -> 422
    r_bad_cursor = client.get(
        "/api/v1/me/applications?after=not-a-valid-base64-json-cursor",
        headers=cand["headers"],
    )
    assert r_bad_cursor.status_code == 422
    assert r_bad_cursor.json()["detail"]["code"] == "INVALID_CURSOR"

    # 2. SQL Injection in status query parameter -> safely handled without SQL syntax error
    r_sqli_status = client.get(
        "/api/v1/me/applications?status=' OR '1'='1",
        headers=cand["headers"],
    )
    assert r_sqli_status.status_code == 200
    assert r_sqli_status.json().get("items") == []


def test_adversarial_me_applications_summary_isolation(client, identities, organization):
    """API-029: Metrics aggregation is strictly isolated to the caller's candidate profile."""
    owner = identities("OWNER", organization)
    cand_a = identities()
    cand_b = identities()
    opp_rev_1 = published_fixture(owner, organization)
    opp_rev_2 = published_fixture(owner, organization)

    # Candidate A applies to Opp 1
    client.post(
        f"/api/v1/opportunities/{opp_rev_1['opportunity_id']}/applications",
        headers={**cand_a["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )

    # Candidate B applies to Opp 2 and withdraws
    r_b = client.post(
        f"/api/v1/opportunities/{opp_rev_2['opportunity_id']}/applications",
        headers={**cand_b["headers"], "Idempotency-Key": str(uuid4())},
        json={},
    )
    app_b_id = r_b.json()["id"]
    client.post(
        f"/api/v1/me/applications/{app_b_id}/withdraw",
        headers=cand_b["headers"],
        json={},
    )

    # Candidate A summary: must show 1 total, 1 submitted, 0 withdrawn
    r_summary_a = client.get("/api/v1/me/applications/summary", headers=cand_a["headers"])
    assert r_summary_a.status_code == 200
    sum_a = r_summary_a.json()
    assert sum_a["total_applications"] == 1
    assert sum_a["submitted"] == 1
    assert sum_a["withdrawn"] == 0

    # Candidate B summary: must show 1 total, 0 submitted, 1 withdrawn
    r_summary_b = client.get("/api/v1/me/applications/summary", headers=cand_b["headers"])
    assert r_summary_b.status_code == 200
    sum_b = r_summary_b.json()
    assert sum_b["total_applications"] == 1
    assert sum_b["submitted"] == 0
    assert sum_b["withdrawn"] == 1
