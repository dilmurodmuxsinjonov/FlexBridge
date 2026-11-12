"""Adversarial and boundary verification for API-007: POST /api/v1/moderation-cases (CAP-034 / DB-078)."""

from uuid import uuid4

import pytest


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
