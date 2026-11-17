"""Adversarial security, concurrency race, IDOR, and privilege escalation tests for
Interviews and Offers System (API-042, API-043 / CAP-009, CAP-011 / AC-012 / DB-044, DB-045, DB-046).

Strictly tested on isolated PostgreSQL test cluster (port 55440); pg_live and frozen main untouched.

Covers:
1. Unauthenticated & forged Bearer token boundary (401 AUTH_REQUIRED).
2. Cross-candidate interview IDOR protection (uniform 404).
3. Foreign organization privilege escalation on interview completion (403/404).
4. Terminal interview state lock: cannot respond to CANCELLED or COMPLETED interviews (409).
5. Malformed payload and SQL injection rejection on interview responses (422).
6. Cross-candidate offer IDOR protection (uniform 404).
7. Expired offer acceptance attempt rejected (409 OFFER_EXPIRED).
8. Declined offer resurrection attempt rejected (409 OFFER_NOT_ACTIVE).
9. Parallel accept concurrency race with 3 candidates for 1 vacancy: exactly one 200, two 409 CAPACITY_EXHAUSTED, occupied_count strictly 1.
10. Offer acceptance rejection on closed or inactive opportunity (409 OPPORTUNITY_NOT_ACTIVE).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from test_candidate import published_fixture


def _setup_app_and_interview(client, owner, candidate, org_id):
    """Helper to publish opportunity, submit application, and schedule an interview."""
    rev = published_fixture(owner, org_id)
    opp_id = rev["opportunity_id"]

    res_app = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Test application for interview"},
    )
    assert res_app.status_code == 201, res_app.text
    app_id = res_app.json()["id"]

    # Schedule interview via API-085
    start_time = now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)
    res_int = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": start_time.isoformat(),
            "ends_at": end_time.isoformat(),
            "mode": "ONLINE",
            "location_or_link": "https://meet.flexbridge.uz/interview-room",
            "timezone": "Asia/Tashkent",
        },
    )
    assert res_int.status_code in (200, 201), res_int.text
    return opp_id, app_id, res_int.json()["id"]


def _setup_app_and_offer(client, owner, candidate, org_id, capacity=1):
    """Helper to publish opportunity with given capacity, submit application, and issue an offer."""
    rev = published_fixture(owner, org_id)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == opp_id)
            .values(capacity=capacity, occupied_count=0)
        )

    res_app = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Test application for offer"},
    )
    assert res_app.status_code == 201, res_app.text
    app_id = res_app.json()["id"]

    # Issue offer via API-086
    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Junior Engineer", "stipend": 5000000}},
    )
    assert res_off.status_code in (200, 201), res_off.text
    return opp_id, app_id, res_off.json()["id"]


# =============================================================================
# 1. Unauthenticated and Malformed Tokens
# =============================================================================
def test_adversarial_unauthenticated_and_forged_tokens(client):
    """API-042 and API-043: Unauthenticated or forged token calls reject with 401."""
    random_uuid = str(uuid4())

    # 1. Interview response unauthenticated
    r1 = client.post(f"/api/v1/interviews/{random_uuid}/responses", json={"response": "ACCEPTED"})
    assert r1.status_code == 401
    assert r1.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_INVALID")

    # 2. Interview response forged token
    r2 = client.post(
        f"/api/v1/interviews/{random_uuid}/responses",
        headers={"Authorization": "Bearer forged-token-attack"},
        json={"response": "ACCEPTED"},
    )
    assert r2.status_code == 401

    # 3. Offer response unauthenticated
    r3 = client.post(f"/api/v1/offers/{random_uuid}/respond", json={"decision": "ACCEPT"})
    assert r3.status_code == 401
    assert r3.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_INVALID")

    # 4. Offer response forged token
    r4 = client.post(
        f"/api/v1/offers/{random_uuid}/respond",
        headers={"Authorization": "Bearer forged-token-attack"},
        json={"decision": "ACCEPT"},
    )
    assert r4.status_code == 401


# =============================================================================
# 2. Cross-Candidate Interview IDOR Protection
# =============================================================================
def test_adversarial_interview_cross_candidate_idor(client, identities, organization):
    """API-042: Third-party candidate attempting to respond to another's interview receives uniform 404."""
    owner = identities("OWNER", organization)
    cand_a = identities()
    cand_b = identities()

    _, _, interview_id = _setup_app_and_interview(client, owner, cand_a, organization)

    # Candidate B attempts to respond to Candidate A's interview
    r_idor = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand_b["headers"],
        json={"response": "ACCEPTED"},
    )
    assert r_idor.status_code == 404
    assert r_idor.json()["detail"]["code"] == "INTERVIEW_NOT_FOUND"

    # Non-existent interview UUID returns identical 404
    r_not_found = client.post(
        f"/api/v1/interviews/{uuid4()}/responses",
        headers=cand_b["headers"],
        json={"response": "ACCEPTED"},
    )
    assert r_not_found.status_code == 404
    assert r_not_found.json() == r_idor.json()


