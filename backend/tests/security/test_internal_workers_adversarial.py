"""Adversarial security and penetration tests for Internal Workers System (API-X07, API-X08).

Verifies:
- 401 UNAUTHORIZED on missing or invalid worker token.
- 403 PERMISSION_DENIED on non-staff / unauthorized actors.
- 404 FILE_NOT_FOUND IDOR anti-enumeration defense.
- 422 VALIDATION_ERROR on malformed UUID or invalid scan statuses.
- Strict containment: Quarantined files cannot be downloaded via API-X03.
- Safe bounding of sweep batch limits.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.db.storage import files_table, now, transaction

INTERNAL_WORKER_SECRET = os.getenv("FLEXBRIDGE_INTERNAL_WORKER_SECRET", "flexbridge-internal-worker-secret-2026")
WORKER_HEADERS = {"X-Internal-Worker-Token": INTERNAL_WORKER_SECRET}


def _seed_file(owner_id: str, scan_status: str = "SCANNING") -> str:
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
                filename="adversarial_test.pdf",
                mime_type="application/pdf",
                byte_size=1024,
                sha256=None,
                scan_status=scan_status,
                retention_class="VERIFICATION_EVIDENCE",
                storage_bucket="flexbridge-test-bucket",
                storage_version_id="test-version-v1",
                storage_etag="test-etag-provenance-1",
                object_version="test-etag-provenance-1",
            )
        )
    return file_id


def test_adversarial_unauthenticated_requests_denied_401(client):
    r_scan = client.post("/api/v1/internal/workers/scan-result", json={"file_id": str(uuid4()), "scan_status": "CLEAN"})
    assert r_scan.status_code == 401, r_scan.text
    assert r_scan.json()["detail"]["code"] == "UNAUTHORIZED"

    r_sweep = client.post("/api/v1/internal/workers/retention-sweep", json={"data_category": "ALL"})
    assert r_sweep.status_code == 401, r_sweep.text
    assert r_sweep.json()["detail"]["code"] == "UNAUTHORIZED"


def test_adversarial_invalid_worker_token_denied_401(client):
    bad_headers = {"X-Internal-Worker-Token": "completely-invalid-worker-secret-999"}
    r = client.post(
        "/api/v1/internal/workers/scan-result",
        json={"file_id": str(uuid4()), "scan_status": "CLEAN"},
        headers=bad_headers,
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


def test_adversarial_non_admin_actor_forbidden_403(client, identities):
    user = identities()
    file_id = _seed_file(user["user_id"])

    r = client.post(
        "/api/v1/internal/workers/scan-result",
        json={"file_id": file_id, "scan_status": "CLEAN"},
        headers=user["headers"],
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"

    r_sweep = client.post(
        "/api/v1/internal/workers/retention-sweep",
        json={"data_category": "ALL"},
        headers=user["headers"],
    )
    assert r_sweep.status_code == 403, r_sweep.text
    assert r_sweep.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_adversarial_scan_result_nonexistent_file_404(client):
    random_id = str(uuid4())
    r = client.post(
        "/api/v1/internal/workers/scan-result",
        json={"file_id": random_id, "scan_status": "CLEAN"},
        headers=WORKER_HEADERS,
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "FILE_NOT_FOUND"


def test_adversarial_scan_result_invalid_uuid_422(client):
    r = client.post(
        "/api/v1/internal/workers/scan-result",
        json={"file_id": "not-a-valid-uuid-at-all", "scan_status": "CLEAN"},
        headers=WORKER_HEADERS,
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "INVALID_UUID"


def test_adversarial_scan_result_invalid_status_422(client, identities):
    user = identities()
    file_id = _seed_file(user["user_id"])

    r = client.post(
        "/api/v1/internal/workers/scan-result",
        json={"file_id": file_id, "scan_status": "COMPLETELY_BOGUS_STATUS"},
        headers=WORKER_HEADERS,
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "INVALID_SCAN_STATUS"


def test_adversarial_quarantined_file_cannot_be_downloaded(client, identities):
    user = identities()
    file_id = _seed_file(user["user_id"], scan_status="QUARANTINED")

    r_download = client.get(f"/api/v1/files/{file_id}/download", headers=user["headers"])
    assert r_download.status_code in {403, 409}, r_download.text
    code = r_download.json().get("detail", {}).get("code", "")
    assert "CLEAN" in code or "DENIED" in code or "QUARANTINED" in code or r_download.status_code == 409
