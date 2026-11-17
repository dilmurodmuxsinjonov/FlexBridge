"""Unit and contract tests for Internal Workers System (API-X07, API-X08).

Contracts:
- API-X07: POST /api/v1/internal/workers/scan-result (CAP-039 / OPERATIONS / DB-073)
- API-X08: POST /api/v1/internal/workers/retention-sweep (CAP-040 / OPERATIONS / DB-083)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import files_table, now, table, transaction

INTERNAL_WORKER_SECRET = os.getenv("FLEXBRIDGE_INTERNAL_WORKER_SECRET", "flexbridge-internal-worker-secret-2026")
WORKER_HEADERS = {"X-Internal-Worker-Token": INTERNAL_WORKER_SECRET}


def _seed_test_file(
    owner_id: str,
    scan_status: str = "SCANNING",
    retention_class: str = "VERIFICATION_EVIDENCE",
) -> str:
    file_id = str(uuid4())
    now_utc = now()
    with transaction() as conn:
        conn.execute(
            files_table.insert().values(
                id=file_id,
                created_at=now_utc,
                updated_at=now_utc,
                owner_user_id=owner_id,
                storage_key=f"quarantine/{file_id}.pdf",
                filename="document.pdf",
                mime_type="application/pdf",
                byte_size=2048,
                sha256=None,
                scan_status=scan_status,
                retention_class=retention_class,
                storage_bucket="flexbridge-test-bucket",
                storage_version_id="test-version-v1",
                storage_etag="test-etag-provenance-1",
                object_version="test-etag-provenance-1",
            )
        )
    return file_id


def test_api_x07_scan_result_clean_updates_file(client, identities):
    user = identities()
    file_id = _seed_test_file(user["user_id"], scan_status="SCANNING")
    sha_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    resp = client.post(
        "/api/v1/internal/workers/scan-result",
        json={
            "file_id": file_id,
            "scan_status": "CLEAN",
            "sha256": sha_val,
            "scanner_name": "clamav",
            "scanner_version": "1.4.0",
        },
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-X07"
    assert data["capability"] == "OPERATIONS"
    assert data["file_id"] == file_id
    assert data["scan_status"] == "CLEAN"
    assert data["quarantined"] is False
    assert data["sha256"] == sha_val

    # Verify database state
    with transaction() as conn:
        row = conn.execute(
            select(files_table.c.scan_status, files_table.c.sha256).where(files_table.c.id == file_id)
        ).mappings().one()
        assert row["scan_status"] == "CLEAN"
        assert row["sha256"] == sha_val


def test_api_x07_scan_result_infected_quarantines_file(client, identities):
    user = identities()
    file_id = _seed_test_file(user["user_id"], scan_status="SCANNING")

    resp = client.post(
        "/api/v1/internal/workers/scan-result",
        json={
            "file_id": file_id,
            "scan_status": "INFECTED",
            "virus_name": "Eicar-Signature-Trojan",
            "scanner_name": "clamav",
        },
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-X07"
    assert data["file_id"] == file_id
    assert data["scan_status"] == "QUARANTINED"
    assert data["quarantined"] is True

    # Verify database state
    with transaction() as conn:
        row = conn.execute(
            select(files_table.c.scan_status, files_table.c.scan_error).where(files_table.c.id == file_id)
        ).mappings().one()
        assert row["scan_status"] == "QUARANTINED"
        assert row["scan_error"] == "Eicar-Signature-Trojan"


def test_api_x07_scan_result_failed_records_error(client, identities):
    user = identities()
    file_id = _seed_test_file(user["user_id"], scan_status="SCANNING")

    resp = client.post(
        "/api/v1/internal/workers/scan-result",
        json={
            "file_id": file_id,
            "scan_status": "SCAN_FAILED",
            "error_message": "Engine timeout after 30s",
        },
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-X07"
    assert data["scan_status"] == "ERROR"
    assert data["quarantined"] is False


def test_api_x07_admin_actor_can_submit_scan_result(client, identities):
    admin = identities("ADMIN")
    user = identities()
    file_id = _seed_test_file(user["user_id"], scan_status="SCANNING")

    resp = client.post(
        "/api/v1/internal/workers/scan-result",
        json={
            "file_id": file_id,
            "scan_status": "CLEAN",
            "sha256": "b" * 64,
        },
        headers=admin["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["contract_id"] == "API-X07"
    assert resp.json()["scan_status"] == "CLEAN"


def test_api_x08_retention_sweep_dry_run(client, identities):
    user = identities()
    now_utc = now()
    old_time = now_utc - timedelta(days=60)

    with transaction() as conn:
        t_sess = table("sessions")
        conn.execute(
            t_sess.insert().values(
                id=str(uuid4()),
                user_id=user["user_id"],
                token_digest="expired_token_hash_for_test",
                device_key_digest="device_digest_test",
                assurance="PASSWORD",
                created_at=old_time,
                updated_at=old_time,
                expires_at=old_time,
                revoked_at=old_time,
                last_seen_at=old_time,
                auth_version=1,
            )
        )

    resp = client.post(
        "/api/v1/internal/workers/retention-sweep",
        json={
            "data_category": "ALL",
            "dry_run": True,
            "limit": 100,
        },
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-X08"
    assert data["capability"] == "OPERATIONS"
    assert data["dry_run"] is True
    assert data["status"] == "COMPLETED"
    assert data["purged_sessions_count"] >= 1


def test_api_x08_retention_sweep_execution(client, identities):
    resp = client.post(
        "/api/v1/internal/workers/retention-sweep",
        json={
            "data_category": "ALL",
            "dry_run": False,
            "limit": 500,
        },
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_id"] == "API-X08"
    assert data["dry_run"] is False
    assert data["status"] == "COMPLETED"
    assert "total_records_actioned" in data