# =============================================================================
# 3. Foreign Organization Privilege Escalation on Interviews
# =============================================================================
def test_adversarial_interview_foreign_org_privilege_escalation(client, identities, organization):
    """API-042: Staff from a foreign organization cannot mark or cancel another org's interview."""
    owner_1 = identities("OWNER", organization)
    cand_a = identities()

    # Second organization and owner
    foreign_org_id = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table("organizations").insert().values(
                id=foreign_org_id,
                created_at=now(),
                updated_at=now(),
                tax_id=str(uuid4())[:12],
                legal_name="Foreign Org Ltd",
                public_name="Foreign Org",
                region="Samarkand",
                status="VERIFIED",
            )
        )
    owner_2 = identities("OWNER", foreign_org_id)

    _, _, interview_id = _setup_app_and_interview(client, owner_1, cand_a, organization)

    # Owner 2 from foreign org attempts to mark the interview COMPLETED
    r_escalate = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=owner_2["headers"],
        json={"response": "COMPLETED"},
    )
    assert r_escalate.status_code in (403, 404)


# =============================================================================
# 4. Terminal Interview State Lock
# =============================================================================
def test_adversarial_interview_terminal_state_lock(client, identities, organization):
    """API-042: Candidate cannot respond to CANCELLED or COMPLETED interviews."""
    owner = identities("OWNER", organization)
    cand = identities()

    _, _, interview_id = _setup_app_and_interview(client, owner, cand, organization)

    # 1. Candidate declines interview -> transitions status to CANCELLED
    r_cancel = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand["headers"],
        json={"response": "DECLINED", "note": "Candidate declined"},
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "CANCELLED"

    # Candidate attempts to accept the cancelled interview -> 409
    r_cand_accept = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand["headers"],
        json={"response": "ACCEPTED"},
    )
    assert r_cand_accept.status_code == 409
    assert r_cand_accept.json()["detail"]["code"] in ("INTERVIEW_ALREADY_FINALIZED", "INTERVIEW_NOT_ACTIVE")

    # 2. Host completes another interview -> transitions status to COMPLETED
    _, _, interview_id_2 = _setup_app_and_interview(client, owner, cand, organization)
    r_complete = client.post(
        f"/api/v1/interviews/{interview_id_2}/responses",
        headers=owner["headers"],
        json={"response": "COMPLETED", "note": "Interview done"},
    )
    assert r_complete.status_code == 200
    assert r_complete.json()["status"] == "COMPLETED"

    # Candidate attempts to reschedule a completed interview -> 409
    r_cand_resched = client.post(
        f"/api/v1/interviews/{interview_id_2}/responses",
        headers=cand["headers"],
        json={"response": "RESCHEDULE_REQUESTED"},
    )
    assert r_cand_resched.status_code == 409
    assert r_cand_resched.json()["detail"]["code"] in ("INTERVIEW_ALREADY_FINALIZED", "INTERVIEW_NOT_ACTIVE")


# =============================================================================
# 5. Invalid Interview Payload and Injection Resistance
# =============================================================================
def test_adversarial_interview_invalid_response_and_sqli_payload(client, identities, organization):
    """API-042: Invalid response choices or SQL injection payloads receive 422 validation error."""
    owner = identities("OWNER", organization)
    cand = identities()
    _, _, interview_id = _setup_app_and_interview(client, owner, cand, organization)

    # 1. Invalid status
    r_bad_status = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand["headers"],
        json={"response": "ARBITRARY_STATUS"},
    )
    assert r_bad_status.status_code == 422

    # 2. SQL injection payload
    r_sqli = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand["headers"],
        json={"response": "' OR '1'='1' --"},
    )
    assert r_sqli.status_code == 422


# =============================================================================
# 6. Cross-Candidate Offer IDOR Protection
# =============================================================================
def test_adversarial_offer_cross_candidate_idor(client, identities, organization):
    """API-043: Candidate B cannot accept or decline Candidate A's offer (uniform 404)."""
    owner = identities("OWNER", organization)
    cand_a = identities()
    cand_b = identities()

    _, _, offer_a_id = _setup_app_and_offer(client, owner, cand_a, organization)

    # Candidate B attempts to ACCEPT Candidate A's offer
    r_idor = client.post(
        f"/api/v1/offers/{offer_a_id}/respond",
        headers=cand_b["headers"],
        json={"decision": "ACCEPT"},
    )
    assert r_idor.status_code == 404
    assert r_idor.json()["detail"]["code"] == "OFFER_NOT_FOUND"

    # Non-existent offer UUID returns identical 404
    r_not_found = client.post(
        f"/api/v1/offers/{uuid4()}/respond",
        headers=cand_b["headers"],
        json={"decision": "ACCEPT"},
    )
    assert r_not_found.status_code == 404
    assert r_not_found.json() == r_idor.json()


