"""FastAPI router for Private Files, Quarantine Scan, and 60s Signed URL (`S2.7.1`, `API-X01..X03`, `AC-042`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.files_quarantine import FileQuarantineError, file_quarantine_service

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class InitiateUploadRequest(BaseModel):
    owner_id: str
    filename: str
    mime_type: str = "application/pdf"
    size_bytes: int = 1024


class CompleteAndScanRequest(BaseModel):
    content_sample: str = "%PDF-1.7 clean document"
    page_count: int = 1
    object_count: int = 10
    uncompressed_mb: float = 0.5


@router.post("/upload-init", status_code=201)
def api_x01_upload_init(payload: InitiateUploadRequest) -> dict[str, Any]:
    """API-X01: Initialize file upload into `quarantine/` prefix."""
    return file_quarantine_service.initiate_upload_api_x01(
        owner_id=payload.owner_id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
    )


@router.post("/{file_id}/complete-scan")
def api_x02_complete_scan(file_id: str, payload: CompleteAndScanRequest) -> dict[str, Any]:
    """API-X02: Complete upload and run ClamAV + `pypdf` structural quarantine scan."""
    try:
        return file_quarantine_service.complete_and_scan_api_x02(
            file_id=file_id,
            content_sample=payload.content_sample,
            page_count=payload.page_count,
            object_count=payload.object_count,
            uncompressed_mb=payload.uncompressed_mb,
        )
    except FileQuarantineError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/{file_id}/download")
def api_x03_download_signed_url(
    file_id: str,
    requester_id: str = Query(...),
) -> dict[str, Any]:
    """API-X03: Issue 60-second signed URL ONLY for `CLEAN` / `PRIVATE_READY` files (`AC-042`)."""
    try:
        return file_quarantine_service.issue_signed_download_url_api_x03(
            file_id=file_id,
            requester_id=requester_id,
        )
    except FileQuarantineError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
