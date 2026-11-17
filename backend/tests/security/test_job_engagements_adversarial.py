"""Adversarial security, concurrency race, anti-spoofing, and IDOR tests for
Dual-Confirmed Job Engagements System (API-045, API-046 / CAP-012 / AC-014, AC-016 / DB-047, DB-048).

Strictly tested on isolated PostgreSQL test cluster (port 55440); pg_live and frozen main untouched.

Covers:
1. Unauthenticated & forged Bearer token boundary (401 AUTH_REQUIRED).
2. Cross-candidate and foreign-employer IDOR protection (uniform 404 on both GET and POST).
3. Anti-spoofing defense: candidate claiming to be EMPLOYER or employer claiming CANDIDATE rejected with 403.
4. Invalid state transitions: ending unstarted engagements or starting completed ones (409).
5. Malformed action payload and SQL injection rejection (422).
6. AC-014 dispute precedence: dispute blocks transition to ACTIVE even if one side confirmed start.
7. Concurrency race: parallel start and dispute resolution under row-level locking.
8. AC-016 boundary: job engagements strictly decoupled from academic diary logs.
9. Append-only audit logging: all confirmation events securely recorded.
10. Parent opportunity status decoupling on completion of active engagement.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from test_candidate import published_fixture


def _setup_job_engagement(client, owner, candidate, org_id):
    """Helper to publish part-time opportunity, apply, issue offer, and accept to produce job_engagement."""
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
        json={"terms_snapshot": {"position": "Software Engineer", "salary_hourly": 50000}},
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
        row = conn.execute(
            select(t_je).where(t_je.c.offer_id == offer_id)
        ).mappings().one()
        eng_id = str(row["id"])

    return opp_id, app_id, offer_id, eng_id


# =============================================================================
# 1. Unauthenticated & Forged Token Boundary
# =============================================================================
def test_adversarial_unauthenticated_and_forged_tokens(client):
    """API-045 and API-046: Missing or forged tokens reject with 401 AUTH_REQUIRED."""
    random_uuid = str(uuid4())

    # 1. GET /me/engagements/{id} unauthenticated
    r1 = client.get(f"/api/v1/me/engagements/{random_uuid}")
    assert r1.status_code == 401
    assert r1.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_INVALID")

    # 2. GET /me/engagements/{id} forged token
    r2 = client.get(
        f"/api/v1/me/engagements/{random_uuid}",
        headers={"Authorization": "Bearer forged-token-attack"},
    )
    assert r2.status_code == 401

    # 3. POST /engagements/{id}/confirmations unauthenticated
    r3 = client.post(
        f"/api/v1/engagements/{random_uuid}/confirmations",
        json={"action": "CONFIRM_START"},
    )
    assert r3.status_code == 401
    assert r3.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_INVALID")

    # 4. POST /engagements/{id}/confirmations forged token
    r4 = client.post(
        f"/api/v1/engagements/{random_uuid}/confirmations",
        headers={"Authorization": "Bearer forged-token-attack"},
        json={"action": "CONFIRM_START"},
    )
    assert r4.status_code == 401


# =============================================================================
# 2. Cross-Candidate and Foreign-Employer IDOR Protection
# =============================================================================
def test_adversarial_cross_candidate_and_foreign_org_idor(client, identities, organization):
    """API-045 & API-046: Third-party candidates or foreign org staff probing engagements receive uniform 404."""
    owner_1 = identities("OWNER", organization)
    cand_a = identities()
    cand_b = identities()

    # Second organization and owner
    foreign_org_id = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table("organizations").insert().values(
                id=foreign_org_id,
                created_at=now(),
                updated_at=now(),
                tax_id=str(uuid4())[:12],
                legal_name="Foreign Corp",
                public_name="Foreign Corp",
                region="Bukhara",
                status="VERIFIED",
            )
        )
    owner_2 = identities("OWNER", foreign_org_id)

    _, _, _, eng_id = _setup_job_engagement(client, owner_1, cand_a, organization)

    # 1. Candidate B attempts GET -> 404
    r_cand_b_get = client.get(f"/api/v1/me/engagements/{eng_id}", headers=cand_b["headers"])
    assert r_cand_b_get.status_code == 404
    assert r_cand_b_get.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 2. Candidate B attempts POST confirmation -> 404
    r_cand_b_post = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=cand_b["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert r_cand_b_post.status_code == 404
    assert r_cand_b_post.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 3. Foreign org staff attempts GET -> 404
    r_foreign_get = client.get(f"/api/v1/me/engagements/{eng_id}", headers=owner_2["headers"])
    assert r_foreign_get.status_code == 404
    assert r_foreign_get.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 4. Foreign org staff attempts POST confirmation -> 404
    r_foreign_post = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner_2["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert r_foreign_post.status_code == 404
    assert r_foreign_post.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 5. Non-existent UUID returns identical 404
    r_not_found = client.get(f"/api/v1/me/engagements/{uuid4()}", headers=cand_b["headers"])
    assert r_not_found.status_code == 404
    assert r_not_found.json() == r_cand_b_get.json()


# =============================================================================
# 3. Anti-Spoofing Defense
# =============================================================================
def test_adversarial_party_spoofing_defense(client, identities, organization):
    """API-046: Candidate claiming to be EMPLOYER or employer claiming CANDIDATE rejected with 403."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # 1. Candidate explicitly claims party="EMPLOYER" -> 403
    r_spoof_cand = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START", "party": "EMPLOYER"},
    )
    assert r_spoof_cand.status_code == 403
    assert r_spoof_cand.json()["detail"]["code"] == "ENGAGEMENT_ACTOR_FORBIDDEN"

    # 2. Employer explicitly claims party="CANDIDATE" -> 403
    r_spoof_emp = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_START", "party": "CANDIDATE"},
    )
    assert r_spoof_emp.status_code == 403
    assert r_spoof_emp.json()["detail"]["code"] == "ENGAGEMENT_ACTOR_FORBIDDEN"


