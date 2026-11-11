"""Unit and contract tests for Workplace Reviews & Mentor Review Queue.

Implements and verifies:
- API-090: GET /api/v1/me/mentor-review-queue (CAP-021, CAP-023, LOG_MENTOR)
- API-091: GET /api/v1/log-revisions/{revision}/workplace (CAP-021, CAP-023, LOG_MENTOR)
- API-092: POST /api/v1/log-revisions/{revision}/workplace-reviews (CAP-021, CAP-023, LOG_MENTOR)
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from app.db.institution_scope import TASHKENT
from app.db.storage import now
from tests.security.test_log_evidence_api055 import create_test_file, evidence_setup


def test_api090_mentor_review_queue_empty_and_populated(client, identities, organization):
    """API-090: Mentor review queue lists submitted daily logs for mentor's active assignments."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    draft1 = setup["draft1"]
    pid = setup["pid"]

    # 1. Unrelated mentor has empty queue
    other_mentor = identities()
    resp_empty = client.get("/api/v1/me/mentor-review-queue", headers=other_mentor["headers"])
    assert resp_empty.status_code == 200, resp_empty.text
    data_empty = resp_empty.json()
    assert data_empty["contract_id"] == "API-090"
    assert data_empty["items"] == []
    assert data_empty["total"] == 0

    # 2. Assigned pure mentor sees submitted day 1 log (draft1)
    resp_queue = client.get("/api/v1/me/mentor-review-queue", headers=pure_mentor["headers"])
    assert resp_queue.status_code == 200, resp_queue.text
    data_queue = resp_queue.json()
    assert data_queue["contract_id"] == "API-090"
    assert data_queue["total"] >= 1

    item = next(it for it in data_queue["items"] if it["revision_id"] == draft1["current_revision_id"])
    assert item["placement_id"] == pid
    assert item["status"] == "SUBMITTED"
    assert item["day_type"] == "WORKED"
    assert item["total_minutes"] == 120
    assert item["candidate"]["full_name"] is not None
    assert item["due_at"] is not None
    assert isinstance(item["is_escalated"], bool)

    # 3. Pagination check with limit=1
    resp_paged = client.get("/api/v1/me/mentor-review-queue?limit=1", headers=pure_mentor["headers"])
    assert resp_paged.status_code == 200, resp_paged.text
    data_paged = resp_paged.json()
    assert len(data_paged["items"]) == 1
    assert data_paged["contract_id"] == "API-090"


