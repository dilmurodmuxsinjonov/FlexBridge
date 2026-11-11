"""Adversarial and security tests for Application HR Review & Transitions (CAP-008 / APPLICATION_HR).

Tests:
1. Unauthenticated requests blocked with 401.
2. Candidate tokens attempting HR operations rejected.
3. Cross-tenant IDOR attacks return uniform 404 (zero resource enumeration).
4. HOST_COORDINATOR restricted exclusively to INTERNSHIP (403 on PART_TIME).
5. Invalid state transitions rejected with 409 INVALID_APPLICATION_TRANSITION.
6. Terminal state mutations rejected with 409 APPLICATION_TERMINAL_STATE.
7. Zero cross-opportunity data leaks within the same organization.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_candidate import published_fixture


def _create_opp_with_kind(conn, org_id: str, author_id: str, kind: str = "INTERNSHIP") -> str:
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    created = now()
    is_paid = (kind == "PART_TIME")

    insert_row(
        conn,
        "opportunities",
        id=opp_id,
        organization_id=org_id,
        kind=kind,
        status="PUBLISHED",
        capacity=5,
        occupied_count=0,
        current_revision_id=rev_id,
        created_at=created,
        updated_at=created,
    )
    insert_row(
        conn,
        "opportunity_revisions",
        id=rev_id,
        opportunity_id=opp_id,
        revision=1,
        author_id=author_id,
        title=f"Sample {kind} Opportunity",
        description="Description",
        region="Tashkent",
        work_mode="HYBRID",
        contract_type="INTERNSHIP_AGREEMENT" if kind == "INTERNSHIP" else "LABOR_PART_TIME",
        eligibility="ALL_CANDIDATES",
        currency="UZS",
        is_paid=is_paid,
        salary_min=Decimal("35000.0") if is_paid else None,
        salary_period="HOUR" if is_paid else None,
        salary_basis="GROSS" if is_paid else None,
        start_date=created.date(),
        schedule_policy="FLEXIBLE",
        shift_match_mode="ALL_SHIFTS_IN_GROUP",
        snapshot_schema=1,
        published_at=created,
        created_at=created,
        updated_at=created,
    )
    return opp_id


def test_adversarial_unauthenticated_requests_blocked(client: TestClient):
    """Guest requests without token must receive 401."""
    fake_id = str(uuid4())
    assert client.get(f"/api/v1/opportunities/{fake_id}/applications").status_code == 401
    assert client.post(f"/api/v1/applications/{fake_id}/transition", json={"to_status": "REVIEWING"}).status_code == 401
    assert client.get(f"/api/v1/applications/{fake_id}/hr").status_code == 401


def test_adversarial_candidate_caller_forbidden(client: TestClient, identities, organization):
    """Candidate callers must not be able to list applications or trigger HR transitions."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    # Apply
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-cand-{uuid4()}"},
        json={"note": "Candidate application"},
    )
    assert res.status_code == 201
    app_id = res.json()["id"]

    # Candidate attempts to call HR endpoints
    assert client.get(f"/api/v1/opportunities/{opp_id}/applications", headers=candidate["headers"]).status_code in (403, 404)
    assert client.post(f"/api/v1/applications/{app_id}/transition", headers=candidate["headers"], json={"to_status": "REVIEWING"}).status_code in (403, 404)
    assert client.get(f"/api/v1/applications/{app_id}/hr", headers=candidate["headers"]).status_code in (403, 404)


def test_adversarial_cross_tenant_idor_anti_enumeration(client: TestClient, identities, organization):
    """Staff of Organization B attempting to access Organization A resources receive uniform 404."""
    owner_a = identities("OWNER", organization)
    rev = published_fixture(owner_a, organization)
    opp_id = rev["opportunity_id"]

    # Candidate applies to Org A
    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-cross-{uuid4()}"},
        json={"note": "Org A candidate"},
    )
    assert res.status_code == 201
    app_id = res.json()["id"]

    # Create Org B with different owner
    org_b_id = str(uuid4())
    with transaction() as conn:
        insert_row(
            conn,
            "organizations",
            id=org_b_id,
            tax_id=f"99{str(uuid4().int)[:7]}",
            legal_name="Competitor Corp LLC",
            public_name="Competitor Corp",
            region="Tashkent",
            status="VERIFIED",
            created_at=now(),
            updated_at=now(),
        )
    owner_b = identities("OWNER", org_b_id)

    # Org B owner attempts to view Org A opportunity applications -> uniform 404
    res_list = client.get(f"/api/v1/opportunities/{opp_id}/applications", headers=owner_b["headers"])
    assert res_list.status_code == 404, res_list.text
    assert res_list.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"

    # Org B owner attempts to transition Org A application -> uniform 404
    res_trans = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner_b["headers"],
        json={"to_status": "REVIEWING"},
    )
    assert res_trans.status_code == 404, res_trans.text
    assert res_trans.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"

    # Org B owner attempts to get HR detail of Org A application -> uniform 404
    res_detail = client.get(f"/api/v1/applications/{app_id}/hr", headers=owner_b["headers"])
    assert res_detail.status_code == 404, res_detail.text
    assert res_detail.json()["detail"]["code"] == "APPLICATION_NOT_FOUND"


