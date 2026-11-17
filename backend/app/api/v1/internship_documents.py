"""FastAPI router for 3-Party E-Imzo, Standardized Internship Diary & Final Conclusion Documents (FB-204)."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.services.internship_documents import internship_documents_service
from app.services.placement_admission import PlacementScopeError

router = APIRouter(prefix="/api/v1", tags=["internship_documents"])


def _handle_scope_error(exc: PlacementScopeError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "sqlstate": getattr(exc, "sqlstate", "45001"), "message": str(exc)},
    )


class EImzoUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    party: Literal["CANDIDATE", "EMPLOYER", "UNIVERSITY"]
    full_name: str = Field(..., min_length=3, max_length=160)
    position_title: str = Field(..., min_length=2, max_length=160)
    organization_or_university: str = Field(..., min_length=2, max_length=200)
    stir_or_pinfl: str | None = Field(default="", max_length=32)
    certificate_serial: str | None = Field(default=None, max_length=64)


class DocumentDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["DIARY", "CONCLUSION"]
    export_format: Literal["PDF", "JSON"] = "PDF"


@router.get("/me/e-imzo")
def get_my_eimzo_certificates_endpoint(
    party: str | None = None,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.get_my_eimzo_certificates(actor=actor, party=party)
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.put("/me/e-imzo")
def upsert_my_eimzo_certificate_endpoint(
    payload: EImzoUpsertRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.upsert_my_eimzo_certificate(
            actor=actor,
            payload=payload.model_dump(),
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.get("/placements/{placement_id}/diary/standard")
def get_standardized_diary_endpoint(
    placement_id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.get_standardized_diary_workspace(
            actor=actor,
            placement_id=placement_id,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.put("/placements/{placement_id}/diary/standard")
def update_standardized_diary_endpoint(
    placement_id: str,
    payload: dict[str, Any] = Body(...),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.update_standardized_diary(
            actor=actor,
            placement_id=placement_id,
            payload=payload,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.post("/placements/{placement_id}/diary/sign")
def sign_internship_diary_endpoint(
    placement_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.sign_internship_diary(
            actor=actor,
            placement_id=placement_id,
            payload=payload,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.get("/placements/{placement_id}/conclusion-document")
def get_final_conclusion_document_endpoint(
    placement_id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.get_final_conclusion_document(
            actor=actor,
            placement_id=placement_id,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.post("/placements/{placement_id}/conclusion-document/sign")
def sign_final_conclusion_document_endpoint(
    placement_id: str,
    payload: dict[str, Any] = Body(...),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.sign_final_conclusion_document(
            actor=actor,
            placement_id=placement_id,
            payload=payload,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.post("/placements/{placement_id}/documents/download")
def download_official_document_endpoint(
    placement_id: str,
    payload: DocumentDownloadRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.download_official_document(
            actor=actor,
            placement_id=placement_id,
            document_type=payload.document_type,
            export_format=payload.export_format,
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.get("/placements/{placement_id}/documents/files/{file_id}/download")
def stream_official_document_file_endpoint(
    placement_id: str,
    file_id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> Response:
    try:
        raw, mime_type, filename = internship_documents_service.get_document_file_bytes(
            actor=actor,
            placement_id=placement_id,
            file_id=file_id,
        )
        return Response(
            content=raw,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc


@router.get("/internship-documents/verify/{verification_code}")
def verify_eimzo_signature_endpoint(
    verification_code: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_documents_service.verify_signature_code(verification_code=verification_code)
    except PlacementScopeError as exc:
        raise _handle_scope_error(exc) from exc
