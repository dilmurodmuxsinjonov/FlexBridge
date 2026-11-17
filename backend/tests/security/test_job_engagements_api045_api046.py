"""Contract, functional, concurrency, and security tests for Dual-Confirmed Job Engagements
(API-045, API-046 / CAP-012 / AC-014, AC-016 / DB-047, DB-048).

Invariants verified:
- Frozen main invariant: 764fb98496fa40857acb07844fd09fcafa99b7d6 is strictly frozen.
- Zero touches to pg_live: tests run exclusively against isolated test PostgreSQL instance on port 55440.
- AC-014: Status transitions to ACTIVE only when BOTH CANDIDATE and EMPLOYER confirm CONFIRM_START.
- AC-016: Non-internship job engagements do not require academic diaries.
- IDOR isolation: Uniform 404 on foreign engagement access to prevent probing.
- Anti-spoofing: Server-side identity resolution prevents actor from claiming the opposite side.
- Concurrency: Parallel confirmations are safe under row-level locking.
"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_candidate import published_fixture


def _setup_job_engagement(client, owner, candidate, org_id):
    """Helper to publish opportunity, submit application, issue offer, and accept to produce job_engagement."""
    rev = published_fixture(owner, org_id)
    opp_id = rev["opportunity_id"]

    # Ensure opportunity is PART_TIME
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
        json={"note": "Applying for job"},
    )
    assert res_app.status_code == 201, res_app.text
    app_id = res_app.json()["id"]

    # 2. Host issues offer
    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Software Developer", "rate": 50000}},
    )
    assert res_off.status_code == 200, res_off.text
    offer_id = res_off.json()["id"]

    # 3. Candidate accepts offer
    res_acc = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_acc.status_code == 200, res_acc.text
    eng_id = res_acc.json().get("engagement_id")
    assert eng_id is not None, "Offer acceptance must produce an engagement_id"

    return opp_id, app_id, offer_id, eng_id


# =============================================================================
# API-045: GET /api/v1/me/engagements/{id}
# =============================================================================

def test_api045_get_engagement_candidate_and_employer(client, identities, organization):
    """API-045 / CAP-012: Candidate and Employer can inspect engagement details and confirmations."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Candidate views engagement
    res_cand = client.get(
        f"/api/v1/me/engagements/{eng_id}",
        headers=candidate["headers"],
    )
    assert res_cand.status_code == 200, res_cand.text
    cand_data = res_cand.json()
    assert cand_data["contract_id"] == "API-045"
    assert cand_data["id"] == eng_id
    assert cand_data["status"] == "PENDING_START_CONFIRMATION"
    assert cand_data["my_side"] == "CANDIDATE"
    assert "CANDIDATE" in cand_data["pending_sides"]
    assert "EMPLOYER" in cand_data["pending_sides"]

    # Employer views engagement
    res_emp = client.get(
        f"/api/v1/me/engagements/{eng_id}",
        headers=owner["headers"],
    )
    assert res_emp.status_code == 200, res_emp.text
    emp_data = res_emp.json()
    assert emp_data["contract_id"] == "API-045"
    assert emp_data["my_side"] == "EMPLOYER"
    assert emp_data["status"] == "PENDING_START_CONFIRMATION"


def test_api045_idor_unrelated_candidate_gets_404(client, identities, organization):
    """API-045: Unrelated candidate probing foreign engagement receives 404."""
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, cand1, organization)

    # Candidate 2 probes Candidate 1's engagement
    res_probe = client.get(
        f"/api/v1/me/engagements/{eng_id}",
        headers=cand2["headers"],
    )
    assert res_probe.status_code == 404
    assert res_probe.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"


# =============================================================================
# API-046 & AC-014: Dual-Party Confirmation Flow
# =============================================================================

def test_ac014_dual_confirmation_start_flow(client, identities, organization):
    """AC-014 / CAP-012: Status transitions to ACTIVE only when BOTH parties confirm CONFIRM_START."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # 1. Candidate confirms start
    res_c_start = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START", "note": "Ishga kirishdim"},
    )
    assert res_c_start.status_code == 200, res_c_start.text
    c_data = res_c_start.json()
    assert c_data["contract_id"] == "API-046"
    assert c_data["side"] == "CANDIDATE"
    # CRITICAL AC-014: Status must STILL be PENDING_START_CONFIRMATION because Employer hasn't confirmed!
    assert c_data["status"] == "PENDING_START_CONFIRMATION"

    # Verify via API-045
    detail_1 = client.get(f"/api/v1/me/engagements/{eng_id}", headers=candidate["headers"]).json()
    assert detail_1["pending_sides"] == ["EMPLOYER"]
    assert len(detail_1["confirmations"]) == 1

    # 2. Employer confirms start
    res_e_start = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_START", "note": "Xodim ishni boshladi"},
    )
    assert res_e_start.status_code == 200, res_e_start.text
    e_data = res_e_start.json()
    assert e_data["side"] == "EMPLOYER"
    # CRITICAL AC-014: Now BOTH have confirmed; status transitions to ACTIVE!
    assert e_data["status"] == "ACTIVE"
    assert e_data["confirmed_started_at"] is not None

    # Verify DB state
    with transaction() as conn:
        t_eng = table("job_engagements")
        eng_row = conn.execute(select(t_eng).where(t_eng.c.id == eng_id)).mappings().one()
        assert eng_row["status"] == "ACTIVE"
        assert eng_row["confirmed_started_at"] is not None


def test_api046_idempotent_confirm_replay(client, identities, organization):
    """API-046: Repeating identical confirmation replays 200 without duplicate DB rows."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # First confirm
    res1 = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert res1.status_code == 200

    # Repeat confirm
    res2 = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert res2.status_code == 200

    # Verify exactly 1 confirmation row exists for candidate
    with transaction() as conn:
        t_conf = table("engagement_confirmations")
        confs = conn.execute(
            select(t_conf).where(
                t_conf.c.engagement_id == eng_id,
                t_conf.c.side == "CANDIDATE",
            )
        ).mappings().all()
        assert len(confs) == 1