def test_adversarial_host_coordinator_restricted_to_internship(client: TestClient, identities, organization):
    """HOST_COORDINATOR can manage INTERNSHIP applications but is forbidden (403) from PART_TIME."""
    hc = identities("HOST_COORDINATOR", organization)
    owner = identities("OWNER", organization)

    with transaction() as conn:
        opp_pt = _create_opp_with_kind(conn, org_id=organization, author_id=owner["user_id"], kind="PART_TIME")
        opp_intern = _create_opp_with_kind(conn, org_id=organization, author_id=owner["user_id"], kind="INTERNSHIP")

    candidate = identities()
    # Apply to PART_TIME
    res_pt = client.post(
        f"/api/v1/opportunities/{opp_pt}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-pt-{uuid4()}"},
        json={"note": "PT app"},
    )
    assert res_pt.status_code == 201
    app_pt_id = res_pt.json()["id"]

    # Apply to INTERNSHIP
    c2 = identities()
    res_in = client.post(
        f"/api/v1/opportunities/{opp_intern}/applications",
        headers=c2["headers"] | {"Idempotency-Key": f"idem-in-{uuid4()}"},
        json={"note": "Intern app"},
    )
    assert res_in.status_code == 201
    app_in_id = res_in.json()["id"]

    # 1. PART_TIME access by HOST_COORDINATOR must return 403
    pt_list = client.get(f"/api/v1/opportunities/{opp_pt}/applications", headers=hc["headers"])
    assert pt_list.status_code == 403, pt_list.text
    assert pt_list.json()["detail"]["code"] == "HOST_COORDINATOR_INTERNSHIP_ONLY"

    pt_trans = client.post(
        f"/api/v1/applications/{app_pt_id}/transition",
        headers=hc["headers"],
        json={"to_status": "REVIEWING"},
    )
    assert pt_trans.status_code == 403, pt_trans.text
    assert pt_trans.json()["detail"]["code"] == "HOST_COORDINATOR_INTERNSHIP_ONLY"

    pt_hr = client.get(f"/api/v1/applications/{app_pt_id}/hr", headers=hc["headers"])
    assert pt_hr.status_code == 403, pt_hr.text
    assert pt_hr.json()["detail"]["code"] == "HOST_COORDINATOR_INTERNSHIP_ONLY"

    # 2. INTERNSHIP access by HOST_COORDINATOR must succeed (200)
    in_list = client.get(f"/api/v1/opportunities/{opp_intern}/applications", headers=hc["headers"])
    assert in_list.status_code == 200, in_list.text

    in_trans = client.post(
        f"/api/v1/applications/{app_in_id}/transition",
        headers=hc["headers"],
        json={"to_status": "REVIEWING"},
    )
    assert in_trans.status_code == 200, in_trans.text

    in_hr = client.get(f"/api/v1/applications/{app_in_id}/hr", headers=hc["headers"])
    assert in_hr.status_code == 200, in_hr.text


def test_adversarial_invalid_state_transitions(client: TestClient, identities, organization):
    """Invalid transitions and malformed status names are rejected."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-invalid-{uuid4()}"},
        json={"note": "Submission"},
    )
    assert res.status_code == 201
    app_id = res.json()["id"]

    # 1. Invalid status name -> 422
    res_bad = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "HIRED_UNKNOWN"},
    )
    assert res_bad.status_code == 422, res_bad.text

    # 2. Skip review straight to OFFER_PENDING -> 409
    res_skip = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "OFFER_PENDING"},
    )
    assert res_skip.status_code == 409, res_skip.text
    assert res_skip.json()["detail"]["code"] == "INVALID_APPLICATION_TRANSITION"


def test_adversarial_terminal_state_immutability(client: TestClient, identities, organization):
    """Terminal states (REJECTED, WITHDRAWN) cannot be transitioned."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-terminal-{uuid4()}"},
        json={"note": "Submission"},
    )
    assert res.status_code == 201
    app_id = res.json()["id"]

    # Reject application -> becomes REJECTED
    rej = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REJECTED", "reason": "Not a match"},
    )
    assert rej.status_code == 200

    # Attempt to transition REJECTED back to REVIEWING -> 409 APPLICATION_TERMINAL_STATE
    retry = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REVIEWING"},
    )
    assert retry.status_code == 409, retry.text
    assert retry.json()["detail"]["code"] == "APPLICATION_TERMINAL_STATE"


def test_adversarial_zero_cross_opportunity_leak(client: TestClient, identities, organization):
    """Applications for Opportunity A never appear in Opportunity B application list."""
    owner = identities("OWNER", organization)
    rev1 = published_fixture(owner, organization)
    rev2 = published_fixture(owner, organization)
    opp1_id = rev1["opportunity_id"]
    opp2_id = rev2["opportunity_id"]

    # Candidate applies to Opp 1 only
    candidate = identities()
    res1 = client.post(
        f"/api/v1/opportunities/{opp1_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-opp1-{uuid4()}"},
        json={"note": "Opp 1 only"},
    )
    assert res1.status_code == 201
    app1_id = res1.json()["id"]

    # List Opp 1 applications -> contains app1
    l1 = client.get(f"/api/v1/opportunities/{opp1_id}/applications", headers=owner["headers"])
    assert l1.status_code == 200
    ids1 = [item["application_id"] for item in l1.json()["items"]]
    assert app1_id in ids1

    # List Opp 2 applications -> MUST NOT contain app1
    l2 = client.get(f"/api/v1/opportunities/{opp2_id}/applications", headers=owner["headers"])
    assert l2.status_code == 200
    ids2 = [item["application_id"] for item in l2.json()["items"]]
    assert app1_id not in ids2
