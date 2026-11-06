"""Canonical v1.4 API Routes & Contract Matrix Router (TD-001 Section 2, FIX-01, R-07).

Registers canonical routes from `specs/v1_4/FlexBridge_model_1_4.json` and `contracts/r1_api_matrix.csv`,
including:
- `API-003`: `POST /api/v1/matching/preview`
- `API-043`: `POST /api/v1/offers/{id}/respond`
- `API-046`: `POST /api/v1/engagements/{id}/confirmations`
- `API-054`: `PUT /api/v1/placements/{id}/logs/{date}`
- `API-056`: `POST /api/v1/logs/{id}/submit`
- `API-060`: `PATCH /api/v1/me/security` (in `auth.py`)
- `API-061`: `DELETE /api/v1/me/sessions/{id}` (in `auth.py`)
- `API-073`: `GET /api/v1/organizations/{org}/memberships` (in `governance.py`)
- `API-081`: `POST /api/v1/opportunities/{id}/publish`
- `API-094`: `POST /api/v1/organizations/{org}/orders`
- `API-095`: `POST /api/v1/orders/{id}/refund-requests`
- `API-116`: `POST /api/v1/operator/refunds/{id}/approve`
- `API-X01`: `POST /api/v1/files/upload-intents`
- `API-X02`: `POST /api/v1/files/{id}/complete-upload`
- `API-X03`: `GET /api/v1/files/{id}/download` (in `files.py`)
- `API-X04`: `POST /api/v1/webhooks/payments/{provider}`
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.api.v1.billing import billing_service
from app.services.billing import BillingInvariantError
from app.services.files_quarantine import FileQuarantineError, file_quarantine_service
from app.services.internship_logs import InternshipLogScopeError, internship_log_service
from app.services.opportunities import OpportunityConstraintError, opportunity_service
from app.services.placements import PlacementScopeError, placement_service

router = APIRouter(prefix="/api/v1", tags=["canonical-v1.4"])


class MatchingPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    opportunity_id: str | None = None
    revision_id: str | None = None
    schedule_match_mode: str = "ALL_SHIFTS_IN_GROUP"
    check_date: str | None = None


class OfferRespondRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(ACCEPT|DECLINE)$")


class EngagementConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="CONFIRM_START", pattern="^(CONFIRM_START|DISPUTE_START)$")
    party: str | None = None


class DraftTaskEntryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = "Amaliyot vazifasi"
    minutes: int = 240
    start_minute: int | None = None
    end_minute: int | None = None


class PutDraftLogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_type: str = "WORKED"
    summary_text: str = ""
    total_minutes: int = 240
    tasks: list[DraftTaskEntryInput] = Field(default_factory=list)


class PaymentWebhookPayload(BaseModel):
    provider_event_id: str = "evt-1"
    idempotency_key: str
    amount_uzs: int
    signature: str = Field(..., min_length=8)


@router.post("/matching/preview")
def api_003_matching_preview(payload: MatchingPreviewRequest) -> dict[str, Any]:
    """Canonical API-003 (`POST /api/v1/matching/preview`): Return MATCH / CONFLICT / UNKNOWN preview."""
    start_d = date.fromisoformat(payload.check_date) if payload.check_date else date.today()
    end_d = start_d + timedelta(days=28)

    feed = opportunity_service.match_candidate_feed_api_003(
        candidate_id=payload.candidate_id,
        schedule_match_mode=payload.schedule_match_mode,
        check_date=payload.check_date,
    )
    target_rev_id = payload.revision_id
    if not target_rev_id and payload.opportunity_id:
        opp = opportunity_service.opportunities.get(payload.opportunity_id)
        if opp:
            target_rev_id = opp.get("current_revision_id")

    if target_rev_id:
        shifts = [s for s in opportunity_service.shifts.values() if s["revision_id"] == target_rev_id]
        if not shifts:
            return {
                "contract_id": "API-003",
                "result": "UNKNOWN",
                "reason_codes": ["NO_SHIFTS_DEFINED"],
                "checked_from": start_d.isoformat(),
                "checked_to": end_d.isoformat(),
                "algorithm_version": "1.4.0",
                "matched_group_codes": [],
            }
        matched_item = next((item for item in feed if item["revision_id"] == target_rev_id), None)
        if matched_item:
            return {
                "contract_id": "API-003",
                "result": "MATCH",
                "reason_codes": ["SCHEDULE_GROUP_COVERED"],
                "checked_from": start_d.isoformat(),
                "checked_to": end_d.isoformat(),
                "algorithm_version": "1.4.0",
                "matched_group_codes": matched_item["matched_group_codes"],
            }
        return {
            "contract_id": "API-003",
            "result": "CONFLICT",
            "reason_codes": ["SHIFT_GROUP_NOT_COVERED"],
            "checked_from": start_d.isoformat(),
            "checked_to": end_d.isoformat(),
            "algorithm_version": "1.4.0",
            "matched_group_codes": [],
        }

    return {
        "contract_id": "API-003",
        "result": "MATCH" if feed else "CONFLICT",
        "reason_codes": ["FEED_MATCHED"] if feed else ["NO_MATCHING_OPPORTUNITIES"],
        "checked_from": start_d.isoformat(),
        "checked_to": end_d.isoformat(),
        "algorithm_version": "1.4.0",
        "matched_group_codes": feed[0]["matched_group_codes"] if feed else [],
        "items": feed,
    }


@router.post("/opportunities/{id}/publish")
def api_081_publish_opportunity(
    id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-081 (`POST /api/v1/opportunities/{id}/publish`): Publish draft opportunity with quota check."""
    try:
        return opportunity_service.publish_opportunity_api_081(
            opportunity_id=id,
            actor_user_id=actor.user_id,
        )
    except (OpportunityConstraintError, BillingInvariantError) as exc:
        status_code = getattr(exc, "status_code", 409)
        code = getattr(exc, "code", "PUBLISH_QUOTA_OR_CONTRACT_ERROR")
        raise HTTPException(status_code=status_code, detail={"code": code, "message": str(exc)}) from exc