# =============================================================================
# 4. Invalid State Transitions
# =============================================================================
def test_adversarial_invalid_state_transitions(client, identities, organization):
    """API-046: Attempting CONFIRM_END while unstarted or CONFIRM_START after completion rejected with 409."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # 1. Attempt CONFIRM_END while PENDING_START_CONFIRMATION -> 409
    r_end_premature = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_END"},
    )
    assert r_end_premature.status_code == 409
    assert r_end_premature.json()["detail"]["code"] == "ENGAGEMENT_NOT_ACTIVE"

    # 2. Transition through start and completion
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=candidate["headers"], json={"action": "CONFIRM_START"})
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=owner["headers"], json={"action": "CONFIRM_START"})
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=candidate["headers"], json={"action": "CONFIRM_END"})
    r_completed = client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=owner["headers"], json={"action": "CONFIRM_END"})
    assert r_completed.status_code == 200
    assert r_completed.json()["status"] == "COMPLETED"

    # 3. Attempt CONFIRM_START on COMPLETED engagement -> 409
    r_restart = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert r_restart.status_code == 409
    assert r_restart.json()["detail"]["code"] == "ENGAGEMENT_NOT_CONFIRMABLE"


# =============================================================================
# 5. Malformed Action and Injection Rejection
# =============================================================================
def test_adversarial_malformed_and_sql_injection_payloads(client, identities, organization):
    """API-046: Invalid action patterns or injection payloads receive 422 validation error."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # 1. Invalid action string
    r_bad_action = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_ALL_RIGHTS"},
    )
    assert r_bad_action.status_code == 422

    # 2. SQL injection pattern in action
    r_sqli = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "' OR '1'='1' --"},
    )
    assert r_sqli.status_code == 422


