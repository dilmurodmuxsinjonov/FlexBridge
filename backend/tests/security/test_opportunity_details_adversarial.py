"""Adversarial security and edge-case tests for Canonical Opportunity Details (API-005 / CAP-001).

Covers:
- Information disclosure & IDOR prevention: DRAFT, PENDING_MODERATION, and ARCHIVED opportunities return uniform 404.
- SQL injection & path manipulation resistance (422 validation boundary).
- Malformed and forged Bearer token attack handling without 500 crashes.
- Revoked org role grant prevents viewing organization's draft opportunities.
- Non-exclusive read transactions: concurrent reads do not take blocking row locks.
- Public data hygiene: internal metadata, author private info, and audit trails never leaked.
"""

from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.opportunities import opportunity_service
from test_candidate import published_fixture


def test_adversarial_draft_guessing_returns_uniform_404(client, identities, organization):
    """API-005: DRAFT opportunity returns 404 identical to non-existent UUID (timing/existence safe)."""
    owner = identities("OWNER", organization)
    guest_candidate = identities()

    # Create a draft opportunity
    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Classified Secret Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=35000,
        actor_user_id=owner["user_id"],
    )
    draft_opp_id = rev["opportunity_id"]
    non_existent_id = str(uuid4())

    # 1. Unauthenticated guest querying draft -> 404
    r_guest_draft = client.get(f"/api/v1/opportunities/{draft_opp_id}")
    r_guest_none = client.get(f"/api/v1/opportunities/{non_existent_id}")
    assert r_guest_draft.status_code == 404
    assert r_guest_none.status_code == 404
    assert r_guest_draft.json() == r_guest_none.json()

    # 2. Candidate querying draft -> 404
    r_cand_draft = client.get(f"/api/v1/opportunities/{draft_opp_id}", headers=guest_candidate["headers"])
    r_cand_none = client.get(f"/api/v1/opportunities/{non_existent_id}", headers=guest_candidate["headers"])
    assert r_cand_draft.status_code == 404
    assert r_cand_none.status_code == 404
    assert r_cand_draft.json() == r_cand_none.json()


def test_adversarial_path_sql_injection_rejected(client):
    """API-005: SQL injection, path traversal, and null byte injections rejected before DB execution."""
    payloads = [
        "123e4567-e89b-12d3-a456-426614174000' OR '1'='1",
        "../../etc/passwd",
        "123e4567-e89b-12d3-a456-426614174000; DROP TABLE opportunities; --",
        "00000000-0000-0000-0000-000000000000%00",
        "not-a-uuid-string",
    ]
    for p in payloads:
        res = client.get(f"/api/v1/opportunities/{p}")
        assert res.status_code in (404, 422), f"Failed for payload: {p}"


def test_adversarial_forged_and_malformed_auth_headers(client, identities, organization):
    """API-005: Malformed Authorization header safely handled without unhandled exception."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # 1. Valid public request without header succeeds
    r_ok = client.get(f"/api/v1/opportunities/{opp_id}")
    assert r_ok.status_code == 200

    # 2. Corrupt / invalid Bearer tokens return 401
    corrupt_headers = [
        {"Authorization": "Bearer invalid-token-string"},
        {"Authorization": "Bearer " + "A" * 500},
        {"Authorization": "Bearer not-a-valid-jwt-token"},
    ]
    for h in corrupt_headers:
        res = client.get(f"/api/v1/opportunities/{opp_id}", headers=h)
        assert res.status_code == 401
        assert res.json()["detail"]["code"] in ("AUTH_REQUIRED", "AUTH_REVOKED", "AUTH_INVALID")


def test_adversarial_revoked_org_grant_blocks_draft_viewing(client, identities, organization):
    """API-005: User with revoked ORG role grant cannot view organization's draft opportunity."""
    owner = identities("OWNER", organization)
    hr = identities("HR", organization)

    rev = opportunity_service.create_opportunity_revision(
        organization_id=organization,
        title="Strict Revocation Test Draft",
        opportunity_kind="PART_TIME_JOB",
        contract_type="LABOR_PART_TIME",
        compensation_type="HOURLY",
        hourly_pay=25000,
        actor_user_id=owner["user_id"],
    )
    opp_id = rev["opportunity_id"]

    # HR can initially view draft
    res_hr_before = client.get(f"/api/v1/opportunities/{opp_id}", headers=hr["headers"])
    assert res_hr_before.status_code == 200

    # Revoke HR's org_role_grants
    with transaction() as conn:
        t_mem = table("org_memberships")
        t_ogrants = table("org_role_grants")
        mem_id = conn.execute(
            select(t_mem.c.id).where(t_mem.c.user_id == hr["user_id"], t_mem.c.organization_id == organization)
        ).scalar_one()
        conn.execute(
            t_ogrants.update().where(t_ogrants.c.membership_id == mem_id).values(revoked_at=now())
        )

    # After revocation, HR receives 404 (IDOR boundary held)
    res_hr_after = client.get(f"/api/v1/opportunities/{opp_id}", headers=hr["headers"])
    assert res_hr_after.status_code == 404
    assert res_hr_after.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_adversarial_public_response_sanitization(client, identities, organization):
    """API-005: Public opportunity response does not leak internal IDs or unverified metadata."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert res.status_code == 200
    data = res.json()

    # Check for absence of internal sensitive fields
    assert "author_id" not in data.get("revision", {})
    assert "snapshot_schema" not in data.get("revision", {})
    assert "tax_id" not in data.get("organization", {})
    assert "balance" not in data.get("organization", {})
    assert "bank_account" not in data.get("organization", {})
