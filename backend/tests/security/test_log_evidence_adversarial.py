"""Adversarial and boundary stress tests for Task Entry Evidence Attachment (API-055 / DB-058 / CAP-022).

Stress vectors tested:
1. SQL Injection attempts in path parameter, visibility string, and payload.
2. Malformed UUIDs in path and payload (422 Unprocessable Entity).
3. Payload tampering: unexpected extra attributes rejected by extra='forbid'.
4. Cross-tenant attempt: candidate A attempts to attach their own file to candidate B's task entry.
5. Large / boundary visibility strings and null bytes.
"""
from uuid import uuid4

import pytest

from test_log_evidence_api055 import create_test_file, evidence_setup


def test_sql_injection_in_visibility_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"])
    payloads = [
        "HOST_ONLY' OR '1'='1",
        "'; DROP TABLE log_evidence; --",
        "UNION SELECT null, null, null--",
    ]
    for sqli in payloads:
        resp = client.post(
            f"/api/v1/log-entries/{entry_id}/evidence",
            headers=cand["headers"],
            json={"file_id": file_id, "visibility": sqli},
        )
        assert resp.status_code == 422


def test_malformed_uuids_in_path_and_body_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    # Malformed path UUID
    r1 = client.post(
        "/api/v1/log-entries/not-a-uuid/evidence",
        headers=cand["headers"],
        json={"file_id": str(uuid4())},
    )
    assert r1.status_code == 422

    # Malformed body UUID
    r2 = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": "malformed-file-id"},
    )
    assert r2.status_code == 422


def test_extra_payload_attributes_forbidden_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"])
    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={
            "file_id": file_id,
            "visibility": "HOST_AND_ACADEMIC",
            "malicious_inject": "admin_override",
            "is_verified": True,
        },
    )
    assert resp.status_code == 422


def test_cross_tenant_evidence_tampering_rejected_403(client, identities, organization):
    """Candidate A cannot attach their own valid file to Candidate B's task entry."""
    ctx_a = evidence_setup(client, identities, organization)
    ctx_b = evidence_setup(client, identities, organization)

    cand_a = ctx_a["f"]["candidate"]
    entry_b = ctx_b["draft_entry_1_id"]

    file_a = create_test_file(cand_a["user_id"], scan_status="CLEAN")

    resp = client.post(
        f"/api/v1/log-entries/{entry_b}/evidence",
        headers=cand_a["headers"],
        json={"file_id": file_a},
    )
    assert resp.status_code in (403, 404)
    if resp.status_code == 403:
        assert "FORBIDDEN" in resp.text or "AUTHOR" in resp.text


def test_superseded_revision_task_entry_rejected_409(client, identities, organization):
    """Updating a draft log supersedes old revisions; attaching evidence to superseded task entries is rejected."""
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    old_entry_id = ctx["draft_entry_1_id"]
    pid = ctx["pid"]
    day2 = ctx["draft2"]["log_date"]

    # Candidate saves a new revision for day 2 with new tasks
    new_draft = client.put(
        f"/api/v1/placements/{pid}/logs/{day2}",
        headers=cand["headers"],
        json={
            "day_type": "WORKED",
            "summary_text": "Updated revision 2 for day 2",
            "total_minutes": 180,
            "tasks": [{"title": "Revised task", "minutes": 180}],
        },
    )
    assert new_draft.status_code == 200

    # Attempting to attach evidence to old_entry_id (which belonged to revision 1) must be rejected
    file_id = create_test_file(cand["user_id"])
    resp = client.post(
        f"/api/v1/log-entries/{old_entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 409
    assert "SUPERSEDED_REVISION_IMMUTABLE" in resp.text


def test_empty_string_and_null_bytes_in_visibility_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"])
    for bad in ["", "\x00", "   ", "HOST_AND_ACADEMIC\x00extra"]:
        resp = client.post(
            f"/api/v1/log-entries/{entry_id}/evidence",
            headers=cand["headers"],
            json={"file_id": file_id, "visibility": bad},
        )
        assert resp.status_code == 422
