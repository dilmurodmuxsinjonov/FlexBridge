"""Functional and contract tests for Institution Summary Report Exports (API-100 / CAP-018 / CAP-026 / REPORT_EXPORT).

Contract:
- API-100: POST /api/v1/institutions/{inst}/exports
"""
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.storage import files_table, table, transaction
from app.services.institution_exports import EXPORT_DISCLAIMER
from test_academic_admission import pending_http, plan, post
from test_academic_authority import academic_fixture
from test_academic_lifecycle import teacher_accept
from test_academic_views import active_revision
from test_admission_lifecycle import terms_request


def test_api100_institution_export_json_success(client, identities, organization):
    """API-100: Coordinator can generate JSON summary report export with accurate metrics."""
    f = academic_fixture(identities, organization)
    coord = f["coord"]
    inst_id = f["inst"]["id"]

    idempotency_key = f"inst-export-json-{uuid4()}"
    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={
            "format": "JSON",
            "idempotency_key": idempotency_key,
            "include_details": True,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-100"
    assert data["capability"] == "REPORT_EXPORT"
    assert data["institution_id"] == inst_id
    assert data["export_format"] == "JSON"
    assert data["actor_role"] == "COORDINATOR"
    assert data["file_id"] is not None
    assert data["download_url"] is not None
    assert data["is_idempotent_replay"] is False
    assert EXPORT_DISCLAIMER in data["disclaimer"]

    summary = data["summary"]
    assert summary["institution_id"] == inst_id
    assert summary["institution_name"] == f["inst"]["name"]
    assert summary["total_students_enrolled"] >= 1
    assert summary["total_active_agreements"] >= 1
    assert summary["total_placements"] >= 1
    assert "total_submitted_logs" in summary
    assert "total_logged_hours" in summary
    assert isinstance(summary["placements"], list)
    assert len(summary["placements"]) >= 1

    # Verify file persistence in DB
    with transaction() as conn:
        f_row = conn.execute(
            select(files_table).where(files_table.c.id == data["file_id"])
        ).mappings().first()
        assert f_row is not None
        assert f_row["owner_user_id"] == coord["user_id"]
        assert f_row["mime_type"] == "application/json"
        assert f_row["retention_class"] == "PRIVATE_EXPORT_FILE"
        assert f_row["scan_status"] == "CLEAN"


def test_api100_institution_export_pdf_success(client, identities, organization):
    """API-100: Coordinator can generate PDF summary report export."""
    f = academic_fixture(identities, organization)
    coord = f["coord"]
    inst_id = f["inst"]["id"]

    idempotency_key = f"inst-export-pdf-{uuid4()}"
    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={
            "format": "PDF",
            "idempotency_key": idempotency_key,
            "include_details": True,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-100"
    assert data["export_format"] == "PDF"
    assert data["is_idempotent_replay"] is False
    assert data["file_id"] is not None

    with transaction() as conn:
        f_row = conn.execute(
            select(files_table).where(files_table.c.id == data["file_id"])
        ).mappings().first()
        assert f_row is not None
        assert f_row["mime_type"] == "application/pdf"
        assert f_row["storage_key"].endswith(".pdf")


def test_api100_idempotency_replay_and_conflict(client, identities, organization):
    """Exact repeat returns cached receipt (is_idempotent_replay: true); altered payload returns 409."""
    f = academic_fixture(identities, organization)
    coord = f["coord"]
    inst_id = f["inst"]["id"]

    idempotency_key = f"inst-replay-{uuid4()}"
    res1 = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "JSON", "idempotency_key": idempotency_key},
    )
    assert res1.status_code == 201, res1.text
    data1 = res1.json()
    assert data1["is_idempotent_replay"] is False

    # Second call with same idempotency key
    res2 = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "JSON", "idempotency_key": idempotency_key},
    )
    assert res2.status_code == 201, res2.text
    data2 = res2.json()
    assert data2["is_idempotent_replay"] is True
    assert data2["export_id"] == data1["export_id"]
    assert data2["file_id"] == data1["file_id"]

    # Reusing same key with altered format -> 409
    res_conflict = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=coord["headers"],
        json={"format": "PDF", "idempotency_key": idempotency_key},
    )
    assert res_conflict.status_code == 409, res_conflict.text
    assert res_conflict.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSE"


def test_api100_summary_reflects_submitted_logs(client, identities, organization):
    """Institution export aggregates submitted daily logs and hours."""
    f = pending_http(client, identities, organization)
    inst_id = f["inst"]["id"]

    a, draft = active_revision(client, f)
    post(client, f"/api/v1/logs/{draft['id']}/submit", f["candidate"], {}, 200)

    res = client.post(
        f"/api/v1/institutions/{inst_id}/exports",
        headers=f["coord"]["headers"],
        json={"format": "JSON", "idempotency_key": f"inst-logs-{uuid4()}"},
    )
    assert res.status_code == 201, res.text
    summary = res.json()["summary"]
    assert summary["total_submitted_logs"] >= 1
    assert summary["total_logged_minutes"] >= 60
    assert summary["total_logged_hours"] >= 1.0
