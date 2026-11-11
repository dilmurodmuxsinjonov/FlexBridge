"""Functional tests for Canonical Opportunity Details (API-005 / CAP-001 / DB-035, DB-036, DB-037, DB-038, DB-021, DB-013)."""

from uuid import uuid4
from datetime import timedelta
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.opportunities import opportunity_service, OpportunityConstraintError
from app.services.schedule import local_today
from test_candidate import published_fixture


def test_public_guest_get_published_opportunity_success(client, identities, organization):
    """API-005 / CAP-001: Unauthenticated guests can view published opportunity details."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-005"
    assert data["id"] == opp_id
    assert data["organization_id"] == organization
    assert data["status"] == "PUBLISHED"
    assert data["capacity"] >= 1
    assert data["vacancies_available"] >= 1

    # Revision details
    revision = data["revision"]
    assert revision is not None
    assert revision["id"] == rev["id"]
    assert revision["title"] == "Candidate matching test"
    assert revision["work_mode"] == "ONSITE"
    assert revision["is_paid"] is True
    assert revision["salary_min"] == 20000.0

    # Organization details
    org = data["organization"]
    assert org is not None
    assert org["id"] == organization
    assert org["legal_name"] is not None
    assert org["public_name"] is not None

    # Shifts
    shifts = data["shifts"]
    assert isinstance(shifts, list)
    assert len(shifts) >= 1
    assert shifts[0]["group_code"] == "A"


def test_authenticated_candidate_get_published_opportunity_success(client, identities, organization):
    """API-005: Authenticated candidates can inspect published opportunity details."""
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}", headers=candidate["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-005"
    assert data["id"] == opp_id
    assert data["status"] == "PUBLISHED"
    assert data["revision"]["contract_type"] == "LABOR_PART_TIME"


def test_opportunity_with_skills_and_shifts(client, identities, organization):
    """API-005: Opportunity with linked skills (DB-037/DB-013) and shifts (DB-038) returns structured payload."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Link a skill in opportunity_skills
    with transaction() as conn:
        t_skills = table("skills")
        skill_row = conn.execute(select(t_skills)).mappings().first()
        if not skill_row:
            skill_id = str(uuid4())
            conn.execute(
                t_skills.insert().values(
                    id=skill_id,
                    code="PYTHON_DEV",
                    name_uz="Python dasturchi",
                    name_ru="Разработчик Python",
                    aliases=[],
                    active=True,
                )
            )
        else:
            skill_id = skill_row["id"]

        t_opp_skills = table("opportunity_skills")
        conn.execute(
            t_opp_skills.insert().values(
                id=str(uuid4()),
                revision_id=rev["id"],
                skill_id=skill_id,
                required=True,
                minimum_level="INTERMEDIATE",
            )
        )

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()

    skills = data["skills"]
    assert len(skills) >= 1
    matched = [s for s in skills if s["id"] == skill_id]
    assert len(matched) == 1
    assert matched[0]["required"] is True
    assert matched[0]["minimum_level"] == "INTERMEDIATE"


