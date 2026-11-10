"""Canonical v1.4 API Routes & Contract Matrix Router (TD-001 Section 2, FIX-01, R-07).

Registers canonical routes from `specs/v1_4/FlexBridge_model_1_4.json` and `contracts/r1_api_matrix.csv`,
including:
- `API-003`: `POST /api/v1/matching/preview`
- `API-043`: `POST /api/v1/offers/{id}/respond`
- `API-046`: `POST /api/v1/engagements/{id}/confirmations`
- `API-053`: `GET /api/v1/placements/{id}/logs` (in `placements.py`)
- `API-054`: `PUT /api/v1/placements/{id}/logs/{date}`
- `API-055`: `POST /api/v1/log-entries/{id}/evidence`
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
from uuid import UUID
from pathlib import Path
from typing import Any
from dataclasses import asdict

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context, require_org, require_platform, candidate_id_for
from app.api.v1.billing import billing_service
from app.services.billing import BillingInvariantError
from app.services.files_quarantine import FileQuarantineError, file_quarantine_service
from app.services.internship_logs import InternshipLogScopeError, internship_log_service
from app.services.opportunities import OpportunityConstraintError, opportunity_service
from app.services.placements import PlacementScopeError, placement_service

router = APIRouter(prefix="/api/v1", tags=["canonical-v1.4"])


class MatchingPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID
    opportunity_id: UUID | None = None
    revision_id: UUID | None = None
    schedule_match_mode: str = Field(default='ALL_SHIFTS_IN_GROUP', pattern='^(ALL_SHIFTS_IN_GROUP|ANY_SHIFT_IN_GROUP)$')
    check_date: date | None = None
    commute_buffer_minutes: int = Field(default=30, ge=0, le=180)
    limit: int = Field(default=100, ge=1, le=100)
    after_id: UUID | None = None


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
    model_config = ConfigDict(extra="forbid")
    provider_event_id: str = Field(min_length=8,max_length=128)
    attempt_id: UUID
    amount_uzs: int = Field(gt=0)
    currency: str = "UZS"
    timestamp: int
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

class CanonicalOrderRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan_code: str
    idempotency_key: str = Field(min_length=8,max_length=128)

class CanonicalRefundRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    amount_uzs: int = Field(gt=0)
    reason: str = Field(min_length=15,max_length=2000)

class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = Field(pattern='^(PAUSED|CLOSED)$')

@router.post('/organizations/{org}/orders',status_code=201)
def canonical_order(org: UUID,payload: CanonicalOrderRequest,actor: ActorContext=Depends(require_actor_context)):
    order,invoice=billing_service.create_order_and_invoice(organization_id=str(org),plan_code=payload.plan_code,actor=actor,idempotency_key=payload.idempotency_key)
    return {'contract_id':'API-094','order':asdict(order),'invoice':asdict(invoice)}

@router.post('/orders/{id}/refund-requests',status_code=201)
def canonical_refund(id: UUID,payload: CanonicalRefundRequest,actor: ActorContext=Depends(require_actor_context)):
    from app.db.storage import transaction
    with transaction() as conn:
        order=billing_service._get_order(str(id),conn)
        if not order: raise BillingInvariantError('ORDER_NOT_FOUND')
        require_org(actor,order.organization_id,'OWNER','BILLING')
        invoice=billing_service._invoice_for_order(str(id),conn)
        return {'contract_id':'API-095',**billing_service.request_refund(invoice_id=invoice.id,amount_uzs=payload.amount_uzs,reason=payload.reason,actor=actor)}

@router.post('/opportunities/{id}/transition')
def transition(id: UUID,payload: TransitionRequest,actor: ActorContext=Depends(require_actor_context)):
    return billing_service.update_opportunity_status(opportunity_id=str(id),new_status=payload.status,actor_user_id=actor.user_id)


@router.post("/matching/preview")
def api_003_matching_preview(payload: MatchingPreviewRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    """Canonical API-003 (`POST /api/v1/matching/preview`): Return MATCH / CONFLICT / UNKNOWN preview."""
    if str(payload.candidate_id) != candidate_id_for(actor):
        raise HTTPException(403, detail={'code': 'CANDIDATE_SCOPE_FORBIDDEN'})
    page = opportunity_service.match_feed_page(candidate_id=str(payload.candidate_id),
        schedule_match_mode=payload.schedule_match_mode, check_date=payload.check_date,
        commute_buffer_minutes=payload.commute_buffer_minutes, limit=payload.limit,
        after_id=str(payload.after_id) if payload.after_id else None,
        opportunity_id=str(payload.opportunity_id) if payload.opportunity_id else None,
        revision_id=str(payload.revision_id) if payload.revision_id else None)
    if payload.opportunity_id or payload.revision_id:
        if not page['evaluations']:
            raise HTTPException(404, detail={'code': 'PUBLISHED_REVISION_NOT_FOUND'})
        return page['evaluations'][0]
    from app.services.schedule import local_today
    from app.services.schedule_matching import ALGORITHM_VERSION
    evaluations = page['evaluations']
    status = 'MATCH' if page['items'] else ('UNKNOWN' if not evaluations or any(
        item['result'] == 'UNKNOWN' for item in evaluations) else 'CONFLICT')
    start = max(payload.check_date or local_today(), local_today())
    return {'contract_id': 'API-003', 'result': status,
        'reason_codes': ['PAGE_MATCHED' if page['items'] else 'NO_MATCH_ON_PAGE'],
        'checked_from': min((item['checked_from'] for item in evaluations), default=start.isoformat()),
        'checked_to': max((item['checked_to'] for item in evaluations), default=(start + timedelta(days=28)).isoformat()),
        'algorithm_version': ALGORITHM_VERSION,
        'availability_revision': evaluations[0]['availability_revision'] if evaluations else None,
        'matched_group_codes': page['items'][0]['matched_group_codes'] if page['items'] else [], **page}


@router.post("/opportunities/{id}/publish")
def api_081_publish_opportunity(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-081 (`POST /api/v1/opportunities/{id}/publish`): Publish draft opportunity with quota check."""
    try:
        return opportunity_service.publish_opportunity_api_081(
            opportunity_id=str(id),
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
        from uuid import UUID
        return billing_service.confirm_payment_webhook_api_x04(provider=provider.upper(),
            provider_event_id=payload.provider_event_id,attempt_id=str(payload.attempt_id),
            amount_uzs=payload.amount_uzs,currency=payload.currency,signature=payload.signature,timestamp=payload.timestamp)

    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/offers/{id}/respond")
def api_043_respond_to_offer(
    id: UUID,
    payload: OfferRespondRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-043 (`POST /api/v1/offers/{id}/respond`): Candidate responds to a pending offer."""
    try:
        return placement_service.respond_to_offer_api_043(
            offer_id=str(id),
            candidate_id=candidate_id_for(actor),
            decision=payload.decision,
        )
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/engagements/{id}/confirmations")
def api_046_confirm_job_engagement(
    id: UUID,
    payload: EngagementConfirmRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-046 (`POST /api/v1/engagements/{id}/confirmations`): Independent party start confirmation."""
    try:
        return placement_service.confirm_engagement_by_actor_api_046(
            placement_id=str(id),
            actor_user_id=actor.user_id,
            actor_roles=list(actor.roles),
            party=payload.party,
            action=payload.action,
        )
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.put("/placements/{id}/logs/{date}")
def api_054_put_draft_daily_log(
    id: UUID,
    date: str,
    payload: PutDraftLogRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-054 (`PUT /api/v1/placements/{id}/logs/{date}`): Save DRAFT daily log (`AC-040`)."""
    try:
        total_mins = sum(t.minutes for t in payload.tasks) if payload.tasks else payload.total_minutes
        return internship_log_service.save_draft_daily_log_api_054(
            placement_id=str(id),
            actor=actor,
            log_date=date,
            day_type=payload.day_type,
            summary_text=payload.summary_text,
            total_minutes=total_mins,
            tasks=[t.model_dump() for t in payload.tasks],
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate}) from exc


class AttachEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_id: UUID
    visibility: str = Field(default="HOST_AND_ACADEMIC", min_length=1, max_length=50)


@router.post("/log-entries/{id}/evidence", status_code=201)
def api_055_post_log_entry_evidence(
    id: UUID,
    payload: AttachEvidenceRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-055 (`POST /api/v1/log-entries/{id}/evidence`): Attach clean file evidence to daily log task entry (`AC-040`)."""
    try:
        return internship_log_service.attach_task_evidence_api_055(
            actor=actor,
            task_entry_id=str(id),
            file_id=str(payload.file_id),
            visibility=payload.visibility,
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate},
        ) from exc


@router.get("/log-entries/{id}/evidence")
def api_055_get_log_entry_evidence(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Get attached evidence for a daily log task entry with visibility enforcement."""
    try:
        items = internship_log_service.get_task_entry_evidence_api_055(
            actor=actor,
            task_entry_id=str(id),
        )
        return {"items": items, "total": len(items)}
    except InternshipLogScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate},
        ) from exc


@router.post("/logs/{id}/submit")
def api_056_submit_daily_log(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-056 (`POST /api/v1/logs/{id}/submit`): Submit a draft daily log (`AC-040`)."""
    try:
        log_row = internship_log_service.get_log(str(id))
        if not log_row:
            raise InternshipLogScopeError("DAILY_LOG_NOT_FOUND", "Kunlik log topilmadi", status_code=404, sqlstate="02000")
        return internship_log_service.submit_daily_log_api_056(
            placement_id=log_row["placement_id"],
            actor=actor,
            log_date=log_row["log_date"],
            log_id=str(id),
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate}) from exc


@router.post("/operator/refunds/{id}/approve")
def approve_refund(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    from uuid import UUID
    return billing_service.approve_refund(str(id),actor)


def register_remaining_canonical_model_routes(app: FastAPI) -> None:
    """Ensure all canonical route signatures from `FlexBridge_model_1_4.json` are registered in OpenAPI (`FIX-01`)."""
    model_path = Path(__file__).resolve().parents[4] / "specs" / "v1_4" / "FlexBridge_model_1_4.json"
    if not model_path.exists():
        return
    model = json.loads(model_path.read_text(encoding="utf-8"))
    normalize = lambda p: re.sub(r"\{[^}]+\}", "{}", p)

    existing_routes = {(method.upper(),normalize(path)) for path,methods in app.openapi()['paths'].items() for method in methods}
    app.openapi_schema = None

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
