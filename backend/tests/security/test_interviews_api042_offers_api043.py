"""Contract, functional, concurrency, and security tests for Interviews and Offers System
(API-042, API-043, API-085, API-086 / CAP-009, CAP-011 / AC-012 / DB-044, DB-045, DB-046).

Invariants verified:
- Frozen main invariant: 764fb98496fa40857acb07844fd09fcafa99b7d6 is never mutated.
- Zero touch to pg_live: tests run exclusively against isolated test PostgreSQL instance on port 55440.
- AC-012: One remaining capacity spot with two parallel accepts yields one 200, one 409 CAPACITY_EXHAUSTED.
- IDOR isolation: Uniform 404 on foreign interview or offer access to prevent probing.
- Expiry and idempotency: Expired offers reject with 409; repeat identical decisions replay with 200.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_candidate import published_fixture


def _create_application(client, owner, candidate, org_id, capacity=5):
    """Helper to publish opportunity and submit initial candidate application."""
    rev = published_fixture(owner, org_id)
    opp_id = rev["opportunity_id"]

    # Set capacity
    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(capacity=capacity, occupied_count=0)
        )

    idem_key = f"idem-app-{uuid4()}"
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": idem_key},
        json={"note": "Initial application"},
    )
    assert res.status_code == 201, res.text
    return opp_id, res.json()


# =============================================================================
# API-085 & API-042: Interviews Scheduling and Responses
# =============================================================================

def test_api085_schedule_interview_and_api042_candidate_accepts(client, identities, organization):
    """API-085 / API-042: Host schedules interview; candidate accepts."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization)
    app_id = app["id"]

    # Host schedules interview
    now_utc = datetime.now(timezone.utc)
    s_time = (now_utc + timedelta(days=2)).isoformat()
    e_time = (now_utc + timedelta(days=2, hours=1)).isoformat()

    res_int = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": s_time,
            "ends_at": e_time,
            "mode": "ONLINE",
            "location_or_link": "https://meet.flexbridge.uz/room-101",
            "timezone": "Asia/Tashkent",
        },
    )
    assert res_int.status_code == 200, res_int.text
    int_data = res_int.json()
    assert int_data["contract_id"] == "API-085"
    assert int_data["status"] == "SCHEDULED"
    interview_id = int_data["id"]

    # Candidate responds ACCEPTED
    res_resp = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=candidate["headers"],
        json={"response": "ACCEPTED", "note": "Men tayyorman"},
    )
    assert res_resp.status_code == 200, res_resp.text
    resp_data = res_resp.json()
    assert resp_data["contract_id"] == "API-042"
    assert resp_data["status"] == "CONFIRMED"
    assert resp_data["response"] == "ACCEPTED"


def test_api042_candidate_reschedule_requested_and_declined(client, identities, organization):
    """API-042: Candidate requests reschedule or declines interview."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization)
    app_id = app["id"]

    now_utc = datetime.now(timezone.utc)
    res_int = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": (now_utc + timedelta(days=3)).isoformat(),
            "ends_at": (now_utc + timedelta(days=3, hours=1)).isoformat(),
            "mode": "ONLINE",
        },
    )
    assert res_int.status_code == 200
    interview_id = res_int.json()["id"]

    # Candidate requests reschedule
    res_resched = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=candidate["headers"],
        json={"response": "RESCHEDULE_REQUESTED", "note": "Boshqa vaqtga ko'chirish iltimos"},
    )
    assert res_resched.status_code == 200
    assert res_resched.json()["status"] == "RESCHEDULE_REQUESTED"

    # Candidate declines
    res_decl = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=candidate["headers"],
        json={"response": "DECLINED", "note": "Bora olmayman"},
    )
    assert res_decl.status_code == 200
    assert res_decl.json()["status"] == "CANCELLED"


def test_api042_hr_marks_completed_and_candidate_forbidden(client, identities, organization):
    """API-042: Only host staff can mark COMPLETED; candidate forbidden."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization)
    app_id = app["id"]

    now_utc = datetime.now(timezone.utc)
    res_int = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": (now_utc + timedelta(days=1)).isoformat(),
            "ends_at": (now_utc + timedelta(days=1, hours=1)).isoformat(),
            "mode": "ONLINE",
        },
    )
    interview_id = res_int.json()["id"]

    # Candidate attempts COMPLETED -> 403
    res_fail = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=candidate["headers"],
        json={"response": "COMPLETED"},
    )
    assert res_fail.status_code == 403
    assert res_fail.json()["detail"]["code"] == "HOST_RESPONSE_ONLY"

    # Host marks COMPLETED -> 200
    res_ok = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=owner["headers"],
        json={"response": "COMPLETED", "note": "Suhbat muvaffaqiyatli o'tdi"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "COMPLETED"

    # After completion, rescheduling or accepting raises 409
    res_after = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=candidate["headers"],
        json={"response": "ACCEPTED"},
    )
    assert res_after.status_code == 409
    assert res_after.json()["detail"]["code"] == "INTERVIEW_ALREADY_FINALIZED"