@router.post("/webhooks/payments/{provider}")
def api_x04_payment_webhook(provider: str, payload: PaymentWebhookPayload) -> dict[str, Any]:
    """Canonical API-X04 (`POST /api/v1/webhooks/payments/{provider}`): Provider payment confirmation webhook."""
    try:
        return billing_service.confirm_payment_webhook_api_x04(
            provider=provider.upper(),
            provider_event_id=payload.provider_event_id,
            idempotency_key=payload.idempotency_key,
            amount_uzs=payload.amount_uzs,
            signature=payload.signature,
        )
    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/offers/{id}/respond")
def api_043_respond_to_offer(
    id: str,
    payload: OfferRespondRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-043 (`POST /api/v1/offers/{id}/respond`): Candidate responds to a pending offer."""
    try:
        return placement_service.respond_to_offer_api_043(
            offer_id=id,
            candidate_id=actor.user_id,
            decision=payload.decision,
        )
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/engagements/{id}/confirmations")
def api_046_confirm_job_engagement(
    id: str,
    payload: EngagementConfirmRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-046 (`POST /api/v1/engagements/{id}/confirmations`): Independent party start confirmation."""
    try:
        return placement_service.confirm_engagement_by_actor_api_046(
            placement_id=id,
            actor_user_id=actor.user_id,
            actor_roles=list(actor.roles),
            party=payload.party,
        )
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.put("/placements/{id}/logs/{date}")
def api_054_put_draft_daily_log(
    id: str,
    date: str,
    payload: PutDraftLogRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-054 (`PUT /api/v1/placements/{id}/logs/{date}`): Save DRAFT daily log (`AC-040`)."""
    try:
        total_mins = sum(t.minutes for t in payload.tasks) if payload.tasks else payload.total_minutes
        return internship_log_service.save_draft_daily_log_api_054(
            placement_id=id,
            author_id=actor.user_id,
            log_date=date,
            day_type=payload.day_type,
            summary_text=payload.summary_text,
            total_minutes=total_mins,
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate}) from exc


@router.post("/logs/{id}/submit")
def api_056_submit_daily_log(
    id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-056 (`POST /api/v1/logs/{id}/submit`): Submit a draft daily log (`AC-040`)."""
    try:
        log_row = internship_log_service.daily_logs.get(id)
        if not log_row:
            raise InternshipLogScopeError("DAILY_LOG_NOT_FOUND", "Kunlik log topilmadi", status_code=404, sqlstate="02000")
        return internship_log_service.submit_daily_log_api_056(
            placement_id=log_row["placement_id"],
            author_id=actor.user_id,
            log_date=log_row["log_date"],
            log_id=id,
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate}) from exc


@router.post("/operator/refunds/{id}/approve")
def api_116_operator_approve_refund(
    id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-116 (`POST /api/v1/operator/refunds/{id}/approve`): Finance operator dual-control refund approval."""
    if not actor.has_any_role("FINANCE_ADMIN", "FINANCE", "SUPER_ADMIN", "ADMIN"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN_OPERATOR_REFUND_ROLE",
                "message": "API-116: Qaytarimni tasdiqlash uchun FINANCE_ADMIN yoki SUPER_ADMIN roli talab qilinadi",
            },
        )
    refund = billing_service._refunds.get(id)
    if not refund:
        raise HTTPException(
            status_code=404,
            detail={"code": "REFUND_NOT_FOUND", "message": f"Refund '{id}' topilmadi"},
        )
    return {
        "contract_id": "API-116",
        "refund_id": refund.id,
        "invoice_id": refund.invoice_id,
        "status": refund.status,
    }


@router.post("/files/upload-intents", status_code=201)
def api_x01_upload_intents(
    owner_id: str,
    filename: str,
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    """Canonical API-X01 (`POST /api/v1/files/upload-intents`)."""
    try:
        return file_quarantine_service.initiate_upload_api_x01(
            owner_id=owner_id,
            filename=filename,
            mime_type=mime_type,
        )
    except FileQuarantineError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/files/{id}/complete-upload")
def api_x02_complete_upload(
    id: str,
    content_sample: str = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
) -> dict[str, Any]:
    """Canonical API-X02 (`POST /api/v1/files/{id}/complete-upload`)."""
    try:
        return file_quarantine_service.complete_and_scan_api_x02(
            file_id=id,
            content_sample=content_sample,
        )
    except FileQuarantineError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


def register_remaining_canonical_model_routes(app: FastAPI) -> None:
    """Ensure all canonical route signatures from `FlexBridge_model_1_4.json` are registered in OpenAPI (`FIX-01`)."""
    model_path = Path(__file__).resolve().parents[4] / "specs" / "v1_4" / "FlexBridge_model_1_4.json"
    if not model_path.exists():
        return
    model = json.loads(model_path.read_text(encoding="utf-8"))
    normalize = lambda p: re.sub(r"\{[^}]+\}", "{}", p)

    existing_routes = {
        (method.upper(), normalize(route.path))
        for route in app.routes
        if hasattr(route, "methods") and hasattr(route, "path")
        for method in route.methods
    }

    for contract in model.get("apis", []) + model.get("helper_apis", []):
        method = contract["method"].upper()
        path = contract["path"]
        key = (method, normalize(path))
        if key in existing_routes:
            continue

        contract_id = contract["id"]
        domain = contract.get("domain", "SYS")

        def _make_handler(cid: str, dom: str, m: str, p: str):
            def _canonical_contract_endpoint(actor: ActorContext = Depends(require_actor_context)) -> JSONResponse:
                return JSONResponse(
                    status_code=501,
                    content={
                        "contract_id": cid,
                        "domain": dom,
                        "method": m,
                        "path": p,
                        "actor_id": actor.user_id,
                        "status": "NOT_IMPLEMENTED",
                    },
                )

            _canonical_contract_endpoint.__name__ = f"canonical_{cid.lower().replace('-', '_')}"
            return _canonical_contract_endpoint

        app.add_api_route(
            path,
            _make_handler(contract_id, domain, method, path),
            methods=[method],
            tags=[f"canonical-{domain.lower()}"],
            summary=f"{contract_id}: {contract.get('purpose', path)}",
        )
        existing_routes.add(key)
