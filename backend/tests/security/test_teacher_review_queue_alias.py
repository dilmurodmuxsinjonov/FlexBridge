"""Verification test for teacher review queue alias (GET /api/v1/me/teacher-review-queue).

Validates parity between canonical API-105 path (/me/academic-review-queue)
and teacher-facing alias (/me/teacher-review-queue).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from test_academic_admission import pending_http
from test_academic_views import active_revision, get
from test_internship_admission import post


def test_teacher_review_queue_alias_parity_and_scoping(client, identities, organization):
    """Verify /me/teacher-review-queue works identically to /me/academic-review-queue."""
    f = pending_http(client, identities, organization)

    # 1. Unauthenticated gets 401
    r_unauth = client.get("/api/v1/me/teacher-review-queue")
    assert r_unauth.status_code == 401, r_unauth.text

    # 2. Before submission: empty queue for teacher
    empty_canon = get(client, "me/academic-review-queue", f["teacher"])
    empty_alias = get(client, "me/teacher-review-queue", f["teacher"])
    assert empty_alias == empty_canon
    assert empty_alias["items"] == []

    # 3. Create active revision and submit log
    a, draft = active_revision(client, f)
    post(client, f"/api/v1/logs/{draft['id']}/submit", f["candidate"], {}, 200)

    # 4. Teacher and Coordinator see submitted log in queue via both endpoints
    canon_teacher = get(client, "me/academic-review-queue", f["teacher"])
    alias_teacher = get(client, "me/teacher-review-queue", f["teacher"])
    assert alias_teacher == canon_teacher
    assert len(alias_teacher["items"]) == 1
    assert alias_teacher["items"][0]["id"] == draft["current_revision_id"]
    assert alias_teacher["items"][0]["daily_log_id"] == draft["id"]

    # Candidate has empty queue
    assert get(client, "me/teacher-review-queue", f["candidate"])["items"] == []

    # 5. Revoking assignment removes log from teacher's queue
    post(client, f"/api/v1/academic-assignments/{a['id']}/revoke", f["coord"], {"idempotency_key": str(uuid4())}, 200)
    assert get(client, "me/teacher-review-queue", f["teacher"])["items"] == []