# =============================================================================
# 7. Expired Offer Acceptance Rejection
# =============================================================================
def test_adversarial_offer_expired_rejection(client, identities, organization):
    """API-043: Candidate cannot accept an expired offer (409 OFFER_EXPIRED); capacity untouched."""
    owner = identities("OWNER", organization)
    cand = identities()

    opp_id, _, offer_id = _setup_app_and_offer(client, owner, cand, organization, capacity=1)

    # Force offer to be expired in the database
    with transaction() as conn:
        conn.execute(
            table("offers")
            .update()
            .where(table("offers").c.id == offer_id)
            .values(expires_at=now() - timedelta(minutes=10))
        )

    # Candidate attempts to accept expired offer -> 409
    r_expired = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=cand["headers"],
        json={"decision": "ACCEPT"},
    )
    assert r_expired.status_code == 409
    assert r_expired.json()["detail"]["code"] == "OFFER_EXPIRED"

    # Verify opportunity occupied_count remains 0
    with transaction() as conn:
        t_opp = table("opportunities")
        opp = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().first()
        assert opp["occupied_count"] == 0


# =============================================================================
# 8. Declined Offer Cannot Be Resurrected
# =============================================================================
def test_adversarial_offer_already_declined_cannot_reaccept(client, identities, organization):
    """API-043: Once an offer is DECLINED, candidate cannot resurrect it by calling ACCEPT."""
    owner = identities("OWNER", organization)
    cand = identities()

    opp_id, _, offer_id = _setup_app_and_offer(client, owner, cand, organization)

    # 1. Candidate declines the offer -> 200
    r_decline = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=cand["headers"],
        json={"decision": "DECLINE", "note": "Pursuing another path"},
    )
    assert r_decline.status_code == 200
    assert r_decline.json()["status"] == "DECLINED"

    # 2. Candidate attempts to ACCEPT the declined offer -> 409
    r_reaccept = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=cand["headers"],
        json={"decision": "ACCEPT"},
    )
    assert r_reaccept.status_code == 409
    assert r_reaccept.json()["detail"]["code"] in ("OFFER_NOT_ACTIVE", "OFFER_NOT_PENDING")


# =============================================================================
# 9. Concurrency Race: 3 Candidates for 1 Vacancy (AC-012 Strict Capacity)
# =============================================================================
def test_adversarial_parallel_accept_under_concurrency_race(client, identities, organization):
    """API-043 / CAP-011 / AC-012: Under concurrent accepts for 1 vacancy, exactly one succeeds (200),
    and all others fail with 409 CAPACITY_EXHAUSTED. Database occupied_count is strictly 1.
    """
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Set capacity = 1
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == opp_id)
            .values(capacity=1, occupied_count=0)
        )

    # 3 distinct candidates apply and receive offers
    candidates = [identities() for _ in range(3)]
    offers = []
    for cand in candidates:
        r_app = client.post(
            f"/api/v1/opportunities/{opp_id}/applications",
            headers=cand["headers"] | {"Idempotency-Key": f"app-race-{uuid4()}"},
            json={},
        )
        assert r_app.status_code == 201
        app_id = r_app.json()["id"]

        r_off = client.post(
            f"/api/v1/applications/{app_id}/offers",
            headers=owner["headers"],
            json={"terms_snapshot": {"position": "Engineer"}},
        )
        assert r_off.status_code in (200, 201)
        offers.append((cand, r_off.json()["id"]))

    def send_accept(cand_tuple):
        cand, off_id = cand_tuple
        return client.post(
            f"/api/v1/offers/{off_id}/respond",
            headers=cand["headers"],
            json={"decision": "ACCEPT"},
        )

    # Fire all 3 concurrent accept requests
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_accept, item) for item in offers]
        results = [f.result() for f in futures]

    statuses = [r.status_code for r in results]
    success_count = statuses.count(200)
    conflict_count = statuses.count(409)

    # Invariants under AC-012:
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}. Statuses: {statuses}"
    assert conflict_count == 2, f"Expected 2 conflicts (CAPACITY_EXHAUSTED), got {conflict_count}. Statuses: {statuses}"

    for r in results:
        if r.status_code == 409:
            assert r.json()["detail"]["code"] == "CAPACITY_EXHAUSTED"

    # Verify DB invariant: occupied_count == 1
    with transaction() as conn:
        t_opp = table("opportunities")
        opp = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().first()
        assert opp["occupied_count"] == 1
        assert opp["capacity"] == 1


# =============================================================================
# 10. Offer Acceptance on Inactive or Closed Opportunity
# =============================================================================
def test_adversarial_accept_when_opportunity_closed(client, identities, organization):
    """API-043: If organization closed the opportunity, pending offer acceptance is blocked."""
    owner = identities("OWNER", organization)
    cand = identities()

    opp_id, _, offer_id = _setup_app_and_offer(client, owner, cand, organization, capacity=2)

    # Host organization closes opportunity
    with transaction() as conn:
        conn.execute(
            table("opportunities")
            .update()
            .where(table("opportunities").c.id == opp_id)
            .values(status="CLOSED")
        )

    # Candidate attempts to accept offer for closed opportunity
    r_closed = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=cand["headers"],
        json={"decision": "ACCEPT"},
    )
    assert r_closed.status_code == 409
    assert r_closed.json()["detail"]["code"] in ("OPPORTUNITY_NOT_ACTIVE", "OPPORTUNITY_CLOSED")
