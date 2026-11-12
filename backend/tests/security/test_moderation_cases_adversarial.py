"""Adversarial and boundary verification for API-007: POST /api/v1/moderation-cases (CAP-032 / DB-078)."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction


def test_adversarial_unauthenticated_rejected(client):
    payload = {
        "opportunity_id": str(uuid4()),
        "category": "SCAM",
        "reason": "Unauthenticated report attempt must be rejected.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload)
    assert r.status_code == 401, r.text


def test_adversarial_zero_targets_rejected(client, identities):
    reporter = identities("CANDIDATE")
    payload = {
        "category": "SCAM",
        "reason": "Missing any target entity must be rejected with 422.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "EXACTLY_ONE_TARGET_REQUIRED"


def test_adversarial_multiple_targets_rejected(client, identities, organization):
    reporter = identities("CANDIDATE")
    payload = {
        "opportunity_id": str(uuid4()),
        "organization_id": organization,
        "category": "SCAM",
        "reason": "Providing multiple targets must be rejected with 422.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "EXACTLY_ONE_TARGET_REQUIRED"


def test_adversarial_nonexistent_opportunity_rejected_404(client, identities):
    reporter = identities("CANDIDATE")
    fake_opp = str(uuid4())
    payload = {
        "opportunity_id": fake_opp,
        "category": "SCAM",
        "reason": "Nonexistent opportunity target must return 404.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_adversarial_nonexistent_organization_rejected_404(client, identities):
    reporter = identities("CANDIDATE")
    fake_org = str(uuid4())
    payload = {
        "organization_id": fake_org,
        "category": "SCAM",
        "reason": "Nonexistent organization target must return 404.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_nonexistent_rating_rejected_404(client, identities):
    reporter = identities("CANDIDATE")
    fake_rating = str(uuid4())
    payload = {
        "rating_id": fake_rating,
        "category": "DEFAMATION",
        "reason": "Nonexistent rating target must return 404.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "RATING_NOT_FOUND"


def test_adversarial_nonexistent_file_rejected_404(client, identities):
    reporter = identities("CANDIDATE")
    fake_file = str(uuid4())
    payload = {
        "file_id": fake_file,
        "category": "MALICIOUS_CONTENT",
        "reason": "Nonexistent file target must return 404.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "FILE_NOT_FOUND"


def test_adversarial_invalid_uuid_rejected_422(client, identities):
    reporter = identities("CANDIDATE")
    payload = {
        "opportunity_id": "not-a-valid-uuid",
        "category": "SCAM",
        "reason": "Malformed UUID string must be rejected by Pydantic validation.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text


def test_adversarial_short_reason_rejected_422(client, identities, organization):
    reporter = identities("CANDIDATE")
    payload = {
        "organization_id": organization,
        "category": "SCAM",
        "reason": "Too short",  # < 10 chars
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text


def test_adversarial_invalid_severity_rejected_422(client, identities, organization):
    reporter = identities("CANDIDATE")
    payload = {
        "organization_id": organization,
        "category": "SCAM",
        "reason": "Valid reason explanation that has enough characters.",
        "severity": "SUPER_EXTREME",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text


def test_adversarial_extra_fields_forbidden_422(client, identities, organization):
    reporter = identities("CANDIDATE")
    payload = {
        "organization_id": organization,
        "category": "SCAM",
        "reason": "Valid reason explanation that has enough characters.",
        "unexpected_field": "injected_value",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text


def test_adversarial_soft_deleted_file_rejected_404(client, identities, organization):
    reporter = identities("HR", organization)
    file_id = str(uuid4())

    with transaction() as conn:
        conn.execute(
            table("files").insert().values(
                id=file_id,
                created_at=now(),
                updated_at=now(),
                owner_user_id=reporter["user_id"],
                storage_key=f"private/test/{file_id}",
                filename="deleted_doc.pdf",
                byte_size=2048,
                mime_type="application/pdf",
                scan_status="PENDING_SCAN",
                retention_class="INTERNSHIP_REPORT",
                sha256="1" * 64,
                deleted_at=now(),  # Soft-deleted
            )
        )

    payload = {
        "file_id": file_id,
        "category": "MALICIOUS_CONTENT",
        "reason": "Reporting a soft-deleted file must be rejected as nonexistent.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "FILE_NOT_FOUND"


def test_adversarial_case_insensitive_category_dedup(client, identities, organization):
    reporter = identities("STUDENT")

    payload1 = {
        "organization_id": organization,
        "category": "scam",  # lowercase
        "reason": "Reporting organization for scam activities in lowercase.",
    }
    r1 = client.post("/api/v1/moderation-cases", json=payload1, headers=reporter["headers"])
    assert r1.status_code == 201, r1.text
    case1 = r1.json()
    assert case1["category"] == "SCAM"
    assert case1["is_idempotent_replay"] is False

    # Second submission with different casing ("SCAM" vs "scam") must deduplicate
    payload2 = {
        "organization_id": organization,
        "category": "SCAM",  # uppercase
        "reason": "Reporting same organization for SCAM activities in uppercase.",
    }
    r2 = client.post("/api/v1/moderation-cases", json=payload2, headers=reporter["headers"])
    assert r2.status_code == 201, r2.text
    case2 = r2.json()
    assert case2["id"] == case1["id"]
    assert case2["is_idempotent_replay"] is True


def test_adversarial_invalid_category_pattern_rejected_422(client, identities, organization):
    reporter = identities("CANDIDATE")
    payload = {
        "organization_id": organization,
        "category": "SCAM\nINJECTION",
        "reason": "Category with newlines or control characters must be rejected.",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 422, r.text


def test_adversarial_concurrent_reports_idempotent_single_case(client, identities, organization):
    reporter = identities("CANDIDATE")
    opp_id = str(uuid4())

    with transaction() as conn:
        conn.execute(
            table("opportunities").insert().values(
                id=opp_id,
                organization_id=organization,
                status="PUBLISHED",
                kind="INTERNSHIP",
                capacity=1,
                occupied_count=0,
                created_at=now(),
                updated_at=now(),
                published_at=now(),
            )
        )

    payload = {
        "opportunity_id": opp_id,
        "category": "SCAM",
        "reason": "Concurrent race condition testing for duplicate moderation cases.",
    }

    def submit_report(_: int):
        return client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit_report, range(2)))

    assert all(r.status_code == 201 for r in results), [r.text for r in results]
    ids = [r.json()["id"] for r in results]
    replays = [r.json()["is_idempotent_replay"] for r in results]

    # Exactly one case in database
    assert ids[0] == ids[1]
    # One was original creation, one was idempotent replay
    assert set(replays) == {True, False}

    # Verify only 1 row exists in DB
    with transaction() as conn:
        t_cases = table("moderation_cases")
        cases = conn.execute(
            select(t_cases.c.id).where(
                t_cases.c.reporter_id == reporter["user_id"],
                t_cases.c.opportunity_id == opp_id,
            )
        ).scalars().all()
        assert len(cases) == 1

