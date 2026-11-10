"""Security and contract tests for Task Entry Evidence Attachment (API-055 / DB-058 / CAP-022 / PG-022.S03).

Verifies:
1. Candidate author attaches clean file evidence to draft task entry (201 Created).
2. Candidate author lists evidence for task entry with file details.
3. Visibility enforcement (HOST_AND_ACADEMIC, HOST_ONLY, ACADEMIC_ONLY).
4. Rejections:
   - 422: Invalid visibility enum value
   - 409: Duplicate evidence attachment (entry_id, file_id)
   - 422: File in PENDING_SCAN status
   - 422: File in QUARANTINED status
   - 422: Deleted file (deleted_at is not None)
   - 403: File owned by another user
   - 404: Nonexistent file UUID
   - 404: Nonexistent task entry UUID
   - 409: Attaching evidence to SUBMITTED immutable daily log
   - 403: Non-author actors (host owner, mentor, teacher, foreign candidate)
   - 401: Unauthenticated request
5. Stakeholder visibility segregation on submitted log:
   - Candidate views all evidence
   - Host/mentor views HOST_AND_ACADEMIC and HOST_ONLY, excluded from ACADEMIC_ONLY
   - Teacher/coordinator views HOST_AND_ACADEMIC and ACADEMIC_ONLY, excluded from HOST_ONLY
6. Candidate draft confidentiality: non-candidate query for draft task evidence returns empty list
7. End-to-end synergy: API-053 placement logs reflects evidence_count correctly
8. 130 tables migration schema regression
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_academic_admission import nominate, pending_http, plan
from test_academic_lifecycle import teacher_accept
from test_academic_reviews import body as review_body, send as review_send
from test_admission_lifecycle import terms_request
from test_internship_admission import post


def create_test_file(user_id: str, scan_status: str = "CLEAN", filename: str = "proof.pdf", deleted: bool = False) -> str:
    """Create a database-backed file with specified scan_status and storage provenance."""
    version = str(uuid4())
    etag = '"' + uuid4().hex + '"'
    now_ts = now()
    with transaction() as conn:
        f = insert_row(
            conn,
            "files",
            owner_user_id=user_id,
            filename=filename,
            mime_type="application/pdf",
            storage_key=("quarantine/" if scan_status == "SCANNING" else "private/test/") + str(uuid4()),
            byte_size=1024,
            sha256="a" * 64 if scan_status == "CLEAN" else None,
            scan_status=scan_status,
            retention_class="VERIFICATION_EVIDENCE",
            deleted_at=now_ts if deleted else None,
            object_version=version if scan_status == "CLEAN" else (etag if scan_status == "SCANNING" else None),
            storage_bucket="test-private-bucket" if scan_status in ("CLEAN", "SCANNING") else None,
            storage_version_id=version if scan_status in ("CLEAN", "SCANNING") else None,
            storage_etag=etag if scan_status in ("CLEAN", "SCANNING") else None,
            scanned_at=now_ts if scan_status == "CLEAN" else None,
        )
    return str(f["id"])


def evidence_setup(client, identities, organization):
    """Set up a placement with 5 distinct actors, 1 submitted log (day 1), and 1 draft log (day 2)."""
    start = now().astimezone(TASHKENT).date() - timedelta(days=3)
    f = pending_http(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=0,
    )
    pid = f["placement"]["id"]
    base = f"/api/v1/placements/{pid}"

    # 1. Setup pure mentor (distinct from f['owner'])
    pure_mentor = identities()
    with transaction() as conn:
        m_mem = insert_row(conn, "org_memberships", organization_id=organization, user_id=pure_mentor["user_id"], status="ACTIVE")
        roles = table("role_catalog")
        rid = conn.execute(select(roles.c.id).where(roles.c.code == "MENTOR", roles.c.scope_kind == "ORG")).scalar_one()
        insert_row(conn, "org_role_grants", membership_id=m_mem["id"], role_id=rid, granted_by_id=f["owner"]["user_id"])

    # 2. Academic nomination
    academic_assignment = nominate(client, f)
    p = plan(client, f)

    # 3. Candidate accepts
    post(client, base + "/accept", f["candidate"], terms_request(p), 200)

    # 4. Pure mentor nominated and accepted
    nom = post(client, base + "/mentor-assignments", f["owner"], dict(mentor_id=pure_mentor["user_id"], idempotency_key=str(uuid4())), 201)
    post(client, f"{base}/assignments/{nom['id']}/accept", pure_mentor, terms_request(p), 200)
    pure_mentor["assignment_id"] = nom["id"]

    # 5. Teacher accepts
    _, _, t_resp = teacher_accept(client, f, academic_assignment, p)
    assert t_resp.status_code == 200, t_resp.text

    # 6. Host activates
    post(client, base + "/host-decisions", f["owner"], {**terms_request(p), "action": "ACTIVATE"}, 200)

    # 7. Day 1 log submitted with a task entry
    r1 = client.put(
        base + "/logs/" + p["start_date"],
        headers=f["candidate"]["headers"],
        json={
            "day_type": "WORKED",
            "summary_text": "Day 1 tasks completed",
            "total_minutes": 120,
            "tasks": [{"title": "Setup repository & CI", "minutes": 120, "start_minute": 0, "end_minute": 120}],
        },
    )
    assert r1.status_code == 200, r1.text
    draft1 = r1.json()
    post(client, "/api/v1/logs/" + draft1["id"] + "/submit", f["candidate"], {}, 200)

    # 8. Day 2 draft log created with 2 task entries
    day2 = (start + timedelta(days=1)).isoformat()
    r2 = client.put(
        base + "/logs/" + day2,
        headers=f["candidate"]["headers"],
        json={
            "day_type": "WORKED",
            "summary_text": "Day 2 in progress",
            "total_minutes": 240,
            "tasks": [
                {"title": "Implement feature A", "minutes": 120, "start_minute": 0, "end_minute": 120},
                {"title": "Write automated tests", "minutes": 120, "start_minute": 120, "end_minute": 240},
            ],
        },
    )
    assert r2.status_code == 200, r2.text
    draft2 = r2.json()

    # Query task entry IDs from database
    with transaction() as conn:
        t_te = table("log_task_entries")
        submitted_entries = conn.execute(
            select(t_te).where(t_te.c.revision_id == draft1["current_revision_id"]).order_by(t_te.c.id)
        ).mappings().all()
        draft_entries = conn.execute(
            select(t_te).where(t_te.c.revision_id == draft2["current_revision_id"]).order_by(t_te.c.id)
        ).mappings().all()

    return {
        "f": f,
        "pid": pid,
        "pure_mentor": pure_mentor,
        "academic_assignment": academic_assignment,
        "draft1": draft1,
        "draft2": draft2,
        "submitted_entry_id": str(submitted_entries[0]["id"]),
        "draft_entry_1_id": str(draft_entries[0]["id"]),
        "draft_entry_2_id": str(draft_entries[1]["id"]),
    }


def test_candidate_can_attach_clean_evidence_to_draft_task_entry(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"], scan_status="CLEAN", filename="feature_a_proof.pdf")

    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id, "visibility": "HOST_AND_ACADEMIC"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-055"
    assert data["entry_id"] == entry_id
    assert data["file_id"] == file_id
    assert data["visibility"] == "HOST_AND_ACADEMIC"
    assert "id" in data
    assert "created_at" in data

    # Verify listing endpoint returns attached evidence
    list_resp = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"])
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()
    assert list_data["total"] == 1
    item = list_data["items"][0]
    assert item["id"] == data["id"]
    assert item["filename"] == "feature_a_proof.pdf"
    assert item["scan_status"] == "CLEAN"
    assert item["byte_size"] == 1024


def test_visibility_options_supported(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    f1 = create_test_file(cand["user_id"], filename="host_only.pdf")
    f2 = create_test_file(cand["user_id"], filename="academic_only.pdf")

    r1 = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": f1, "visibility": "HOST_ONLY"},
    )
    assert r1.status_code == 201
    assert r1.json()["visibility"] == "HOST_ONLY"

    r2 = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": f2, "visibility": "ACADEMIC_ONLY"},
    )
    assert r2.status_code == 201
    assert r2.json()["visibility"] == "ACADEMIC_ONLY"


def test_invalid_visibility_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"])
    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id, "visibility": "INVALID_SCOPE"},
    )
    assert resp.status_code == 422
    assert "INVALID_EVIDENCE_VISIBILITY" in resp.text


def test_duplicate_evidence_attachment_rejected_409(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"])
    r1 = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert r2.status_code == 409
    assert "EVIDENCE_ALREADY_ATTACHED" in r2.text


def test_pending_scan_file_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"], scan_status="PENDING_SCAN")
    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 422
    assert "FILE_NOT_CLEAN_FOR_EVIDENCE" in resp.text


def test_quarantined_file_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"], scan_status="QUARANTINED")
    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 422
    assert "FILE_NOT_CLEAN_FOR_EVIDENCE" in resp.text


def test_deleted_file_rejected_422(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    file_id = create_test_file(cand["user_id"], scan_status="CLEAN", deleted=True)
    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 422
    assert "FILE_DELETED" in resp.text


def test_file_owned_by_another_user_rejected_403(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    stranger = identities()
    foreign_file = create_test_file(stranger["user_id"], scan_status="CLEAN")

    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": foreign_file},
    )
    assert resp.status_code == 403
    assert "FILE_ACCESS_DENIED" in resp.text


def test_nonexistent_file_rejected_404(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    entry_id = ctx["draft_entry_1_id"]

    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        headers=cand["headers"],
        json={"file_id": str(uuid4())},
    )
    assert resp.status_code == 404
    assert "FILE_NOT_FOUND" in resp.text


def test_nonexistent_task_entry_rejected_404(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]

    file_id = create_test_file(cand["user_id"])
    resp = client.post(
        f"/api/v1/log-entries/{uuid4()}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 404
    assert "TASK_ENTRY_NOT_FOUND" in resp.text


def test_submitted_log_task_entry_is_immutable_409(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    submitted_entry = ctx["submitted_entry_id"]

    file_id = create_test_file(cand["user_id"])
    resp = client.post(
        f"/api/v1/log-entries/{submitted_entry}/evidence",
        headers=cand["headers"],
        json={"file_id": file_id},
    )
    assert resp.status_code == 409
    assert "SUBMITTED_LOG_IMMUTABLE" in resp.text


def test_non_author_actors_rejected_403(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    entry_id = ctx["draft_entry_1_id"]

    host_owner = ctx["f"]["owner"]
    mentor = ctx["pure_mentor"]
    teacher = ctx["f"]["teacher"]
    stranger = identities()

    for actor in [host_owner, mentor, teacher, stranger]:
        file_id = create_test_file(actor["user_id"])
        resp = client.post(
            f"/api/v1/log-entries/{entry_id}/evidence",
            headers=actor["headers"],
            json={"file_id": file_id},
        )
        assert resp.status_code == 403, f"Actor {actor['user_id']} was not forbidden: {resp.status_code}"


def test_unauthenticated_request_rejected_401(client, identities, organization):
    ctx = evidence_setup(client, identities, organization)
    entry_id = ctx["draft_entry_1_id"]

    resp = client.post(
        f"/api/v1/log-entries/{entry_id}/evidence",
        json={"file_id": str(uuid4())},
    )
    assert resp.status_code in (401, 403)


def test_stakeholder_visibility_segregation(client, identities, organization):
    """Verify that on a submitted log:
    - Host/Mentor only sees HOST_AND_ACADEMIC and HOST_ONLY (not ACADEMIC_ONLY).
    - Teacher/Coordinator only sees HOST_AND_ACADEMIC and ACADEMIC_ONLY (not HOST_ONLY).
    - Candidate sees all.
    """
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    host = ctx["f"]["owner"]
    mentor = ctx["pure_mentor"]
    teacher = ctx["f"]["teacher"]
    entry_id = ctx["draft_entry_1_id"]
    draft2_id = ctx["draft2"]["id"]

    f_shared = create_test_file(cand["user_id"], filename="shared_evidence.pdf")
    f_host = create_test_file(cand["user_id"], filename="host_confidential.pdf")
    f_acad = create_test_file(cand["user_id"], filename="academic_confidential.pdf")

    # Attach all 3 types to draft entry
    assert client.post(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"], json={"file_id": f_shared, "visibility": "HOST_AND_ACADEMIC"}).status_code == 201
    assert client.post(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"], json={"file_id": f_host, "visibility": "HOST_ONLY"}).status_code == 201
    assert client.post(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"], json={"file_id": f_acad, "visibility": "ACADEMIC_ONLY"}).status_code == 201

    # While still in DRAFT, mentor or teacher querying evidence gets empty list (draft confidentiality)
    assert client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=mentor["headers"]).json()["total"] == 0
    assert client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=teacher["headers"]).json()["total"] == 0

    # Submit day 2 log
    sub_resp = post(client, f"/api/v1/logs/{draft2_id}/submit", cand, {}, 200)

    # 1. Candidate views all 3 items
    cand_items = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"]).json()["items"]
    assert len(cand_items) == 3

    # 2. Host owner views shared + host_only (2 items, academic excluded)
    host_items = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=host["headers"]).json()["items"]
    assert len(host_items) == 2
    assert {i["visibility"] for i in host_items} == {"HOST_AND_ACADEMIC", "HOST_ONLY"}

    # 3. Mentor views shared + host_only (2 items, academic excluded)
    mentor_items = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=mentor["headers"]).json()["items"]
    assert len(mentor_items) == 2
    assert {i["visibility"] for i in mentor_items} == {"HOST_AND_ACADEMIC", "HOST_ONLY"}

    # 4. Teacher views shared + academic_only (2 items, host excluded)
    teacher_items = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=teacher["headers"]).json()["items"]
    assert len(teacher_items) == 2
    assert {i["visibility"] for i in teacher_items} == {"HOST_AND_ACADEMIC", "ACADEMIC_ONLY"}

    # 5. Verify historical PRIVATE_HOST_EVIDENCE is hidden from teacher (Copilot CLI review finding)
    f_priv = create_test_file(cand["user_id"], filename="private_host.pdf")
    with transaction() as conn:
        insert_row(conn, "log_evidence", entry_id=entry_id, file_id=f_priv, visibility="PRIVATE_HOST_EVIDENCE")

    teacher_items_updated = client.get(f"/api/v1/log-entries/{entry_id}/evidence", headers=teacher["headers"]).json()["items"]
    assert len(teacher_items_updated) == 2
    assert f_priv not in [i["file_id"] for i in teacher_items_updated]


def test_api053_reflects_evidence_count(client, identities, organization):
    """Verify that attaching evidence updates evidence_count in API-053 placement diary logs view."""
    ctx = evidence_setup(client, identities, organization)
    cand = ctx["f"]["candidate"]
    pid = ctx["pid"]
    entry_id = ctx["draft_entry_2_id"]

    f1 = create_test_file(cand["user_id"])
    client.post(f"/api/v1/log-entries/{entry_id}/evidence", headers=cand["headers"], json={"file_id": f1})

    # Query API-053
    resp = client.get(f"/api/v1/placements/{pid}/logs?include_tasks=true", headers=cand["headers"])
    assert resp.status_code == 200
    logs = resp.json()["items"]

    # Locate day 2 draft log and task 2
    day2_log = next(l for l in logs if l.get("current_revision", {}).get("status") == "DRAFT")
    tasks = day2_log["current_revision"]["tasks"]
    task2 = next(t for t in tasks if t["id"] == entry_id)
    assert task2["evidence_count"] == 1


def test_migration_schema_integrity():
    """Verify 130 tables migration schema baseline remains intact (DB-058 log_evidence)."""
    with transaction() as conn:
        tables_res = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'flexbridge'")).scalar_one()
        assert tables_res == 130
        col_res = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'flexbridge' AND table_name = 'log_evidence' ORDER BY ordinal_position"
        )).fetchall()
        col_names = [r[0] for r in col_res]
        assert col_names == ["id", "created_at", "updated_at", "entry_id", "file_id", "visibility"]