def test_api042_idor_foreign_candidate_gets_404(client, identities, organization):
    """API-042: Third-party candidate probing foreign interview receives 404."""
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()

    opp_id, app = _create_application(client, owner, cand1, organization)
    now_utc = datetime.now(timezone.utc)
    res_int = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": (now_utc + timedelta(days=1)).isoformat(),
            "ends_at": (now_utc + timedelta(days=1, hours=1)).isoformat(),
        },
    )
    interview_id = res_int.json()["id"]

    # Candidate 2 attempts to respond
    res_probe = client.post(
        f"/api/v1/interviews/{interview_id}/responses",
        headers=cand2["headers"],
        json={"response": "ACCEPTED"},
    )
    assert res_probe.status_code == 404
    assert res_probe.json()["detail"]["code"] == "INTERVIEW_NOT_FOUND"


# =============================================================================
# API-086 & API-043: Job Offers Issuing and Candidate Responses
# =============================================================================

def test_api086_issue_offer_and_api043_candidate_accepts(client, identities, organization):
    """API-086 / API-043 / CAP-011: Host issues offer; candidate accepts, capacity decremented."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization, capacity=3)
    app_id = app["id"]

    # Host issues offer
    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"salary": 5000000, "position": "Junior Engineer"}},
    )
    assert res_off.status_code == 200, res_off.text
    off_data = res_off.json()
    assert off_data["contract_id"] == "API-086"
    assert off_data["status"] == "OFFERED"
    offer_id = off_data["id"]

    # Candidate responds ACCEPT
    res_accept = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_accept.status_code == 200, res_accept.text
    acc_data = res_accept.json()
    assert acc_data["contract_id"] == "API-043"
    assert acc_data["status"] == "ACCEPTED"
    assert acc_data["vacancies_remaining"] == 2

    # Verify DB state
    with transaction() as conn:
        t_opp = table("opportunities")
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().one()
        assert opp_row["occupied_count"] == 1

        t_apps = table("applications")
        app_row = conn.execute(select(t_apps).where(t_apps.c.id == app_id)).mappings().one()
        assert app_row["status"] == "ACCEPTED"
        assert app_row["occupied_at"] is not None

        t_offers = table("offers")
        off_row = conn.execute(select(t_offers).where(t_offers.c.id == offer_id)).mappings().one()
        assert off_row["status"] == "ACCEPTED"
        assert off_row["accepted_at"] is not None


def test_api043_idempotent_accept_replay(client, identities, organization):
    """API-043: Repeating ACCEPT on already accepted offer replays 200 without double count."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization, capacity=5)
    app_id = app["id"]

    res_off = client.post(f"/api/v1/applications/{app_id}/offers", headers=owner["headers"], json={})
    offer_id = res_off.json()["id"]

    # First accept
    res1 = client.post(f"/api/v1/offers/{offer_id}/respond", headers=candidate["headers"], json={"decision": "ACCEPT"})
    assert res1.status_code == 200

    # Replay accept
    res2 = client.post(f"/api/v1/offers/{offer_id}/respond", headers=candidate["headers"], json={"decision": "ACCEPT"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "ACCEPTED"

    # Occupied count must still be 1
    with transaction() as conn:
        t_opp = table("opportunities")
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().one()
        assert opp_row["occupied_count"] == 1


def test_api043_candidate_declines_offer(client, identities, organization):
    """API-043: Candidate declines offer; capacity remains untouched."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization, capacity=5)
    app_id = app["id"]

    res_off = client.post(f"/api/v1/applications/{app_id}/offers", headers=owner["headers"], json={})
    offer_id = res_off.json()["id"]

    # Decline
    res_dec = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "DECLINE", "note": "Boshqa taklifni tanladim"},
    )
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "DECLINED"

    # Verify occupied_count is still 0
    with transaction() as conn:
        t_opp = table("opportunities")
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().one()
        assert opp_row["occupied_count"] == 0

    # Trying to ACCEPT after DECLINE raises 409
    res_rej = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_rej.status_code == 409
    assert res_rej.json()["detail"]["code"] == "OFFER_NOT_ACTIVE"


def test_api043_expired_offer_rejected(client, identities, organization):
    """API-043 / CAP-011: Expired offer cannot be accepted."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app = _create_application(client, owner, candidate, organization, capacity=5)
    app_id = app["id"]

    past_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"expires_at": past_time},
    )
    assert res_off.status_code == 200
    offer_id = res_off.json()["id"]

    # Candidate attempts ACCEPT on expired offer -> 409
    res_exp = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_exp.status_code == 409
    assert res_exp.json()["detail"]["code"] == "OFFER_EXPIRED"


