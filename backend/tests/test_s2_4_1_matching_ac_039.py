"""Automated test suite for S2.4.1: `contract_type` & compensation matrix (`INV-03`), `group_code` shifts (`INV-02`), and `API-003` `ALL`/`ANY` matching (`AC-039`, `REV-002`)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.api.v1.billing import billing_service
from app.main import app
from app.services.billing import ServiceEntitlement

client = TestClient(app)


def test_ac_039_contract_type_and_compensation_matrix_inv_03() -> None:
    """Verify `INV-03` / `AC-039`: invalid `contract_type` or mismatched `HOURLY`/`STIPEND`/`UNPAID_ACADEMIC` fails with 422 (`23514`)."""
    # 1. Invalid contract_type
    bad_ct = client.post(
        "/api/v1/opportunities/revisions",
        json={
            "organization_id": "org-1",
            "title": "Junior QA",
            "opportunity_kind": "PART_TIME_JOB",
            "contract_type": "FREELANCE_GIG_INVALID",
            "compensation_type": "HOURLY",
            "hourly_pay": 35000,
        },
    )
    assert bad_ct.status_code == 422
    assert bad_ct.json()["detail"]["code"] == "INVALID_CONTRACT_TYPE"

    # 2. HOURLY with stipend_amount > 0 must fail
    bad_matrix = client.post(
        "/api/v1/opportunities/revisions",
        json={
            "organization_id": "org-1",
            "title": "Junior QA",
            "opportunity_kind": "PART_TIME_JOB",
            "contract_type": "LABOR_PART_TIME",
            "compensation_type": "HOURLY",
            "hourly_pay": 35000,
            "stipend_amount": 1000000,
        },
    )
    assert bad_matrix.status_code == 422
    assert bad_matrix.json()["detail"]["code"] == "INVALID_COMPENSATION_CONTRACT_MATRIX"

    # 3. UNPAID_ACADEMIC on non-academic PART_TIME_JOB must fail
    bad_unpaid = client.post(
        "/api/v1/opportunities/revisions",
        json={
            "organization_id": "org-1",
            "title": "Unpaid Job Attempt",
            "opportunity_kind": "PART_TIME_JOB",
            "contract_type": "UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT",
            "compensation_type": "UNPAID_ACADEMIC",
        },
    )
    assert bad_unpaid.status_code == 422
    assert bad_unpaid.json()["detail"]["code"] == "INVALID_COMPENSATION_CONTRACT_MATRIX"


def test_ac_039_api_003_all_vs_any_shift_matching_and_exceptions() -> None:
    """Verify `AC-039` / `API-003` (`REV-002` `R2-10`):

    - Every `group_code` requires all of its shifts to be covered (`all(shift_matches)`).
    - When an opportunity has `GROUP_A` (partially covered: 2 of 3 shifts) and `GROUP_B` (fully covered: 2 of 2 shifts):
      -> `ANY_SHIFT_IN_GROUP` matches via `GROUP_B` (at least one complete shift group is covered).
      -> `ALL_SHIFTS_IN_GROUP` does NOT match (because `GROUP_A` is incomplete: 1 of 2 groups covered).
    - When Friday `[840, 1020)` availability is added so both `GROUP_A` and `GROUP_B` are completely covered:
      -> `ALL_SHIFTS_IN_GROUP` matches with `["GROUP_A", "GROUP_B"]`.
    - When an `UNAVAILABLE` exception is added on `2026-11-16` `[600, 660)`, `ALL_SHIFTS_IN_GROUP` on `check_date=2026-11-16` excludes the opportunity.
    """
    now = datetime.now(timezone.utc)
    ent = ServiceEntitlement(
        id="ent-org-uzum-ac039",
        organization_id="org-uzum",
        plan_code="ORG_PLAN_30D",
        total_post_credits=None,
        used_post_credits=0,
        concurrent_active_limit=5,
        status="ACTIVE",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=29),
    )
    billing_service._entitlements[ent.id] = ent
    billing_service._org_active_entitlement["org-uzum"] = ent.id

    cand_id = "cand-ac-039"
    for weekday in (1, 3, 5):
        r = client.post(
            f"/api/v1/candidates/{cand_id}/availability-rules",
            json={"weekday": weekday, "start_minute": 540, "end_minute": 780},
        )
        assert r.status_code == 201

    rev_resp = client.post(
        "/api/v1/opportunities/revisions",
        json={
            "organization_id": "org-uzum",
            "title": "Data Analyst Intern",
            "opportunity_kind": "GENERAL_INTERNSHIP",
            "contract_type": "PAID_INTERNSHIP_CONTRACT",
            "compensation_type": "STIPEND",
            "stipend_amount": 2500000,
        },
    )
    assert rev_resp.status_code == 201
    rev_id = rev_resp.json()["id"]

    # Add GROUP_A shifts: Mon 09-12, Wed 09-12, Fri 14-17 (candidate is NOT free Fri 14-17 -> incomplete group)
    for wd, start_m, end_m in ((1, 540, 720), (3, 540, 720), (5, 840, 1020)):
        s = client.post(
            f"/api/v1/opportunities/revisions/{rev_id}/shifts",
            json={"group_code": "GROUP_A", "weekday": wd, "start_minute": start_m, "end_minute": end_m},
        )
        assert s.status_code == 201

    # Overlapping shift in same GROUP_A on Monday must be rejected (`INV-02`, `23P01`)
    dup_shift = client.post(
        f"/api/v1/opportunities/revisions/{rev_id}/shifts",
        json={"group_code": "GROUP_A", "weekday": 1, "start_minute": 600, "end_minute": 750},
    )
    assert dup_shift.status_code == 409
    assert dup_shift.json()["detail"]["sqlstate"] == "23P01"

    # 1. Incomplete single group (2/3 shifts covered) must NOT match under EITHER mode (REV-002 R2-10)
    feed_incomplete = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ANY_SHIFT_IN_GROUP"},
    )
    assert feed_incomplete.status_code == 200
    assert feed_incomplete.json()["items"] == []

    # 2. Add alternative GROUP_B (Mon 09-12, Wed 09-12 -> 2/2 shifts covered)
    for wd in (1, 3):
        s_b = client.post(
            f"/api/v1/opportunities/revisions/{rev_id}/shifts",
            json={"group_code": "GROUP_B", "weekday": wd, "start_minute": 540, "end_minute": 720},
        )
        assert s_b.status_code == 201

    # ANY_SHIFT_IN_GROUP matches via GROUP_B (1 of 2 groups completely covered)
    feed_any = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ANY_SHIFT_IN_GROUP"},
    )
    assert len(feed_any.json()["items"]) == 1
    assert feed_any.json()["items"][0]["matched_group_codes"] == ["GROUP_B"]

    # ALL_SHIFTS_IN_GROUP does NOT match yet because GROUP_A is still incomplete
    feed_all_partial = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ALL_SHIFTS_IN_GROUP"},
    )
    assert feed_all_partial.json()["items"] == []

    # 3. Add Friday 14-17 availability so GROUP_A is also completely covered -> ALL_SHIFTS_IN_GROUP matches both groups!
    r_fri = client.post(
        f"/api/v1/candidates/{cand_id}/availability-rules",
        json={"weekday": 5, "start_minute": 840, "end_minute": 1020},
    )
    assert r_fri.status_code == 201

    feed_all_2 = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ALL_SHIFTS_IN_GROUP"},
    )
    assert len(feed_all_2.json()["items"]) == 1
    assert feed_all_2.json()["items"][0]["matched_group_codes"] == ["GROUP_A", "GROUP_B"]

    # 4. Add UNAVAILABLE exception on 2026-11-16 [600, 660) -> blocks ALL_SHIFTS_IN_GROUP on that date
    exc = client.post(
        f"/api/v1/candidates/{cand_id}/availability-exceptions",
        json={
            "exception_date": "2026-11-16",
            "start_minute": 600,
            "end_minute": 660,
            "kind": "UNAVAILABLE",
        },
    )
    assert exc.status_code == 201

    feed_all_blocked = client.get(
        "/api/v1/opportunities/feed",
        params={
            "candidate_id": cand_id,
            "schedule_match_mode": "ALL_SHIFTS_IN_GROUP",
            "check_date": "2026-11-16",
        },
    )
    assert feed_all_blocked.json()["items"] == []
