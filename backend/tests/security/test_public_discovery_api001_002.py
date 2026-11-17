"""Unit and contract tests for Public Opportunities Search (API-001) and Onboarding Options (API-002).

Invariants:
- API-001 (GET /api/v1/opportunities):
  * Strictly requires organization status == 'VERIFIED'.
  * Strictly returns status == 'PUBLISHED' and closed_at IS NULL.
  * Filters out expired opportunities (expires_at < now()).
  * Keyset cursor pagination over (published_at DESC, id DESC).
  * Computes real-time vacancies_available = max(0, capacity - occupied_count).
- API-002 (GET /api/v1/onboarding/options):
  * Returns available persona routes.
  * Enforces Stage 2 Freelance Directive: FREELANCER is marked stage 2, is_active=False, status='PLANNED'.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.db.storage import table, transaction, now
from app.services.placements import insert_row


def _create_org(conn, *, legal_name: str, public_name: str, status: str = "VERIFIED", region: str = "Tashkent") -> str:
    t_org = table("organizations")
    org_id = str(uuid.uuid4())
    conn.execute(
        t_org.insert().values(
            id=org_id,
            tax_id=f"99{str(uuid.uuid4().int)[:7]}",
            legal_name=legal_name,
            public_name=public_name,
            region=region,
            status=status,
            created_at=now(),
            updated_at=now(),
        )
    )
    return org_id


def _create_user(conn, *, display_name: str = "Author User") -> str:
    user_id = str(uuid.uuid4())
    conn.execute(
        table("users").insert().values(
            id=user_id,
            display_name=display_name,
            status="ACTIVE",
            password_hash="argon2id$mockedhash",
            locale="uz",
            timezone="Asia/Tashkent",
            created_at=now(),
            updated_at=now(),
        )
    )
    return user_id


def _create_opp(
    conn,
    *,
    org_id: str,
    author_id: str | None = None,
    title: str,
    status: str = "PUBLISHED",
    kind: str = "PART_TIME",
    is_paid: bool = True,
    salary_min: float = 30000.0,
    salary_max: float = 50000.0,
    region: str = "Tashkent",
    capacity: int = 5,
    occupied_count: int = 2,
    closed_at: datetime | None = None,
    expires_at: datetime | None = None,
    published_at: datetime | None = None,
    schedule_policy: str = "FIXED",
) -> tuple[str, str]:
    t_opp = table("opportunities")
    t_rev = table("opportunity_revisions")

    opp_id = str(uuid.uuid4())
    rev_id = str(uuid.uuid4())
    created = now()

    if not author_id:
        author_id = _create_user(conn, display_name=f"Author of {title}")

    conn.execute(
        t_opp.insert().values(
            id=opp_id,
            organization_id=org_id,
            kind=kind,
            status=status,
            capacity=capacity,
            occupied_count=occupied_count,
            created_at=created,
            updated_at=created,
            published_at=published_at or (created if status == "PUBLISHED" else None),
            expires_at=expires_at,
            closed_at=closed_at,
        )
    )

    conn.execute(
        t_rev.insert().values(
            id=rev_id,
            opportunity_id=opp_id,
            revision=1,
            author_id=author_id,
            title=title,
            description=f"Description for {title}",
            region=region,
            work_mode="HYBRID",
            eligibility="ALL",
            contract_type="LABOR_PART_TIME",
            is_paid=is_paid,
            salary_min=salary_min if is_paid else None,
            salary_max=salary_max if is_paid else None,
            currency="UZS",
            salary_basis="GROSS" if is_paid else None,
            salary_period="HOUR" if is_paid else None,
            start_date=created.date(),
            schedule_policy=schedule_policy,
            shift_match_mode="ANY",
            snapshot_schema=1,
            created_at=created,
            updated_at=created,
            published_at=published_at or (created if status == "PUBLISHED" else None),
        )
    )

    conn.execute(
        t_opp.update().where(t_opp.c.id == opp_id).values(current_revision_id=rev_id)
    )
    return opp_id, rev_id


def test_api001_public_search_published_only(client: TestClient):
    with transaction() as conn:
        org_verified = _create_org(conn, legal_name="Apex Corp LLC", public_name="Apex Corp", status="VERIFIED")
        org_pending = _create_org(conn, legal_name="Pending Inc", public_name="Pending Inc", status="PENDING")

        # 1. Published and open -> Should be visible
        opp_pub, _ = _create_opp(conn, org_id=org_verified, title="Python Junior Engineer", status="PUBLISHED")
        # 2. Draft -> Should NOT be visible
        opp_draft, _ = _create_opp(conn, org_id=org_verified, title="Secret Draft Role", status="DRAFT")
        # 3. Closed -> Should NOT be visible
        opp_closed, _ = _create_opp(conn, org_id=org_verified, title="Closed Role", status="CLOSED", closed_at=now())
        # 4. Published on unverified org -> Should NOT be visible
        opp_unver, _ = _create_opp(conn, org_id=org_pending, title="Unverified Org Role", status="PUBLISHED")

    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_id"] == "API-001"
    items = data["items"]
    item_ids = [it["id"] for it in items]

    assert opp_pub in item_ids
    assert opp_draft not in item_ids
    assert opp_closed not in item_ids
    assert opp_unver not in item_ids


def test_api001_filters_region_kind_paid_schedule(client: TestClient):
    with transaction() as conn:
        org_samarkand = _create_org(conn, legal_name="Samarkand Tech", public_name="Samarkand Tech", region="Samarkand")
        org_tashkent = _create_org(conn, legal_name="Tashkent Data", public_name="Tashkent Data", region="Tashkent")

        opp_sam, _ = _create_opp(conn, org_id=org_samarkand, title="Samarkand Tour Guide", region="Samarkand", kind="INTERNSHIP", is_paid=False, schedule_policy="FLEXIBLE")
        opp_tash, _ = _create_opp(conn, org_id=org_tashkent, title="Tashkent Backend Dev", region="Tashkent", kind="PART_TIME", is_paid=True, salary_min=45000, schedule_policy="FIXED")

    # Filter by region
    resp_reg = client.get("/api/v1/opportunities?region=Samarkand")
    assert resp_reg.status_code == 200
    ids_reg = [it["id"] for it in resp_reg.json()["items"]]
    assert opp_sam in ids_reg
    assert opp_tash not in ids_reg

    # Filter by is_paid
    resp_paid = client.get("/api/v1/opportunities?is_paid=true")
    assert resp_paid.status_code == 200
    ids_paid = [it["id"] for it in resp_paid.json()["items"]]
    assert opp_tash in ids_paid
    assert opp_sam not in ids_paid

    # Filter by min_hourly_pay
    resp_pay = client.get("/api/v1/opportunities?min_hourly_pay=40000")
    assert resp_pay.status_code == 200
    ids_pay = [it["id"] for it in resp_pay.json()["items"]]
    assert opp_tash in ids_pay
    assert opp_sam not in ids_pay

    # Filter by schedule_policy
    resp_sch = client.get("/api/v1/opportunities?schedule_policy=FLEXIBLE")
    assert resp_sch.status_code == 200
    ids_sch = [it["id"] for it in resp_sch.json()["items"]]
    assert opp_sam in ids_sch
    assert opp_tash not in ids_sch


def test_api001_keyset_pagination_and_vacancies(client: TestClient):
    with transaction() as conn:
        org = _create_org(conn, legal_name="Scale Org", public_name="Scale Org")
        opp_ids = []
        base_time = now() - timedelta(hours=10)
        for i in range(5):
            pub_time = base_time + timedelta(hours=i)
            opp_id, _ = _create_opp(
                conn,
                org_id=org,
                title=f"Paged Role {i}",
                capacity=10,
                occupied_count=3,
                published_at=pub_time,
            )
            opp_ids.append(opp_id)

    # Fetch page 1 with limit=2
    resp1 = client.get("/api/v1/opportunities?limit=2")
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert len(d1["items"]) == 2
    assert d1["has_more"] is True
    assert d1["next_after"] is not None
    # Vacancies calculation
    assert d1["items"][0]["vacancies_available"] == 7
    assert d1["items"][0]["capacity"] == 10
    assert d1["items"][0]["occupied_count"] == 3

    # Fetch page 2 using cursor
    cursor = d1["next_after"]
    resp2 = client.get(f"/api/v1/opportunities?limit=2&after={cursor}")
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert len(d2["items"]) == 2
    # Disjoint check
    page1_ids = {it["id"] for it in d1["items"]}
    page2_ids = {it["id"] for it in d2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_api001_expired_opportunity_exclusion(client: TestClient):
    with transaction() as conn:
        org = _create_org(conn, legal_name="Time Bound Org", public_name="Time Bound Org")
        expired_time = now() - timedelta(hours=2)
        opp_exp, _ = _create_opp(conn, org_id=org, title="Expired Vacancy", expires_at=expired_time)
        future_time = now() + timedelta(days=5)
        opp_active, _ = _create_opp(conn, org_id=org, title="Active Vacancy", expires_at=future_time)

    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()["items"]]
    assert opp_active in ids
    assert opp_exp not in ids


def test_api002_onboarding_options_structure_and_stage2_isolation(client: TestClient):
    resp = client.get("/api/v1/onboarding/options")
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_id"] == "API-002"
    assert data["version"] == "1.0"
    assert data["active_stage"] == 1
    options = data["options"]

    personas = {opt["persona"]: opt for opt in options}
    # Verify standard personas are active for Stage 1
    for persona in ("CANDIDATE", "STUDENT", "EMPLOYER", "HOST_ORGANIZATION", "INSTITUTION"):
        assert persona in personas
        assert personas[persona]["is_active"] is True
        assert personas[persona]["stage"] == 1
        assert personas[persona]["status"] == "AVAILABLE"
        assert len(personas[persona]["capabilities"]) > 0

    # CRITICAL: Stage 2 Freelance Directive verification
    assert "FREELANCER" in personas
    freelancer = personas["FREELANCER"]
    assert freelancer["is_active"] is False
    assert freelancer["stage"] == 2
    assert freelancer["status"] == "PLANNED"
    assert "2-bosqich" in freelancer["note"]