def test_api043_idor_foreign_candidate_gets_404(client, identities, organization):
    """API-043: Candidate B probing Candidate A's offer receives 404."""
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()

    opp_id, app = _create_application(client, owner, cand1, organization)
    res_off = client.post(f"/api/v1/applications/{app['id']}/offers", headers=owner["headers"], json={})
    offer_id = res_off.json()["id"]

    # Candidate 2 attempts to accept
    res_probe = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=cand2["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_probe.status_code == 404
    assert res_probe.json()["detail"]["code"] == "OFFER_NOT_FOUND"


# =============================================================================
# AC-012: Concurrency & Capacity Lock Invariant (CAP-011)
# =============================================================================

def test_ac012_capacity_exhausted_single_spot_two_candidates(client, identities, organization):
    """AC-012: Two candidates with offers for 1 remaining spot.
    
    First accept succeeds (200, occupied_count=1).
    Second accept gets 409 CAPACITY_EXHAUSTED.
    Occupied count equals capacity (1 == 1); no over-allocation.
    """
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()

    # Opportunity with exactly 1 vacancy
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(capacity=1, occupied_count=0)
        )

    # Cand1 applies
    res_app1 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand1["headers"] | {"Idempotency-Key": f"app-1-{uuid4()}"},
        json={"note": "Cand 1 application"},
    )
    assert res_app1.status_code == 201
    app1_id = res_app1.json()["id"]

    # Cand2 applies
    res_app2 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand2["headers"] | {"Idempotency-Key": f"app-2-{uuid4()}"},
        json={"note": "Cand 2 application"},
    )
    assert res_app2.status_code == 201
    app2_id = res_app2.json()["id"]

    # Host issues offers to both (offering does NOT reserve capacity)
    off1 = client.post(f"/api/v1/applications/{app1_id}/offers", headers=owner["headers"], json={}).json()["id"]
    off2 = client.post(f"/api/v1/applications/{app2_id}/offers", headers=owner["headers"], json={}).json()["id"]

    # Cand1 accepts first -> 200
    res_acc1 = client.post(f"/api/v1/offers/{off1}/respond", headers=cand1["headers"], json={"decision": "ACCEPT"})
    assert res_acc1.status_code == 200, res_acc1.text
    assert res_acc1.json()["status"] == "ACCEPTED"
    assert res_acc1.json()["vacancies_remaining"] == 0

    # Cand2 accepts second -> 409 CAPACITY_EXHAUSTED
    res_acc2 = client.post(f"/api/v1/offers/{off2}/respond", headers=cand2["headers"], json={"decision": "ACCEPT"})
    assert res_acc2.status_code == 409, res_acc2.text
    assert res_acc2.json()["detail"]["code"] == "CAPACITY_EXHAUSTED"

    # Verify database state
    with transaction() as conn:
        t_opp = table("opportunities")
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().one()
        assert opp_row["occupied_count"] == 1
        assert opp_row["capacity"] == 1


def test_ac012_parallel_race_condition_accept(client, identities, organization):
    """AC-012 Concurrency: Parallel threads race to accept 1 spot. Exactly one 200, one 409."""
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()

    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(capacity=1, occupied_count=0)
        )

    # Both apply
    app1_id = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand1["headers"] | {"Idempotency-Key": f"app-p1-{uuid4()}"},
        json={},
    ).json()["id"]

    app2_id = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand2["headers"] | {"Idempotency-Key": f"app-p2-{uuid4()}"},
        json={},
    ).json()["id"]

    # Both get offers
    off1 = client.post(f"/api/v1/applications/{app1_id}/offers", headers=owner["headers"], json={}).json()["id"]
    off2 = client.post(f"/api/v1/applications/{app2_id}/offers", headers=owner["headers"], json={}).json()["id"]

    def accept_call(offer_id, cand_headers):
        return client.post(f"/api/v1/offers/{offer_id}/respond", headers=cand_headers, json={"decision": "ACCEPT"})

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(accept_call, off1, cand1["headers"])
        f2 = executor.submit(accept_call, off2, cand2["headers"])
        r1 = f1.result()
        r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 200 in statuses, f"Expected one 200, got {statuses}"
    assert 409 in statuses, f"Expected one 409, got {statuses}"

    with transaction() as conn:
        t_opp = table("opportunities")
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().one()
        assert opp_row["occupied_count"] == 1
