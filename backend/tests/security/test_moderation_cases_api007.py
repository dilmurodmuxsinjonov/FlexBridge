"""Functional and contract verification for API-007: POST /api/v1/moderation-cases (CAP-032 / DB-078)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import table, transaction, now
from test_academic_admission import pending_http


def test_api007_report_opportunity_success(client, identities, organization):
    owner = identities("OWNER", organization)
    reporter = identities("CANDIDATE")

    # Create an opportunity to report
    opp_id = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table("opportunities").insert().values(
                id=opp_id,
                organization_id=organization,
                status="PUBLISHED",
                kind="INTERNSHIP",
                capacity=2,
                occupied_count=0,
                created_at=now(),
                updated_at=now(),
                published_at=now(),
            )
        )

    payload = {
        "opportunity_id": opp_id,
        "category": "SCAM",
        "reason": "This opportunity asks for payment upfront which violates platform terms.",
        "severity": "HIGH",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 201, r.text
    data = r.json()

    assert data["contract_id"] == "API-007"
    assert data["reporter_id"] == reporter["user_id"]
    assert data["target_type"] == "OPPORTUNITY"
    assert data["target_id"] == opp_id
    assert data["opportunity_id"] == opp_id
    assert data["organization_id"] is None
    assert data["rating_id"] is None
    assert data["file_id"] is None
    assert data["category"] == "SCAM"
    assert data["severity"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["is_idempotent_replay"] is False

    # Check due_at is approximately 48 hours in future for HIGH severity
    due_at = datetime.fromisoformat(data["due_at"])
    created_at = datetime.fromisoformat(data["created_at"])
    diff_hours = (due_at - created_at).total_seconds() / 3600
    assert 47.9 <= diff_hours <= 48.1

    # Verify database persistence
    with transaction() as conn:
        t_cases = table("moderation_cases")
        case = conn.execute(select(t_cases).where(t_cases.c.id == data["id"])).mappings().one()
        assert str(case["reporter_id"]) == reporter["user_id"]
        assert str(case["opportunity_id"]) == opp_id
        assert case["category"] == "SCAM"
        assert case["severity"] == "HIGH"
        assert case["status"] == "OPEN"


def test_api007_report_organization_success(client, identities, organization):
    reporter = identities("STUDENT")

    payload = {
        "organization_id": organization,
        "category": "POLICY_VIOLATION",
        "reason": "The organization does not provide safe working conditions.",
        "severity": "CRITICAL",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 201, r.text
    data = r.json()

    assert data["contract_id"] == "API-007"
    assert data["target_type"] == "ORGANIZATION"
    assert data["target_id"] == organization
    assert data["organization_id"] == organization
    assert data["severity"] == "CRITICAL"
    assert data["status"] == "OPEN"

    # CRITICAL SLA is 24 hours
    due_at = datetime.fromisoformat(data["due_at"])
    created_at = datetime.fromisoformat(data["created_at"])
    diff_hours = (due_at - created_at).total_seconds() / 3600
    assert 23.9 <= diff_hours <= 24.1


def test_api007_report_rating_success(client, identities, organization):
    reporter = identities("OWNER", organization)
    candidate = identities("CANDIDATE")

    # Create completed placement and active rubric for rating submission
    f = pending_http(client, identities, organization)
    placement_id = f["placement"]["id"]
    rubric_id = str(uuid4())
    rating_id = str(uuid4())

    with transaction() as conn:
        conn.execute(
            table("rubric_versions").insert().values(
                id=rubric_id,
                family="GENERAL_INTERNSHIP",
                version=1,
                status="ACTIVE",
                scale_min=1,
                scale_max=5,
                published_at=now(),
            )
        )
        conn.execute(
            table("rating_submissions").insert().values(
                id=rating_id,
                created_at=now(),
                updated_at=now(),
                placement_id=placement_id,
                engagement_id=None,
                rubric_id=rubric_id,
                rater_id=candidate["user_id"],
                target_user_id=None,
                target_org_id=organization,
                version=1,
                status="PUBLISHED",
                comment="Valid comment",
                submitted_at=now(),
                publish_after=now(),
            )
        )

    payload = {
        "rating_id": rating_id,
        "category": "DEFAMATION",
        "reason": "This rating contains offensive language and defamatory false claims.",
        "severity": "MEDIUM",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 201, r.text
    data = r.json()

    assert data["contract_id"] == "API-007"
    assert data["target_type"] == "RATING"
    assert data["target_id"] == rating_id
    assert data["rating_id"] == rating_id
    assert data["severity"] == "MEDIUM"

    # MEDIUM SLA is 72 hours
    due_at = datetime.fromisoformat(data["due_at"])
    created_at = datetime.fromisoformat(data["created_at"])
    diff_hours = (due_at - created_at).total_seconds() / 3600
    assert 71.9 <= diff_hours <= 72.1


def test_api007_report_file_success(client, identities, organization):
    reporter = identities("HR", organization)

    # Insert a file to report
    file_id = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table("files").insert().values(
                id=file_id,
                created_at=now(),
                updated_at=now(),
                owner_user_id=reporter["user_id"],
                storage_key=f"private/test/{file_id}",
                filename="test_evidence.pdf",
                byte_size=1024,
                mime_type="application/pdf",
                scan_status="PENDING_SCAN",
                retention_class="INTERNSHIP_REPORT",
                sha256="0" * 64,
            )
        )

    payload = {
        "file_id": file_id,
        "category": "MALICIOUS_CONTENT",
        "reason": "The uploaded document contains malicious links and phishing material.",
        "severity": "LOW",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 201, r.text
    data = r.json()

    assert data["contract_id"] == "API-007"
    assert data["target_type"] == "FILE"
    assert data["target_id"] == file_id
    assert data["file_id"] == file_id
    assert data["severity"] == "LOW"

    # LOW SLA is 168 hours (7 days)
    due_at = datetime.fromisoformat(data["due_at"])
    created_at = datetime.fromisoformat(data["created_at"])
    diff_hours = (due_at - created_at).total_seconds() / 3600
    assert 167.9 <= diff_hours <= 168.1


def test_api007_idempotent_replay(client, identities, organization):
    reporter = identities("HR", organization)

    payload = {
        "organization_id": organization,
        "category": "COMMUNICATION_ISSUE",
        "reason": "Repeated non-responsiveness regarding internship agreements.",
        "severity": "MEDIUM",
    }
    r1 = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r1.status_code == 201, r1.text
    case1 = r1.json()
    assert case1["is_idempotent_replay"] is False

    # Second submission identical
    r2 = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r2.status_code == 201, r2.text
    case2 = r2.json()

    assert case2["id"] == case1["id"]
    assert case2["is_idempotent_replay"] is True


def test_api007_audit_trail_recorded(client, identities, organization):
    reporter = identities("OWNER", organization)

    payload = {
        "organization_id": organization,
        "category": "DISCRIMINATION",
        "reason": "Clear evidence of discriminatory internship selection requirements.",
        "severity": "HIGH",
    }
    r = client.post("/api/v1/moderation-cases", json=payload, headers=reporter["headers"])
    assert r.status_code == 201, r.text
    case_id = r.json()["id"]

    # Verify audit event in audit_events table
    with transaction() as conn:
        t_audit = table("audit_events")
        audit = conn.execute(
            select(t_audit).where(
                t_audit.c.object_type == "moderation_case",
                t_audit.c.object_key == case_id,
                t_audit.c.action == "MODERATION_CASE_REPORTED",
            )
        ).mappings().first()

        assert audit is not None
        assert str(audit["actor_id"]) == reporter["user_id"]
        assert audit["scope_snapshot"]["category"] == "DISCRIMINATION"
        assert audit["scope_snapshot"]["severity"] == "HIGH"
        assert audit["scope_snapshot"]["target_type"] == "ORGANIZATION"
        assert audit["scope_snapshot"]["target_id"] == organization