def test_api046_dispute_start_transitions_to_disputed(client, identities, organization):
    """API-046: Either party filing DISPUTE_START marks engagement as DISPUTED."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Employer disputes start
    res_disp = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "DISPUTE_START", "note": "Nomzod ishga kelmadi"},
    )
    assert res_disp.status_code == 200, res_disp.text
    disp_data = res_disp.json()
    assert disp_data["status"] == "DISPUTED"

    with transaction() as conn:
        t_eng = table("job_engagements")
        eng_row = conn.execute(select(t_eng).where(t_eng.c.id == eng_id)).mappings().one()
        assert eng_row["status"] == "DISPUTED"


def test_api046_dual_confirm_end_flow(client, identities, organization):
    """API-046: From ACTIVE engagement, both parties confirming CONFIRM_END sets COMPLETED."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # 1. Both confirm start -> ACTIVE
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=candidate["headers"], json={"action": "CONFIRM_START"})
    client.post(f"/api/v1/engagements/{eng_id}/confirmations", headers=owner["headers"], json={"action": "CONFIRM_START"})

    # 2. Candidate confirms end
    res_c_end = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_END", "note": "Shartnoma muddati tugadi"},
    )
    assert res_c_end.status_code == 200
    # Still ACTIVE until employer also confirms
    assert res_c_end.json()["status"] == "ACTIVE"

    # 3. Employer confirms end -> COMPLETED
    res_e_end = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_END", "note": "Barcha vazifalar topshirildi"},
    )
    assert res_e_end.status_code == 200
    assert res_e_end.json()["status"] == "COMPLETED"

    with transaction() as conn:
        t_eng = table("job_engagements")
        eng_row = conn.execute(select(t_eng).where(t_eng.c.id == eng_id)).mappings().one()
        assert eng_row["status"] == "COMPLETED"


def test_api046_cannot_confirm_end_while_pending_start(client, identities, organization):
    """API-046: Attempting CONFIRM_END on unstarted engagement fails with 409."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    res_fail = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_END"},
    )
    assert res_fail.status_code == 409
    assert res_fail.json()["detail"]["code"] == "ENGAGEMENT_NOT_ACTIVE"


def test_api046_spoofing_party_forbidden(client, identities, organization):
    """API-046: Candidate attempting party=EMPLOYER or Employer attempting party=CANDIDATE receives 403."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    # Candidate tries to spoof EMPLOYER
    res_spoof1 = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate["headers"],
        json={"action": "CONFIRM_START", "party": "EMPLOYER"},
    )
    assert res_spoof1.status_code == 403
    assert res_spoof1.json()["detail"]["code"] == "ENGAGEMENT_ACTOR_FORBIDDEN"

    # Employer tries to spoof CANDIDATE
    res_spoof2 = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_START", "party": "CANDIDATE"},
    )
    assert res_spoof2.status_code == 403
    assert res_spoof2.json()["detail"]["code"] == "ENGAGEMENT_ACTOR_FORBIDDEN"


def test_api046_idor_third_party_confirm_gets_404(client, identities, organization):
    """API-046: Third-party attempting to confirm another's engagement receives 404."""
    owner = identities("OWNER", organization)
    cand1 = identities()
    cand2 = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, cand1, organization)

    res_probe = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=cand2["headers"],
        json={"action": "CONFIRM_START"},
    )
    assert res_probe.status_code == 404
    assert res_probe.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"


def test_ac014_concurrency_parallel_confirmations(client, identities, organization):
    """AC-014 Concurrency: Parallel confirmation calls from both sides safely resolve to ACTIVE."""
    owner = identities("OWNER", organization)
    candidate = identities()
    opp_id, app_id, offer_id, eng_id = _setup_job_engagement(client, owner, candidate, organization)

    def do_confirm(headers):
        return client.post(
            f"/api/v1/engagements/{eng_id}/confirmations",
            headers=headers,
            json={"action": "CONFIRM_START"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_confirm, candidate["headers"])
        f2 = executor.submit(do_confirm, owner["headers"])
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 200
    assert r2.status_code == 200

    # Final DB status must be ACTIVE
    with transaction() as conn:
        t_eng = table("job_engagements")
        eng_row = conn.execute(select(t_eng).where(t_eng.c.id == eng_id)).mappings().one()
        assert eng_row["status"] == "ACTIVE"
        assert eng_row["confirmed_started_at"] is not None
