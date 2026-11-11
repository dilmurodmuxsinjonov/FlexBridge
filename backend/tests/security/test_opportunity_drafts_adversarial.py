"""Adversarial and security tests for Opportunity Drafting (API-078, API-079, API-080).

Security & Invariant Verification:
- IDOR Resistance: Foreign org staff and candidates receive uniform 404 OPPORTUNITY_NOT_FOUND.
- Role Boundaries: HOST_COORDINATOR is strictly restricted to INTERNSHIP opportunities (403 on PART_TIME).
- AC-008 Immutability: Published opportunities reject any draft mutation with 409 OPPORTUNITY_NOT_DRAFT.
- Labor Invariants: Unpaid PART_TIME rejected with 422 UNPAID_PART_TIME_FORBIDDEN.
- INV-02 Shift Overlap: Conflicting shifts within same group/weekday rejected with 409 OVERLAPPING_OPPORTUNITY_SHIFT.
- Capacity Safety: Capacity < occupied_count rejected with 409 CAPACITY_LESS_THAN_OCCUPIED.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from uuid import uuid4
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def _create_opp(
    conn,
    *,
    org_id: str,
    author_id: str,
    title: str = "Test Opp",
    kind: str = "PART_TIME",
    status: str = "DRAFT",
    capacity: int = 5,
    occupied_count: int = 2,
    is_paid: bool = True,
    salary_min: float = 35000.0,
) -> str:
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    created = now()

    insert_row(
        conn,
        "opportunities",
        id=opp_id,
        organization_id=org_id,
        kind=kind,
        status=status,
        capacity=capacity,
        occupied_count=occupied_count,
        created_at=created,
        updated_at=created,
        published_at=created if status == "PUBLISHED" else None,
    )

    insert_row(
        conn,
        "opportunity_revisions",
        id=rev_id,
        opportunity_id=opp_id,
        revision=1,
        author_id=author_id,
        title=title,
        description=f"Description of {title}",
        region="Tashkent",
        work_mode="HYBRID",
        eligibility="ALL_CANDIDATES",
        contract_type="LABOR_PART_TIME" if kind == "PART_TIME" else "INTERNSHIP_AGREEMENT",
        currency="UZS",
        is_paid=is_paid,
        salary_min=Decimal(str(salary_min)) if is_paid else None,
        salary_period="HOUR" if is_paid else None,
        salary_basis="GROSS" if is_paid else None,
        start_date=created.date(),
        schedule_policy="FIXED",
        shift_match_mode="ALL_SHIFTS_IN_GROUP",
        snapshot_schema=1,
        created_at=created,
        updated_at=created,
        published_at=created if status == "PUBLISHED" else None,
    )

    conn.execute(
        table("opportunities").update().where(table("opportunities").c.id == opp_id).values(current_revision_id=rev_id)
    )
    return opp_id


def test_idor_unrelated_org_returns_uniform_404(client: TestClient, identities, organization):
    """IDOR Protection: Staff from another organization cannot probe or modify draft; receives 404."""
    org_a = organization
    owner_a = identities("OWNER", org_a)

    # Create Org B
    with transaction() as conn:
        org_b = str(uuid4())
        insert_row(
            conn,
            "organizations",
            id=org_b,
            tax_id=f"99{str(uuid4().int)[:7]}",
            legal_name="Victim Org LLC",
            public_name="Victim Org",
            region="Tashkent",
            status="VERIFIED",
            created_at=now(),
            updated_at=now(),
        )
    owner_b = identities("OWNER", org_b)

    # Org A creates draft
    with transaction() as conn:
        opp_id = _create_opp(conn, org_id=org_a, author_id=owner_a["user_id"], title="Confidential Strategy Role")

    # Attacker from Org B tries to update Org A's draft
    res_b = client.put(
        f"/api/v1/opportunities/{opp_id}/draft",
        headers=owner_b["headers"],
        json={"title": "Hacked Title"},
    )
    assert res_b.status_code == 404
    assert res_b.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"

    # Attacker tries to update terms
    res_terms = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=owner_b["headers"],
        json={"is_paid": True, "salary_min": 1000},
    )
    assert res_terms.status_code == 404
    assert res_terms.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"

    # Attacker tries to update schedule
    res_sched = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/schedule",
        headers=owner_b["headers"],
        json={"schedule_policy": "STRICT"},
    )
    assert res_sched.status_code == 404
    assert res_sched.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_ac008_published_opportunity_immutable(client: TestClient, identities, organization):
    """AC-008: Published opportunities reject draft modifications with 409 OPPORTUNITY_NOT_DRAFT."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_pub = _create_opp(conn, org_id=org_id, author_id=owner["user_id"], status="PUBLISHED")

    # 1. PUT draft on published
    r1 = client.put(
        f"/api/v1/opportunities/{opp_pub}/draft",
        headers=owner["headers"],
        json={"title": "Modified Title"},
    )
    assert r1.status_code == 409
    assert r1.json()["detail"]["code"] == "OPPORTUNITY_NOT_DRAFT"

    # 2. PUT terms on published
    r2 = client.put(
        f"/api/v1/opportunities/{opp_pub}/draft/terms",
        headers=owner["headers"],
        json={"is_paid": True, "salary_min": 99000},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "OPPORTUNITY_NOT_DRAFT"

    # 3. PUT schedule on published
    r3 = client.put(
        f"/api/v1/opportunities/{opp_pub}/draft/schedule",
        headers=owner["headers"],
        json={"schedule_policy": "NEGOTIABLE"},
    )
    assert r3.status_code == 409
    assert r3.json()["detail"]["code"] == "OPPORTUNITY_NOT_DRAFT"


def test_host_coordinator_role_boundary(client: TestClient, identities, organization):
    """HOST_COORDINATOR can only modify INTERNSHIP opportunities; PART_TIME returns 403."""
    org_id = organization
    host_coord = identities("HOST_COORDINATOR", org_id)

    with transaction() as conn:
        opp_pt = _create_opp(conn, org_id=org_id, author_id=host_coord["user_id"], kind="PART_TIME")
        opp_intern = _create_opp(conn, org_id=org_id, author_id=host_coord["user_id"], kind="INTERNSHIP", is_paid=False)

    # 1. Attempt on PART_TIME -> 403
    res_pt = client.put(
        f"/api/v1/opportunities/{opp_pt}/draft",
        headers=host_coord["headers"],
        json={"title": "Coordinator Title Attempt"},
    )
    assert res_pt.status_code == 403
    assert res_pt.json()["detail"]["code"] == "HOST_COORDINATOR_INTERNSHIP_ONLY"

    # 2. Attempt on INTERNSHIP -> 200
    res_intern = client.put(
        f"/api/v1/opportunities/{opp_intern}/draft",
        headers=host_coord["headers"],
        json={"title": "Valid Academic Internship"},
    )
    assert res_intern.status_code == 200
    assert res_intern.json()["contract_id"] == "API-078"


def test_unpaid_part_time_rejected_422(client: TestClient, identities, organization):
    """Labor Invariant: Setting is_paid=False on a PART_TIME draft is rejected with 422."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_id = _create_opp(conn, org_id=org_id, author_id=owner["user_id"], kind="PART_TIME")

    res = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=owner["headers"],
        json={"is_paid": False},
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "UNPAID_PART_TIME_FORBIDDEN"


def test_shift_overlap_rejection_409(client: TestClient, identities, organization):
    """INV-02: Overlapping shifts within the same group and weekday return 409 OVERLAPPING_OPPORTUNITY_SHIFT."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_id = _create_opp(conn, org_id=org_id, author_id=owner["user_id"])

    # Overlapping shifts: 09:00-12:00 (540-720) and 11:00-14:00 (660-840) on weekday 1
    overlapping_payload = {
        "schedule_policy": "STRICT",
        "shift_match_mode": "ALL",
        "shifts": [
            {"weekday": 1, "start_minute": 540, "end_minute": 720, "group_code": "SHIFT_A"},
            {"weekday": 1, "start_minute": 660, "end_minute": 840, "group_code": "SHIFT_A"},
        ],
    }

    res = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/schedule",
        headers=owner["headers"],
        json=overlapping_payload,
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "OVERLAPPING_OPPORTUNITY_SHIFT"


def test_capacity_boundaries_and_occupied_check(client: TestClient, identities, organization):
    """Capacity validation: capacity <= 0 returns 422; capacity < occupied_count returns 409."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        # capacity=5, occupied=3
        opp_id = _create_opp(conn, org_id=org_id, author_id=owner["user_id"], capacity=5, occupied_count=3)

    # 1. Zero capacity -> 422
    r_zero = client.put(
        f"/api/v1/opportunities/{opp_id}/draft",
        headers=owner["headers"],
        json={"capacity": 0},
    )
    assert r_zero.status_code == 422

    # 2. Capacity less than occupied (2 < 3) -> 409
    r_less = client.put(
        f"/api/v1/opportunities/{opp_id}/draft",
        headers=owner["headers"],
        json={"capacity": 2},
    )
    assert r_less.status_code == 409
    assert r_less.json()["detail"]["code"] == "CAPACITY_LESS_THAN_OCCUPIED"

    # 3. Capacity exactly equal to occupied (3 == 3) -> 200
    r_exact = client.put(
        f"/api/v1/opportunities/{opp_id}/draft",
        headers=owner["headers"],
        json={"capacity": 3},
    )
    assert r_exact.status_code == 200
    assert r_exact.json()["capacity"] == 3


def test_invalid_salary_and_date_ranges_422(client: TestClient, identities, organization):
    """Validation for salary bounds and date ranges: salary_max < salary_min, end_date < start_date."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_id = _create_opp(conn, org_id=org_id, author_id=owner["user_id"], kind="PART_TIME")

    # 1. Negative salary_min -> 422
    r1 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=owner["headers"],
        json={"is_paid": True, "salary_min": -500},
    )
    assert r1.status_code == 422

    # 2. salary_max < salary_min -> 422
    r2 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=owner["headers"],
        json={"is_paid": True, "salary_min": 50000, "salary_max": 30000},
    )
    assert r2.status_code == 422
    assert r2.json()["detail"]["code"] == "INVALID_SALARY_RANGE"

    # 3. end_date < start_date -> 422
    r3 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=owner["headers"],
        json={"is_paid": True, "salary_min": 50000, "start_date": "2026-12-01", "end_date": "2026-11-01"},
    )
    assert r3.status_code == 422
    assert r3.json()["detail"]["code"] == "INVALID_DATE_RANGE"
