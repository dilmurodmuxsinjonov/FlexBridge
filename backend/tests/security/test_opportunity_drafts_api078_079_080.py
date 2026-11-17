"""Contract and functional tests for Opportunity Draft Updates, Terms, and Schedule (API-078, API-079, API-080 / CAP-016).

Specifications:
- API-078: PUT /api/v1/opportunities/{id}/draft
  * Updates title, description, region, work_mode, eligibility, capacity, contract_type.
  * Enforces capacity >= occupied_count and status == 'DRAFT'.
  * Returns contract_id: API-078.
- API-079: PUT /api/v1/opportunities/{id}/draft/terms
  * Validates salary_min/max, currency, salary_period, salary_basis, start_date, end_date.
  * PART_TIME must be paid (unpaid rejected with 422).
  * Returns contract_id: API-079.
- API-080: PUT /api/v1/opportunities/{id}/draft/schedule
  * Configures schedule_policy (STRICT/NEGOTIABLE), shift_match_mode (ALL/ANY).
  * Validates non-overlapping shifts in same group (INV-02).
  * Returns contract_id: API-080.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from uuid import uuid4
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def _create_opp_draft(
    conn,
    *,
    org_id: str,
    author_id: str,
    title: str = "Draft Software Engineer",
    kind: str = "PART_TIME",
    capacity: int = 5,
    occupied_count: int = 0,
    is_paid: bool = True,
    salary_min: float = 35000.0,
    salary_period: str = "HOUR",
) -> tuple[str, str]:
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    created = now()

    insert_row(
        conn,
        "opportunities",
        id=opp_id,
        organization_id=org_id,
        kind=kind,
        status="DRAFT",
        capacity=capacity,
        occupied_count=occupied_count,
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
        title=title,
        description=f"Description of {title}",
        region="Tashkent",
        work_mode="HYBRID",
        eligibility="ALL_CANDIDATES",
        contract_type="LABOR_PART_TIME" if kind == "PART_TIME" else "INTERNSHIP_AGREEMENT",
        currency="UZS",
        is_paid=is_paid,
        salary_min=Decimal(str(salary_min)) if is_paid else None,
        salary_period=salary_period if is_paid else None,
        salary_basis="GROSS" if is_paid else None,
        start_date=created.date(),
        schedule_policy="FIXED",
        shift_match_mode="ALL_SHIFTS_IN_GROUP",
        snapshot_schema=1,
        created_at=created,
        updated_at=created,
    )

    conn.execute(
        table("opportunities").update().where(table("opportunities").c.id == opp_id).values(current_revision_id=rev_id)
    )
    return opp_id, rev_id


def test_api078_update_draft_core_metadata_success(client: TestClient, identities, organization):
    """API-078: Successfully update opportunity draft core parameters with contract stamp."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_id, rev_id = _create_opp_draft(conn, org_id=org_id, author_id=owner["user_id"], kind="PART_TIME", capacity=3)

    payload = {
        "title": "Lead Python Engineer",
        "description": "Senior backend architect for high load pipelines",
        "region": "Samarkand",
        "work_mode": "REMOTE",
        "eligibility": "ALL_CANDIDATES",
        "capacity": 7,
        "contract_type": "LABOR_PART_TIME",
        "program_required": "Computer Science MS",
    }

    res = client.put(f"/api/v1/opportunities/{opp_id}/draft", headers=owner["headers"], json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-078"
    assert data["opportunity_id"] == opp_id
    assert data["revision_id"] == rev_id
    assert data["status"] == "DRAFT"
    assert data["kind"] == "PART_TIME"
    assert data["capacity"] == 7
    assert data["title"] == "Lead Python Engineer"
    assert data["description"] == "Senior backend architect for high load pipelines"
    assert data["region"] == "Samarkand"
    assert data["work_mode"] == "REMOTE"
    assert data["eligibility"] == "ALL_CANDIDATES"
    assert data["program_required"] == "Computer Science MS"


def test_api079_update_draft_terms_part_time_and_internship(client: TestClient, identities, organization):
    """API-079: Update terms with valid salary range for PART_TIME and unpaid for INTERNSHIP."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_pt, _ = _create_opp_draft(conn, org_id=org_id, author_id=owner["user_id"], kind="PART_TIME")
        opp_intern, _ = _create_opp_draft(conn, org_id=org_id, author_id=owner["user_id"], kind="INTERNSHIP", is_paid=False)

    # 1. Update PART_TIME terms with valid salary
    pt_payload = {
        "is_paid": True,
        "salary_min": 45000,
        "salary_max": 75000,
        "currency": "UZS",
        "salary_period": "HOUR",
        "salary_basis": "GROSS",
        "start_date": "2026-12-01",
        "end_date": "2027-06-01",
    }
    res_pt = client.put(f"/api/v1/opportunities/{opp_pt}/draft/terms", headers=owner["headers"], json=pt_payload)
    assert res_pt.status_code == 200, res_pt.text
    data_pt = res_pt.json()
    assert data_pt["contract_id"] == "API-079"
    assert data_pt["is_paid"] is True
    assert data_pt["salary_min"] == 45000.0
    assert data_pt["salary_max"] == 75000.0
    assert data_pt["salary_period"] == "HOUR"
    assert data_pt["salary_basis"] == "GROSS"
    assert data_pt["start_date"] == "2026-12-01"
    assert data_pt["end_date"] == "2027-06-01"

    # 2. Update INTERNSHIP terms to unpaid with educational requirement
    intern_payload = {
        "is_paid": False,
        "start_date": "2026-11-20",
        "end_date": "2027-02-20",
        "program_required": "Software Engineering 3rd year",
    }
    res_intern = client.put(f"/api/v1/opportunities/{opp_intern}/draft/terms", headers=owner["headers"], json=intern_payload)
    assert res_intern.status_code == 200, res_intern.text
    data_intern = res_intern.json()
    assert data_intern["contract_id"] == "API-079"
    assert data_intern["is_paid"] is False
    assert data_intern["salary_min"] is None
    assert data_intern["salary_max"] is None
    assert data_intern["program_required"] == "Software Engineering 3rd year"


def test_api080_update_draft_schedule_success(client: TestClient, identities, organization):
    """API-080: Successfully update schedule matching policy and shift intervals."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        opp_id, rev_id = _create_opp_draft(conn, org_id=org_id, author_id=owner["user_id"])

    schedule_payload = {
        "schedule_policy": "NEGOTIABLE",
        "shift_match_mode": "ANY",
        "shifts": [
            {
                "weekday": 1,
                "start_minute": 540,   # 09:00
                "end_minute": 780,     # 13:00
                "group_code": "MORNING",
                "timezone": "Asia/Tashkent",
            },
            {
                "weekday": 3,
                "start_minute": 840,   # 14:00
                "end_minute": 1080,    # 18:00
                "group_code": "AFTERNOON",
                "timezone": "Asia/Tashkent",
            },
            {
                "weekday": 5,
                "start_minute": 540,
                "end_minute": 780,
                "group_code": "MORNING",
                "timezone": "Asia/Tashkent",
            },
        ],
    }

    res = client.put(f"/api/v1/opportunities/{opp_id}/draft/schedule", headers=owner["headers"], json=schedule_payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-080"
    assert data["opportunity_id"] == opp_id
    assert data["revision_id"] == rev_id
    assert data["schedule_policy"] == "NEGOTIABLE"
    assert data["shift_match_mode"] == "ANY"
    assert data["shifts_count"] == 3
    assert len(data["shifts"]) == 3

    # Check shift sorting by weekday
    assert data["shifts"][0]["weekday"] == 1
    assert data["shifts"][0]["start_minute"] == 540
    assert data["shifts"][1]["weekday"] == 3
    assert data["shifts"][2]["weekday"] == 5


def test_opportunity_draft_sequential_lifecycle(client: TestClient, identities, organization):
    """Verifies that API-078 -> API-079 -> API-080 chain executes cleanly on a single draft."""
    org_id = organization
    hr_user = identities("HR", org_id)

    with transaction() as conn:
        opp_id, _ = _create_opp_draft(conn, org_id=org_id, author_id=hr_user["user_id"])

    # Step 1: Draft metadata
    r1 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft",
        headers=hr_user["headers"],
        json={"title": "Data Analyst", "capacity": 4, "work_mode": "HYBRID"},
    )
    assert r1.status_code == 200
    assert r1.json()["title"] == "Data Analyst"
    assert r1.json()["capacity"] == 4

    # Step 2: Terms
    r2 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/terms",
        headers=hr_user["headers"],
        json={"is_paid": True, "salary_min": 40000, "salary_period": "HOUR", "salary_basis": "GROSS"},
    )
    assert r2.status_code == 200
    assert r2.json()["salary_min"] == 40000.0

    # Step 3: Schedule
    r3 = client.put(
        f"/api/v1/opportunities/{opp_id}/draft/schedule",
        headers=hr_user["headers"],
        json={
            "schedule_policy": "STRICT",
            "shift_match_mode": "ALL",
            "shifts": [{"weekday": 2, "start_minute": 600, "end_minute": 900, "group_code": "GROUP_A"}],
        },
    )
    assert r3.status_code == 200
    assert r3.json()["shifts_count"] == 1