# =============================================================================
# 6. AC-014 Dispute Precedence over Start
# =============================================================================
def test_adversarial_ac014_single_dispute_blocks_active_transition(client, identities, organization):
    """API-046 / AC-014: Dispute blocks transition to ACTIVE even if one side confirmed start."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Candidate confirms start
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START"},
    )

    # Employer files dispute
    r_dispute = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "DISPUTE_START", "note": "Nomzod ishga kelmadi"},
    )
    assert r_dispute.status_code == 200
    assert r_dispute.json()["status"] == "DISPUTED"

    # Status remains DISPUTED, never ACTIVE
    r_view = client.get(f"/api/v1/me/engagements/{eng_id}", headers=candidate["headers"])
    assert r_view.status_code == 200
    assert r_view.json()["status"] == "DISPUTED"
    assert r_view.json()["confirmed_started_at"] is None


# =============================================================================
# 7. Concurrency Race: Simultaneous Start and Dispute
# =============================================================================
def test_adversarial_concurrency_race_start_and_dispute(client, identities, organization):
    """API-046: Concurrent start confirmation and dispute resolution under row-level locking."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    def send_cand():
        return client.post(
            f"/api/v1/engagements/{eng_id}/confirmations",
            headers=candidate["headers"],
            json={"action": "CONFIRM_START"},
        )

    def send_emp():
        return client.post(
            f"/api/v1/engagements/{eng_id}/confirmations",
            headers=owner["headers"],
            json={"action": "DISPUTE_START", "note": "Simultaneous dispute"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_cand)
        f2 = executor.submit(send_emp)
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 200
    assert r2.status_code == 200

    # Dispute must prevail
    r_check = client.get(f"/api/v1/me/engagements/{eng_id}", headers=owner["headers"])
    assert r_check.status_code == 200
    assert r_check.json()["status"] == "DISPUTED"


# =============================================================================
# 8. AC-016 Non-Internship Job Engagements Have No Academic Diaries
# =============================================================================
def test_adversarial_ac016_job_engagements_no_academic_diaries(client, identities, organization):
    """AC-016: Non-internship job engagements do not require academic diaries; /logs route does not operate on them."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Attempting to fetch logs on a job engagement UUID fails as not a placement
    r_logs = client.get(f"/api/v1/placements/{eng_id}/logs", headers=candidate["headers"])
    assert r_logs.status_code in (404, 422)


# =============================================================================
# 9. Append-Only Audit Trail Recording
# =============================================================================
def test_adversarial_audit_trail_recording(client, identities, organization):
    """API-046: Engagement confirmations create audit trail entries with AppendOnlyAuditStore."""
    owner = identities("OWNER", organization)
    candidate = identities()

    _, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START", "note": "Audit verification note"},
    )

    with transaction() as conn:
        t_audit = table("audit_events")
        audit_row = conn.execute(
            select(t_audit).where(
                t_audit.c.object_type == "job_engagement",
                t_audit.c.object_key == eng_id,
                t_audit.c.action == "ENGAGEMENT_CONFIRM_START",
            )
        ).mappings().first()
        assert audit_row is not None
        assert audit_row["actor_id"] == candidate["user_id"]


# =============================================================================
# 10. Parent Opportunity Archival Decoupling
# =============================================================================
def test_adversarial_parent_opportunity_status_decoupling(client, identities, organization):
    """API-046: An active engagement can be confirmed COMPLETED even if host paused the opportunity."""
    owner = identities("OWNER", organization)
    candidate = identities()

    opp_id, _, _, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Activate engagement
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=candidate["headers"], json={"action": "CONFIRM_START"})
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=owner["headers"], json={"action": "CONFIRM_START"})

    # Host pauses or closes parent opportunity
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == opp_id)
            .values(status="CLOSED")
        )

    # Both parties should still be able to confirm END
    r_cand_end = client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=candidate["headers"], json={"action": "CONFIRM_END"})
    assert r_cand_end.status_code == 200

    r_emp_end = client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=owner["headers"], json={"action": "CONFIRM_END"})
    assert r_emp_end.status_code == 200
    assert r_emp_end.json()["status"] == "COMPLETED"