def test_api091_workplace_log_revision_detail(client, identities, organization):
    """API-091: Workplace view of daily log revision with tasks, candidate, and evidence segregation."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    candidate = setup["f"]["candidate"]
    draft1 = setup["draft1"]
    draft2 = setup["draft2"]
    sub_entry_id = setup["submitted_entry_id"]

    # 1. Attach clean files: one HOST_AND_ACADEMIC, one ACADEMIC_ONLY
    # Note: attachment requires draft status so attach to draft2 entry, but let's test draft1 tasks first
    rev1_id = draft1["current_revision_id"]

    resp = client.get(f"/api/v1/log-revisions/{rev1_id}/workplace", headers=pure_mentor["headers"])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-091"
    assert data["revision_id"] == rev1_id
    assert data["status"] == "SUBMITTED"
    assert data["day_type"] == "WORKED"
    assert data["total_minutes"] == 120
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["title"] == "Setup repository & CI"
    assert data["candidate"]["user_id"] == candidate["user_id"]
    assert data["terms"] is not None
    assert data["existing_review"] is None

    # 2. Attach evidence to draft2, submit it, and verify visibility segregation
    draft2_entry1_id = setup["draft_entry_1_id"]
    f_host = create_test_file(candidate["user_id"], scan_status="CLEAN", filename="code_diff.pdf")
    f_acad = create_test_file(candidate["user_id"], scan_status="CLEAN", filename="transcript.pdf")

    # Attach HOST_AND_ACADEMIC
    r_att1 = client.post(
        f"/api/v1/log-entries/{draft2_entry1_id}/evidence",
        headers=candidate["headers"],
        json={"file_id": f_host, "visibility": "HOST_AND_ACADEMIC"},
    )
    assert r_att1.status_code == 201, r_att1.text

    # Attach ACADEMIC_ONLY
    r_att2 = client.post(
        f"/api/v1/log-entries/{draft2_entry1_id}/evidence",
        headers=candidate["headers"],
        json={"file_id": f_acad, "visibility": "ACADEMIC_ONLY"},
    )
    assert r_att2.status_code == 201, r_att2.text

    # Submit draft2
    r_sub = client.post(f"/api/v1/logs/{draft2['id']}/submit", headers=candidate["headers"], json={})
    assert r_sub.status_code == 200, r_sub.text

    # Inspect draft2 revision via API-091
    rev2_id = draft2["current_revision_id"]
    resp2 = client.get(f"/api/v1/log-revisions/{rev2_id}/workplace", headers=pure_mentor["headers"])
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["contract_id"] == "API-091"

    # Verify evidence: HOST_AND_ACADEMIC is included, ACADEMIC_ONLY is concealed from workplace
    task1 = next(t for t in data2["tasks"] if t["task_id"] == draft2_entry1_id)
    ev_files = [e["file_id"] for e in task1["evidence"]]
    assert f_host in ev_files
    assert f_acad not in ev_files  # ACADEMIC_ONLY concealed from mentor!


def test_api092_workplace_review_flow_approved(client, identities, organization):
    """API-092: Mentor submits APPROVED review decision; verifies status transition and queue departure."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    draft1 = setup["draft1"]
    rev1_id = draft1["current_revision_id"]

    # 1. Submit APPROVED review
    review_payload = {
        "decision": "APPROVED",
        "comment": "Task completed according to corporate engineering standards",
    }
    r_rev = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json=review_payload,
    )
    assert r_rev.status_code == 200, r_rev.text
    res = r_rev.json()
    assert res["contract_id"] == "API-092"
    assert res["revision_id"] == rev1_id
    assert res["decision"] == "APPROVED"
    assert res["comment"] == review_payload["comment"]
    assert res["decided_at"] is not None

    # 2. Inspect revision via API-091: existing_review is present with APPROVED decision
    r_detail = client.get(f"/api/v1/log-revisions/{rev1_id}/workplace", headers=pure_mentor["headers"])
    assert r_detail.status_code == 200, r_detail.text
    detail = r_detail.json()
    assert detail["existing_review"] is not None
    assert detail["existing_review"]["decision"] == "APPROVED"

    # 3. Check queue API-090: approved log is removed from pending review queue
    r_queue = client.get("/api/v1/me/mentor-review-queue", headers=pure_mentor["headers"])
    assert r_queue.status_code == 200, r_queue.text
    queue_revisions = [it["revision_id"] for it in r_queue.json()["items"]]
    assert rev1_id not in queue_revisions

    # 4. Idempotent repeat: submitting exact same decision returns 200
    r_idem = client.post(
        f"/api/v1/log-revisions/{rev1_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json=review_payload,
    )
    assert r_idem.status_code == 200, r_idem.text
    assert r_idem.json()["decision"] == "APPROVED"


def test_api092_workplace_review_changes_requested_and_rejected(client, identities, organization):
    """API-092: Test CHANGES_REQUESTED and REJECTED review decisions."""
    setup = evidence_setup(client, identities, organization)
    pure_mentor = setup["pure_mentor"]
    candidate = setup["f"]["candidate"]
    draft2 = setup["draft2"]

    # Submit draft2
    r_sub = client.post(f"/api/v1/logs/{draft2['id']}/submit", headers=candidate["headers"], json={})
    assert r_sub.status_code == 200, r_sub.text
    rev2_id = draft2["current_revision_id"]

    # Submit CHANGES_REQUESTED
    r_rev = client.post(
        f"/api/v1/log-revisions/{rev2_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json={"decision": "CHANGES_REQUESTED", "comment": "Please add more details to task descriptions"},
    )
    assert r_rev.status_code == 200, r_rev.text
    res = r_rev.json()
    assert res["contract_id"] == "API-092"
    assert res["decision"] == "CHANGES_REQUESTED"

    # Conflicting repeat: trying to change to REJECTED or APPROVED without a new revision returns 409
    r_conflict = client.post(
        f"/api/v1/log-revisions/{rev2_id}/workplace-reviews",
        headers=pure_mentor["headers"],
        json={"decision": "REJECTED", "comment": "Conflicting decision"},
    )
    assert r_conflict.status_code == 409, r_conflict.text
    assert r_conflict.json()["detail"]["code"] == "REVISION_ALREADY_REVIEWED"
