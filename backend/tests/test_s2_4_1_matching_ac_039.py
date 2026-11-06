"""Automated test suite for S2.4.1: `contract_type` & compensation matrix (`INV-03`), `group_code` shifts (`INV-02`), and `API-003` `ALL`/`ANY` matching (`AC-039`)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

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
    """Verify `AC-039` / `API-003`:

    - Candidate has Monday `[540, 780)` (09:00-13:00), Wednesday `[540, 780)`, Friday `[540, 780)`.
    - Opportunity has `GROUP_A` with 3 shifts: Mon `[540, 720)`, Wed `[540, 720)`, Fri `[840, 1020)` (14:00-17:00).
      Candidate only covers 2 of 3 shifts in `GROUP_A`:
      -> `ALL_SHIFTS_IN_GROUP` does NOT match `GROUP_A`.
      -> `ANY_SHIFT_IN_GROUP` DOES match `GROUP_A`.
    - When `GROUP_B` is added with Mon `[540, 720)` and Wed `[540, 720)`, `ALL_SHIFTS_IN_GROUP` matches via `GROUP_B`!
    - When an `UNAVAILABLE` exception is added on `2026-11-16` `[600, 660)`, `ALL_SHIFTS_IN_GROUP` on `check_date=2026-11-16` excludes `GROUP_B`.
    """
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

    # Add GROUP_A shifts: Mon 09-12, Wed 09-12, Fri 14-17 (candidate is NOT free Fri 14-17)
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

    # 1. ALL_SHIFTS_IN_GROUP must NOT match GROUP_A (only 2/3 shifts covered)
    feed_all_1 = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ALL_SHIFTS_IN_GROUP"},
    )
    assert feed_all_1.status_code == 200
    assert feed_all_1.json()["items"] == []

    # 2. ANY_SHIFT_IN_GROUP MUST match GROUP_A (2/3 >= 1 shift covered)
    feed_any_1 = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ANY_SHIFT_IN_GROUP"},
    )
    assert feed_any_1.status_code == 200
    assert len(feed_any_1.json()["items"]) == 1
    assert feed_any_1.json()["items"][0]["matched_group_codes"] == ["GROUP_A"]

    # 3. Add alternative GROUP_B (Mon 09-12, Wed 09-12) -> ALL_SHIFTS_IN_GROUP now matches GROUP_B!
    for wd in (1, 3):
        s_b = client.post(
            f"/api/v1/opportunities/revisions/{rev_id}/shifts",
            json={"group_code": "GROUP_B", "weekday": wd, "start_minute": 540, "end_minute": 720},
        )
        assert s_b.status_code == 201

    feed_all_2 = client.get(
        "/api/v1/opportunities/feed",
        params={"candidate_id": cand_id, "schedule_match_mode": "ALL_SHIFTS_IN_GROUP"},
    )
    assert len(feed_all_2.json()["items"]) == 1
    assert feed_all_2.json()["items"][0]["matched_group_codes"] == ["GROUP_B"]

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
