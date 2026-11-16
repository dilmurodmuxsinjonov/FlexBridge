"""Fail-closed intake for user-supplied PDF documents (direct JSON/base64 upload).

The bytes must be a real PDF supplied by the user, the antivirus must confirm it
clean and the private object must be stored before any CLEAN file record exists.
Callers run this outside database transactions (the scan can take seconds).
"""
from __future__ import annotations

import base64
import hashlib
import io
from dataclasses import dataclass

from pypdf import PdfReader

from app.adapters import antivirus, storage
from app.services.auth import AuthError

MAX_BYTES = 20 * 1024 * 1024
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"


@dataclass(frozen=True)
class StoredPdf:
    storage_key: str
    sha256: str
    byte_size: int
    bucket: str
    version_id: str
    etag: str


def decode_pdf(content_b64: object) -> bytes:
    value = str(content_b64 or "").strip()
    if not value:
        raise AuthError("FILE_CONTENT_REQUIRED", "Attach the PDF file itself", 422)
    try:
        if value.startswith("data:") and "," in value:
            value = value.split(",", 1)[1]
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise AuthError("INVALID_BASE64_FILE", "Invalid base64 file content", 422) from exc
    if len(raw) < 16 or len(raw) > MAX_BYTES:
        raise AuthError("INVALID_FILE_SIZE", "PDF file size must be between 16B and 20MB", 422)
    return raw


def scan_and_validate(raw: bytes) -> None:
    if EICAR in raw:
        raise AuthError("MALWARE_DETECTED_QUARANTINED", "Uploaded file failed antivirus inspection", 422)
    try:
        antivirus.scan(raw)
    except ValueError as exc:
        raise AuthError("MALWARE_DETECTED_QUARANTINED", "Uploaded file quarantined by antivirus", 422) from exc
    except Exception as exc:
        raise AuthError("ANTIVIRUS_UNAVAILABLE", "File scanning is temporarily unavailable, try again later", 503) from exc
    if not raw.startswith(b"%PDF-"):
        raise AuthError("INVALID_PDF_FORMAT", "Only valid PDF files (%PDF-) are accepted", 422)
    try:
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) < 1 or len(reader.pages) > 50:
            raise AuthError("INVALID_PDF_PAGES", "PDF must contain between 1 and 50 pages", 422)
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("INVALID_PDF_FORMAT", "Corrupted or invalid PDF file", 422) from exc


def store(storage_key: str, raw: bytes) -> StoredPdf:
    try:
        ref = storage.write_private(storage_key, raw)
        ref.check_bucket()
    except Exception as exc:
        raise AuthError("FILE_STORAGE_UNAVAILABLE", "File storage is temporarily unavailable, try again later", 503) from exc
    return StoredPdf(storage_key, hashlib.sha256(raw).hexdigest(), len(raw), ref.bucket, ref.version_id, ref.etag)


def clean_filename(value: object, default: str = "document.pdf") -> str:
    name = str(value or default).strip() or default
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[-200:]
