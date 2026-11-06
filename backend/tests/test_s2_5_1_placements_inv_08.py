"""Automated test suite for S2.5.1: Applications, Offers, Placements `INV-08` composite FK checks, and two-party start confirmation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_inv_08_application_attempts_and_placements_composite_fk_scope() -> None:
    """Verify `INV-08` rejects `application_attempts` and `placements` referencing a mismatched `opportunity_id` (`23503`)."""
    app_1 = client.post(
        "/api/v1/applications",
        json={"opportunity_id": "opp-101", "candidate_id": "cand-101"},
    ).json()

    # 1. Attempt referencing wrong opportunity_id ("opp-999") must fail with 409 (`23503`)
    bad_attempt = client.post(
        f"/api/v1/applications/{app_1['id']}/attempts",
        json={"opportunity_id": "opp-999", "attempt_no": 1},
    )
    assert bad_attempt.status_code == 409
    assert bad_attempt.json()["detail"]["sqlstate"] == "23503"

    # Valid attempt succeeds
    ok_attempt = client.post(
        f"/api/v1/applications/{app_1['id']}/attempts",
        json={"opportunity_id": "opp-101", "attempt_no": 1},
    )
    assert ok_attempt.status_code == 201

    offer = client.post(
        "/api/v1/offers",
        json={
            "application_id": app_1["id"],
            "opportunity_id": "opp-101",
            "candidate_id": "cand-101",
            "offered_by": "hr-1",
        },
    ).json()

    # 2. Placement referencing mismatched opportunity_id ("opp-999") must fail with 409 (`23503`)
    bad_placement = client.post(
        "/api/v1/placements",
        json={
            "application_id": app_1["id"],
            "offer_id": offer["id"],
            "opportunity_id": "opp-999",
            "candidate_id": "cand-101",
            "organization_id": "org-1",
        },
    )
    assert bad_placement.status_code == 409
    assert bad_placement.json()["detail"]["sqlstate"] == "23503"


def test_placement_requires_two_party_start_confirmation() -> None:
    """Verify a placement transitions to `ACTIVE` only after both `CANDIDATE` and `ORGANIZATION` confirm work start."""
    app_row = client.post(
        "/api/v1/applications",
        json={"opportunity_id": "opp-202", "candidate_id": "cand-202"},
    ).json()
    offer = client.post(
        "/api/v1/offers",
        json={
            "application_id": app_row["id"],
            "opportunity_id": "opp-202",
            "candidate_id": "cand-202",
            "offered_by": "hr-2",
        },
    ).json()
    placement = client.post(
        "/api/v1/placements",
        json={
            "application_id": app_row["id"],
            "offer_id": offer["id"],
            "opportunity_id": "opp-202",
            "candidate_id": "cand-202",
            "organization_id": "org-2",
        },
    ).json()
    pid = placement["id"]
    assert placement["status"] == "PENDING_START_CONFIRMATION"

    # Candidate confirms first -> still PENDING_START_CONFIRMATION
    c1 = client.post(f"/api/v1/placements/{pid}/confirm-start", json={"party": "CANDIDATE"})
    assert c1.status_code == 200
    assert c1.json()["status"] == "PENDING_START_CONFIRMATION"

    # Organization confirms second -> now ACTIVE!
    c2 = client.post(f"/api/v1/placements/{pid}/confirm-start", json={"party": "ORGANIZATION"})
    assert c2.status_code == 200
    assert c2.json()["status"] == "ACTIVE"