def test_get_closed_opportunity_public_visibility(client, identities, organization):
    """API-005: Closed opportunity is visible to public with status CLOSED and 0 vacancies."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(status="CLOSED", closed_at=now(), occupied_count=1, capacity=1)
        )

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "CLOSED"
    assert data["vacancies_available"] == 0
    assert data["closed_at"] is not None


def test_get_nonexistent_opportunity_404(client):
    """API-005: Non-existent opportunity returns 404 OPPORTUNITY_NOT_FOUND."""
    fake_id = str(uuid4())
    res = client.get(f"/api/v1/opportunities/{fake_id}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_get_opportunity_invalid_uuid_422(client):
    """API-005: Non-UUID identifier in path returns 422 Unprocessable Entity."""
    res = client.get("/api/v1/opportunities/not-a-valid-uuid")
    assert res.status_code == 422


def test_draft_opportunity_hidden_from_guest(client, identities, organization):
    """API-005: DRAFT opportunity returns 404 to unauthenticated guests (isolation)."""
    owner = identities("OWNER", organization)
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Secret Draft Opp",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=25000,
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_draft_opportunity_hidden_from_candidate(client, identities, organization):
    """API-005: DRAFT opportunity returns 404 to candidates."""
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Secret Candidate Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=25000,
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}", headers=candidate["headers"])
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_draft_opportunity_hidden_from_other_organization(client, identities, organization):
    """API-005: DRAFT opportunity returns 404 to another organization's owner."""
    owner_a = identities("OWNER", organization)
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Org A Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=25000,
        actor_user_id=owner_a["user_id"],
    )
    opp_id = rev["opportunity_id"]

    # Organization B
    with transaction() as conn:
        t_org = table("organizations")
        org_b_id = str(uuid4())
        conn.execute(
            t_org.insert().values(
                id=org_b_id,
                tax_id="999888777",
                legal_name="Other Org LLC",
                public_name="Other Org",
                region="Toshkent",
                status="ACTIVE",
            )
        )
    owner_b = identities("OWNER", org_b_id)

    res = client.get(f"/api/v1/opportunities/{opp_id}", headers=owner_b["headers"])
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_draft_opportunity_accessible_to_owning_org_owner_and_hr(client, identities, organization):
    """API-005: DRAFT opportunity is visible to owning organization's OWNER and HR."""
    owner = identities("OWNER", organization)
    hr = identities("HR", organization)
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Org Owned Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=30000,
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    # Owning OWNER
    res_owner = client.get(f"/api/v1/opportunities/{opp_id}", headers=owner["headers"])
    assert res_owner.status_code == 200, res_owner.text
    assert res_owner.json()["status"] == "DRAFT"
    assert res_owner.json()["revision"]["title"] == "Org Owned Draft"

    # Owning HR
    res_hr = client.get(f"/api/v1/opportunities/{opp_id}", headers=hr["headers"])
    assert res_hr.status_code == 200, res_hr.text
    assert res_hr.json()["status"] == "DRAFT"


def test_draft_opportunity_accessible_to_platform_moderator_and_admin(client, identities, organization):
    """API-005: Platform MODERATOR and ADMIN can inspect DRAFT opportunities for moderation review."""
    owner = identities("OWNER", organization)
    moderator = identities("MODERATOR")
    admin = identities("ADMIN")

    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Moderation Review Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=35000,
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    # Moderator
    res_mod = client.get(f"/api/v1/opportunities/{opp_id}", headers=moderator["headers"])
    assert res_mod.status_code == 200, res_mod.text
    assert res_mod.json()["status"] == "DRAFT"

    # Admin
    res_admin = client.get(f"/api/v1/opportunities/{opp_id}", headers=admin["headers"])
    assert res_admin.status_code == 200, res_admin.text
    assert res_admin.json()["status"] == "DRAFT"


def test_unpaid_academic_opportunity_details(client, identities, organization):
    """API-005: UNPAID_ACADEMIC opportunity details correctly format non-salary fields."""
    owner = identities("OWNER", organization)
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="University Academic Internship",
        opportunity_kind="ACADEMIC_INTERNSHIP",
        contract_type="UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT",
        compensation_type="UNPAID_ACADEMIC",
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    # Publish
    with transaction() as conn:
        conn.execute(
            table("opportunities").update().where(table("opportunities").c.id == opp_id).values(status="PUBLISHED")
        )

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["revision"]["is_paid"] is False
    assert data["revision"]["salary_min"] is None
    assert data["revision"]["salary_period"] is None
    assert data["revision"]["contract_type"] == "ACADEMIC_TRIPARTITE"


def test_closed_opportunity_with_unfilled_capacity_reports_zero_vacancies(client, identities, organization):
    """API-005: Opportunity closed with leftover capacity (capacity=5, occupied=1) strictly reports vacancies_available=0."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(status="CLOSED", closed_at=now(), capacity=5, occupied_count=1)
        )

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "CLOSED"
    assert data["capacity"] == 5
    assert data["occupied_count"] == 1
    assert data["vacancies_available"] == 0


def test_expired_opportunity_reports_zero_vacancies(client, identities, organization):
    """API-005: Published opportunity whose expires_at is in the past reports vacancies_available=0."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    past_date = now() - timedelta(days=2)
    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(status="PUBLISHED", expires_at=past_date, capacity=5, occupied_count=1)
        )

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "PUBLISHED"
    assert data["vacancies_available"] == 0


def test_direct_invalid_uuid_call_raises_404():
    """API-005: Calling get_opportunity_detail directly with non-UUID string defensively raises 404."""
    with pytest.raises(OpportunityConstraintError) as exc_info:
        opportunity_service.get_opportunity_detail("not-a-valid-uuid-at-all")
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "OPPORTUNITY_NOT_FOUND"
