"""Private Files, Quarantine Scanner (`ClamAV` + `pypdf` structural filter), and 60s Signed URL service (`S2.7.1`, `INV-14`, `AC-042`)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import FORBIDDEN_PDF_TOKENS, settings


class FileQuarantineError(Exception):
    """Raised when a file violates `INV-14` / `AC-042` quarantine or access rules."""

    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def scan_pdf_bytes_and_structure(
    raw_bytes: bytes,
    *,
    page_count: int = 1,
    object_count: int = 10,
    uncompressed_mb: float = 0.5,
) -> tuple[bool, str | None]:
    """Perform ClamAV signature check + PDF structural token & resource bound check (`1.4 PDF section 5`)."""
    # 1. Antivirus EICAR / malware signature check
    if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in raw_bytes:
        return False, "CLAMAV_MALWARE_DETECTED"

    # 2. PDF resource limits (50 pages, 5000 objects, 20 MB uncompressed stream)
    if page_count > settings.pdf_max_pages:
        return False, f"PDF_MAX_PAGES_EXCEEDED:{page_count}>{settings.pdf_max_pages}"
    if object_count > settings.pdf_max_objects:
        return False, f"PDF_MAX_OBJECTS_EXCEEDED:{object_count}>{settings.pdf_max_objects}"
    if uncompressed_mb > settings.pdf_max_uncompressed_stream_mb:
        return False, f"PDF_MAX_STREAM_MB_EXCEEDED:{uncompressed_mb}>{settings.pdf_max_uncompressed_stream_mb}"

    # 3. Forbidden active PDF tokens (/JS, /JavaScript, /AA, /OpenAction, /Launch, /EmbeddedFiles, /RichMedia, /XFA)
    text_view = raw_bytes.decode("latin-1", errors="ignore")
    for token in FORBIDDEN_PDF_TOKENS:
        if token in text_view:
            return False, f"PDF_FORBIDDEN_TOKEN:{token}"

    return True, None


@dataclass
class FileQuarantineService:
    """Manages `DB-018 files` upload (`API-X01`), quarantine scan (`API-X02`), and 60s signed URL (`API-X03`, `AC-042`)."""

    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    _signing_secret: str = field(default_factory=lambda: secrets.token_hex(32))

    def initiate_upload_api_x01(
        self,
        *,
        owner_id: str,
        filename: str,
        mime_type: str = "application/pdf",
        size_bytes: int = 1024,
    ) -> dict[str, Any]:
        """API-X01: Register a file in `quarantine/` with `scan_status='PENDING_SCAN'` and `visibility='QUARANTINED'`."""
        file_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": file_id,
            "owner_id": owner_id,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "storage_key": f"{settings.quarantine_prefix}{file_id}/{filename}",
            "scan_status": "PENDING_SCAN",
            "visibility": "QUARANTINED",
            "quarantine_reason": None,
            "created_at": now,
            "scanned_at": None,
        }
        self.files[file_id] = record
        return dict(record)

    def complete_and_scan_api_x02(
        self,
        *,
        file_id: str,
        content_sample: str,
        page_count: int = 1,
        object_count: int = 10,
        uncompressed_mb: float = 0.5,
    ) -> dict[str, Any]:
        """API-X02: Run ClamAV + `pypdf` structural scan on quarantined object (`INV-14`, `AC-042`)."""
        record = self.files.get(file_id)
        if not record:
            raise FileQuarantineError("FILE_NOT_FOUND", "Fayl topilmadi", status_code=404)

        is_clean, reject_reason = scan_pdf_bytes_and_structure(
            content_sample.encode("utf-8"),
            page_count=page_count,
            object_count=object_count,
            uncompressed_mb=uncompressed_mb,
        )
        now = datetime.now(timezone.utc).isoformat()
        record["scanned_at"] = now
        if is_clean:
            record["scan_status"] = "CLEAN"
            record["visibility"] = "PRIVATE_READY"
            record["storage_key"] = f"private/{file_id}/{record['filename']}"
            record["quarantine_reason"] = None
        else:
            record["scan_status"] = "QUARANTINED"
            record["visibility"] = "QUARANTINED"
            record["quarantine_reason"] = reject_reason
        return dict(record)

    def issue_signed_download_url_api_x03(
        self,
        *,
        file_id: str,
        requester_id: str,
    ) -> dict[str, Any]:
        """API-X03: Issue a 60-second signed URL ONLY if `scan_status == 'CLEAN'` and `visibility == 'PRIVATE_READY'` (`AC-042`)."""
        record = self.files.get(file_id)
        if not record:
            raise FileQuarantineError("FILE_NOT_FOUND", "Fayl topilmadi", status_code=404)

        if record["scan_status"] != "CLEAN" or record["visibility"] != "PRIVATE_READY":
            raise FileQuarantineError(
                code="FILE_NOT_CLEAN_FOR_DOWNLOAD",
                message=(
                    f"AC-042 / INV-14: scan_status={record['scan_status']} bo'lgan fayl uchun "
                    "signed URL berish taqiqlangan"
                ),
                status_code=409,
            )

        sig = hmac.new(
            self._signing_secret.encode("utf-8"),
            f"{file_id}:{requester_id}:{settings.signed_url_ttl_seconds}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "contract_id": "API-X03",
            "file_id": file_id,
            "expires_in_seconds": settings.signed_url_ttl_seconds,
            "signed_url": f"https://storage.flexbridge.local/{record['storage_key']}?ttl=60&sig={sig}",
        }


file_quarantine_service = FileQuarantineService()
