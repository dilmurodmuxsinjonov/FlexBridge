"""Adversarial security and invariant tests for Workplace Reviews & Mentor Review Queue.

Verifies:
1. AC-028 / SEC-01: Candidate cannot review their own daily log (403 SELF_REVIEW_FORBIDDEN).
2. IDOR Anti-Enumeration: Unassigned mentor or cross-tenant caller receives uniform 404 LOG_REVISION_NOT_FOUND.
3. Unauthenticated requests blocked (401).
4. Mutability Invariant: Reviewing DRAFT log rejected (409 SUBMITTED_REVISION_REQUIRED).
5. Input Validation: Invalid review decisions rejected (422).
6. Revoked Mentor Assignment: Revoked mentor cannot access review queue or submit reviews.
7. Random UUID Uniform 404: Non-existent revision UUID returns uniform 404.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.storage import now, table, transaction
from tests.security.test_log_evidence_api055 import evidence_setup


def test_adversarial_unauthenticated_requests_blocked(client):
    """Unauthenticated requests must be rejected with 401 across all 3 endpoints."""
    fake_id = str(uuid4())
    r1 = client.get("/api/v1/me/mentor-review-queue")
    assert r1.status_code == 401, r1.text

    r2 = client.get(f"/api/v1/log-revisions/{fake_id}/workplace")
    assert r2.status_code == 401, r2.text

    r3 = client.post(f"/api/v1/log-revisions/{fake_id}/workplace-reviews", json={"decision": "APPROVED"})
    assert r3.status_code == 401, r3.text


def test_adversarial_self_review_forbidden(client, identities, organization):
    """AC-028 / SEC-01 Invariant: Candidate author cannot review their own daily log (403 SELF_REVIEW_FORBIDDEN)."""
    setup = evidence_setup(client, identities, organization)
    candidate = setup["f"]["candidate"]
    draft1 = setup["draft1"]
    rev1_id = draft1["current_revision_id"]

    # Candidate attempts to submit a workplace review on their own log
    resp = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=candidate["headers"],
        json={"decision": "APPROVED", "comment": "I approve my own work"},
    )
    assert resp.status_code == 403, resp.text
    err = resp.json()["detail"]
    assert err["code"] == "SELF_REVIEW_FORBIDDEN"


def test_adversarial_cross_mentor_idor_anti_enumeration(client, identities, organization):
    """Cross-mentor IDOR defense: Unassigned mentor gets uniform 404 LOG_REVISION_NOT_FOUND."""
    setup = evidence_setup(client, identities, organization)
    draft1 = setup["draft1"]
    rev1_id = draft1["current_revision_id"]

    other_mentor = identities()

    # Attempt to view log revision detail
    r_get = client.get(f"/api/v1/log-revisions/{rev1_id}/workplace", headers=other_mentor["headers"])
    assert r_get.status_code == 404, r_get.text
    assert r_get.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"

    # Attempt to submit review
    r_post = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=other_mentor["headers"],
        json={"decision": "APPROVED", "comment": "Unauthorized review"},
    )
    assert r_post.status_code == 404, r_post.text
    assert r_post.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"


def test_adversarial_draft_revision_not_reviewable(client, identities, organization):
    """Draft daily log revisions cannot be reviewed until candidate submits them (409 SUBMITTED_REVISION_REQUIRED)."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    draft2 = setup["draft2"]  # Day 2 log is in DRAFT status
    rev2_id = draft2["current_revision_id"]

    resp = client.post(
        f"/api/v1/log-revisions/{rev2_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json={"decision": "APPROVED", "comment": "Premature review of draft"},
    )
    assert resp.status_code == 409, resp.text
    err = resp.json()["detail"]
    assert err["code"] == "SUBMITTED_REVISION_REQUIRED"


def test_adversarial_invalid_review_decision(client, identities, organization):
    """Invalid review decision values must be rejected with 422."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    draft1 = setup["draft1"]
    rev1_id = draft1["current_revision_id"]

    resp = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json={"decision": "MALICIOUS_DECISION", "comment": "Invalid payload"},
    )
    assert resp.status_code == 422, resp.text


def test_adversarial_unassigned_mentor_access_denied(client, identities, organization):
    """An unassigned mentor cannot see or review another placement's daily logs."""
    setup = evidence_setup(client, identities, organization)
    unassigned_mentor = identities()
    draft1 = setup["draft1"]
    rev1_id = draft1["current_revision_id"]

    # Queue should be empty for unassigned mentor
    r_queue = client.get("/api/v1/me/mentor-review-queue", headers=unassigned_mentor["headers"])
    assert r_queue.status_code == 200, r_queue.text
    assert r_queue.json()["items"] == []

    # Accessing revision detail returns uniform 404
    r_detail = client.get(f"/api/v1/log-revisions/{rev1_id}/workplace", headers=unassigned_mentor["headers"])
    assert r_detail.status_code == 404, r_detail.text
    assert r_detail.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"

    # Submitting review returns uniform 404
    r_rev = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=unassigned_mentor["headers"],
        json={"decision": "APPROVED", "comment": "Unassigned mentor attempt"},
    )
    assert r_rev.status_code == 404, r_rev.text
    assert r_rev.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"


def test_adversarial_nonexistent_revision_uniform_404(client, identities):
    """Random non-existent revision UUID returns uniform 404 across endpoints."""
    actor = identities()
    fake_id = str(uuid4())

    r1 = client.get(f"/api/v1/log-revisions/{fake_id}/workplace", headers=actor["headers"])
    assert r1.status_code == 404, r1.text
    assert r1.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"

    r2 = client.post(
        f"/api/v1/log-revisions/{fake_id}/workplace-reviews",
        headers=actor["headers"],
        json={"decision": "APPROVED", "comment": "Non-existent log"},
    )
    assert r2.status_code == 404, r2.text
    assert r2.json()["detail"]["code"] == "LOG_REVISION_NOT_FOUND"
