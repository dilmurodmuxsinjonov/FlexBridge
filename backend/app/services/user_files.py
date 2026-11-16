"""Direct PDF upload for any signed-in account (staff evidence such as an
institution appointment order or a signed agreement).

The candidate upload stays candidate-only; this path exists so university and
organization representatives can attach the PDFs their governance requests
require. Same fail-closed pipeline (pdf_intake): no generated files, AV must
confirm the bytes, the object must be stored before the CLEAN record exists.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import rate_limit
from app.db.storage import files_table, now, transaction
from app.services import pdf_intake
from app.services.auth import AuthError
from app.services.authority import account_authority

audit = AppendOnlyAuditStore()

PURPOSES = {
    "INSTITUTION_APPOINTMENT": "GOVERNANCE_EVIDENCE",
    "INSTITUTION_AGREEMENT": "GOVERNANCE_EVIDENCE",
    "ORGANIZATION_EVIDENCE": "GOVERNANCE_EVIDENCE",
}


def upload_user_pdf(actor: ActorContext, payload: dict[str, Any]) -> dict[str, Any]:
    purpose = str(payload.get("purpose") or "").upper()
    retention = PURPOSES.get(purpose)
    if retention is None:
        raise AuthError("INVALID_FILE_PURPOSE", "Unsupported document purpose", 422)
    rate_limit("user-pdf-upload", actor.user_id, 30, 3600)
    with transaction() as conn:
        account_authority(conn, actor)

    filename = pdf_intake.clean_filename(payload.get("filename"))
    raw = pdf_intake.decode_pdf(payload.get("content_base64"))
    pdf_intake.scan_and_validate(raw)
    file_id = str(uuid4())
    stored = pdf_intake.store(f"private/users/{actor.user_id}/{file_id}.pdf", raw)

    with transaction() as conn:
        account_authority(conn, actor)
        ts = now()
        conn.execute(
            files_table.insert().values(
                id=file_id,
                created_at=ts,
                updated_at=ts,
                owner_user_id=actor.user_id,
                storage_key=stored.storage_key,
                filename=filename,
                mime_type="application/pdf",
                byte_size=stored.byte_size,
                sha256=stored.sha256,
                scan_status="CLEAN",
                scanned_at=ts,
                retention_class=retention,
                object_version=stored.version_id,
                storage_bucket=stored.bucket,
                storage_version_id=stored.version_id,
                storage_etag=stored.etag,
            )
        )
        audit.append_audit_event(
            actor_id=actor.user_id,
            action="USER_PDF_UPLOADED_AND_SCANNED",
            entity_type="file",
            entity_id=file_id,
            metadata={"purpose": purpose, "byte_size": stored.byte_size, "sha256": stored.sha256},
        )
    return {
        "file_id": file_id,
        "filename": filename,
        "mime_type": "application/pdf",
        "byte_size": stored.byte_size,
        "sha256": stored.sha256,
        "scan_status": "CLEAN",
        "purpose": purpose,
        "created_at": ts.isoformat(),
    }
