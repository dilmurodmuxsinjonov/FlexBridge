"""Canonical v1.4 API Routes & Contract Matrix Router (TD-001 Section 2, FIX-01, R-07).

Registers canonical routes from `specs/v1_4/FlexBridge_model_1_4.json` and `contracts/r1_api_matrix.csv`,
including:
- `API-003`: `POST /api/v1/matching/preview`
- `API-004`: `POST /api/v1/saved-opportunities`
- `API-005`: `GET /api/v1/opportunities/{id}`
- `API-031`: `GET /api/v1/me/notifications` (in `notifications.py`)
- `API-037`: `GET /api/v1/me/saved-opportunities`
- `API-038`: `DELETE /api/v1/me/saved-opportunities/{id}`
- `API-043`: `POST /api/v1/offers/{id}/respond`
- `API-045`: `GET /api/v1/me/engagements/{id}`
- `API-046`: `POST /api/v1/engagements/{id}/confirmations`
- `API-047`: `POST /api/v1/engagements/{id}/ratings`
- `API-053`: `GET /api/v1/placements/{id}/logs` (in `placements.py`)
- `API-054`: `PUT /api/v1/placements/{id}/logs/{date}`
- `API-055`: `POST /api/v1/log-entries/{id}/evidence`
- `API-056`: `POST /api/v1/logs/{id}/submit`
- `API-057`: `GET /api/v1/me/ratings`
- `API-058`: `POST /api/v1/ratings/{id}/appeals`
- `API-059`: `PUT /api/v1/me/notification-preferences`
- `API-060`: `PATCH /api/v1/me/security` (in `auth.py`)
- `API-061`: `DELETE /api/v1/me/sessions/{id}` (in `auth.py`)
- `API-062`: `POST /api/v1/me/privacy-requests`
- `API-063`: `GET /api/v1/me/support-tickets`
- `API-064`: `POST /api/v1/support-tickets/{id}/messages`
- `API-070`: `GET /api/v1/organizations/{org}/entitlements`
- `API-073`: `GET /api/v1/organizations/{org}/memberships` (in `governance.py`)
- `API-081`: `POST /api/v1/opportunities/{id}/publish`
- `API-082`: `GET /api/v1/opportunities/{id}/applications` (in `opportunities.py`)
- `API-083`: `POST /api/v1/applications/{id}/transition`
- `API-084`: `GET /api/v1/applications/{id}/hr`
- `API-090`: `GET /api/v1/me/mentor-review-queue`
- `API-091`: `GET /api/v1/log-revisions/{revision}/workplace`
- `API-092`: `POST /api/v1/log-revisions/{revision}/workplace-reviews`
- `API-093`: `GET /api/v1/organizations/{org}/billing`
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

from fastapi import APIRouter, Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context, optional_actor_context, require_org, require_platform, candidate_id_for
from app.api.v1.billing import billing_service
from app.services.application_hr import ApplicationHRError, application_hr_service
from app.services.billing import BillingInvariantError
from app.services.files_quarantine import FileQuarantineError, file_quarantine_service
from app.services.internship_logs import InternshipLogScopeError, internship_log_service
from app.services.interviews_and_offers import InterviewOfferError, interview_offer_service
from app.services.job_engagements import JobEngagementError, job_engagement_service
from app.services.opportunities import OpportunityConstraintError, opportunity_service
from app.services.moderation_cases import ModerationCaseError, moderation_cases_service
from app.services.placements import PlacementScopeError, placement_service
from app.services.workplace_reviews import WorkplaceReviewError, workplace_review_service

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

    decision: str | None = None
    response: str | None = None
    note: str | None = None


class InterviewResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(..., pattern="^(?i:(ACCEPTED|DECLINED|RESCHEDULE_REQUESTED|COMPLETED|NO_SHOW))$")
    note: str | None = None


class CreateInterviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_at: str
    ends_at: str
    mode: str = Field(default="ONLINE", pattern="^(?i:(ONLINE|IN_PERSON))$")
    location_or_link: str | None = None
    timezone: str = "Asia/Tashkent"


class CreateOfferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_at: str | None = None
    terms_snapshot: dict[str, Any] | None = None
    idempotency_key: str | None = None


class EngagementConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="CONFIRM_START", pattern="^(?i:(CONFIRM_START|DISPUTE_START|CONFIRM_END|DISPUTE_END))$")
    party: str | None = None
    note: str | None = None


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


@router.get("/opportunities/{id}")
def api_005_get_opportunity_detail(
    id: UUID,
    actor: ActorContext | None = Depends(optional_actor_context),
) -> dict[str, Any]:
    """Canonical API-005 (`GET /api/v1/opportunities/{id}`): Public immutable published revision, wage, eligibility, and org details (`CAP-001`)."""
    try:
        return opportunity_service.get_opportunity_detail(
            opportunity_id=str(id),
            actor=actor,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


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


@router.post("/interviews/{id}/responses")
def api_042_respond_to_interview(
    id: UUID,
    payload: InterviewResponseRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-042 (`POST /api/v1/interviews/{id}/responses`): Candidate or host responds to interview (CAP-009)."""
    try:
        return interview_offer_service.respond_to_interview(
            actor=actor,
            interview_id=str(id),
            response=payload.response.upper(),
            note=payload.note,
        )
    except InterviewOfferError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/offers/{id}/respond")
def api_043_respond_to_offer(
    id: UUID,
    payload: OfferRespondRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-043 (`POST /api/v1/offers/{id}/respond`): Candidate responds to a pending offer (CAP-011)."""
    dec = payload.decision or payload.response
    if not dec or dec.upper() not in ("ACCEPT", "DECLINE"):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Faqat 'ACCEPT' yoki 'DECLINE' qabul qilinadi"},
        )
    try:
        return interview_offer_service.respond_to_offer(
            actor=actor,
            offer_id=str(id),
            response=dec.upper(),
            note=payload.note,
        )
    except InterviewOfferError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/applications/{id}/interviews")
def api_085_schedule_interview(
    id: UUID,
    payload: CreateInterviewRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-085 (`POST /api/v1/applications/{id}/interviews`): Host schedules interview for application (CAP-009)."""
    try:
        return interview_offer_service.schedule_interview(
            actor=actor,
            application_id=str(id),
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            mode=payload.mode.upper(),
            location_or_link=payload.location_or_link,
            timezone_str=payload.timezone,
        )
    except InterviewOfferError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/applications/{id}/offers")
def api_086_issue_offer(
    id: UUID,
    payload: CreateOfferRequest | None = None,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-086 (`POST /api/v1/applications/{id}/offers`): Host issues offer for application (CAP-011)."""
    p = payload or CreateOfferRequest()
    try:
        return interview_offer_service.issue_offer(
            actor=actor,
            application_id=str(id),
            expires_at=p.expires_at,
            terms_snapshot=p.terms_snapshot,
            idempotency_key=p.idempotency_key,
        )
    except InterviewOfferError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/me/engagements/{id}")
def api_045_get_my_engagement(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-045 (`GET /api/v1/me/engagements/{id}`): View engagement details, confirmations, dual-sided status (CAP-012)."""
    try:
        return job_engagement_service.get_engagement(
            actor=actor,
            engagement_id=str(id),
        )
    except JobEngagementError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/engagements/{id}/confirmations")
def api_046_confirm_job_engagement(
    id: UUID,
    payload: EngagementConfirmRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-046 (`POST /api/v1/engagements/{id}/confirmations`): Dual-party start/end/dispute confirmation (CAP-012 / AC-014)."""
    try:
        return job_engagement_service.confirm_engagement(
            actor=actor,
            engagement_id=str(id),
            action=payload.action.upper(),
            party=payload.party,
            note=payload.note,
        )
    except JobEngagementError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    except PlacementScopeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


class CriterionScoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: UUID
    score: int = Field(..., ge=1, le=5)


class SubmitEngagementRatingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rubric_id: UUID | None = None
    scores: list[CriterionScoreInput] = Field(..., min_length=1, max_length=50)
    comment: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=128)


@router.post("/engagements/{id}/ratings", status_code=201)
def api_047_post_engagement_rating(
    id: UUID,
    payload: SubmitEngagementRatingPayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-047 (`POST /api/v1/engagements/{id}/ratings`): Mutual double-blind engagement ratings (CAP-027 / AC-024)."""
    from app.services.user_ratings import RatingScopeError, user_ratings_service
    try:
        return user_ratings_service.submit_engagement_rating_api_047(
            actor=actor,
            engagement_id=str(id),
            scores=[s.model_dump() for s in payload.scores],
            rubric_id=str(payload.rubric_id) if payload.rubric_id else None,
            comment=payload.comment,
            idempotency_key=payload.idempotency_key,
        )
    except RatingScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate},
        ) from exc
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


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


@router.get("/me/ratings")
def get_my_ratings_endpoint(
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-057 (`GET /api/v1/me/ratings`): Personal rating summary, rubric version, and score explanation (`AC-021..024`, `CAP-027`)."""
    from app.services.user_ratings import user_ratings_service
    return user_ratings_service.get_my_ratings_api_057(actor=actor)


class RatingAppealPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reason: str = Field(..., min_length=10, max_length=4000, description="E'tiroz sababi va dalillari")
    category: str = Field(default="FACTUAL_DISPUTE", max_length=50, description="E'tiroz toifasi")
    evidence_notes: str | None = Field(default=None, max_length=4000, description="Qo'shimcha dalillar")


@router.post("/ratings/{id}/appeals", status_code=201)
def submit_rating_appeal_endpoint(
    id: UUID,
    payload: RatingAppealPayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-058 (`POST /api/v1/ratings/{id}/appeals`): Submit rating appeal (`AC-025`, `CAP-028`, `DB-067`)."""
    from app.services.user_ratings import RatingScopeError, user_ratings_service
    try:
        return user_ratings_service.submit_rating_appeal_api_058(
            rating_id=str(id),
            actor=actor,
            reason=payload.reason,
            category=payload.category,
            evidence_notes=payload.evidence_notes,
        )
    except RatingScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate},
        ) from exc


class PreferenceUpdateItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel: str = Field(..., description="Kanal: EMAIL, SMS, PUSH, WHATSAPP")
    purpose: str = Field(..., description="Maqsad: TRANSACTIONAL, SECURITY, MARKETING")
    enabled: bool = Field(..., description="Holat: true / false")


class NotificationPreferencesUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    preferences: list[PreferenceUpdateItem] = Field(..., min_length=1, description="Sozlamalar ro'yxati")


@router.get("/me/notification-preferences")
def get_notification_preferences_endpoint(
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve current notification preferences for authenticated user."""
    from app.services.notification_preferences import notification_preferences_service
    return notification_preferences_service.get_preferences(actor=actor)


@router.put("/me/notification-preferences")
def update_notification_preferences_endpoint(
    payload: NotificationPreferencesUpdatePayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-059 (`PUT /api/v1/me/notification-preferences`): Update user notification preferences (`CAP-031`, `AC-030`)."""
    from app.services.notification_preferences import NotificationScopeError, notification_preferences_service
    try:
        return notification_preferences_service.update_preferences_api_059(
            actor=actor,
            preferences=[item.model_dump() for item in payload.preferences],
        )
    except NotificationScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc), "sqlstate": exc.sqlstate},
        ) from exc


class PrivacyRequestPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: str = Field(..., description="Privacy so'rovi turi: EXPORT, DELETE, RECTIFY")
    reason: str | None = Field(default=None, max_length=2000, description="So'rov sababi")
    details: dict[str, Any] | None = Field(default=None, description="Qo'shimcha tafsilotlar")


@router.post("/me/privacy-requests", status_code=201)
def create_privacy_request_endpoint(
    payload: PrivacyRequestPayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-062 (`POST /api/v1/me/privacy-requests`): Submit user privacy request (`CAP-032`, `AC-031`)."""
    from app.services.privacy import PrivacyError, privacy_service
    try:
        return privacy_service.create_privacy_request_api_062(
            actor=actor,
            kind=payload.kind,
            reason=payload.reason,
            details=payload.details,
        )
    except PrivacyError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/me/privacy-requests")
def get_privacy_requests_endpoint(
    kind: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Query user privacy requests (`CAP-032`)."""
    from app.services.privacy import privacy_service
    return privacy_service.get_my_privacy_requests(
        actor=actor,
        kind=kind,
        status=status,
        page=page,
        page_size=page_size,
    )


class SupportTicketCreatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject: str = Field(..., min_length=3, max_length=255, description="Ticket mavzusi")
    body: str = Field(..., min_length=5, max_length=4000, description="Dastlabki murojaat matni")
    category: str = Field(default="GENERAL", description="Kategoriya")
    priority: str = Field(default="NORMAL", description="Muhimlik darajasi")
    file_id: str | None = Field(default=None, description="Ilova qilingan fayl UUID")


class SupportMessageCreatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    body: str = Field(..., min_length=1, max_length=4000, description="Javob xabari matni")
    file_id: str | None = Field(default=None, description="Ilova qilingan fayl UUID")
    internal: bool = Field(default=False, description="Ichki operator qaydi (faqat xodimlar uchun)")


@router.get("/me/support-tickets")
def get_my_support_tickets_endpoint(
    status: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-063 (`GET /api/v1/me/support-tickets`): List support tickets for authenticated user (`CAP-033`, `AC-032`)."""
    from app.services.support_tickets import support_tickets_service
    return support_tickets_service.get_my_tickets(
        actor=actor,
        status=status,
        category=category,
        page=page,
        page_size=page_size,
    )


@router.post("/me/support-tickets", status_code=201)
def create_support_ticket_endpoint(
    payload: SupportTicketCreatePayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Create a new support ticket with initial message (`CAP-033`, `AC-032`)."""
    from app.services.support_tickets import SupportTicketError, support_tickets_service
    try:
        return support_tickets_service.create_ticket(
            actor=actor,
            subject=payload.subject,
            body=payload.body,
            category=payload.category,
            priority=payload.priority,
            file_id=payload.file_id,
        )
    except SupportTicketError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.post("/support-tickets/{id}/messages", status_code=201)
def post_support_message_endpoint(
    id: UUID,
    payload: SupportMessageCreatePayload,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-064 (`POST /api/v1/support-tickets/{id}/messages`): Post message to ticket thread (`CAP-033`, `AC-032`)."""
    from app.services.support_tickets import SupportTicketError, support_tickets_service
    try:
        return support_tickets_service.post_message(
            actor=actor,
            ticket_id=str(id),
            body=payload.body,
            file_id=payload.file_id,
            internal=payload.internal,
        )
    except SupportTicketError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/support-tickets/{id}/messages")
def get_support_messages_endpoint(
    id: UUID,
    page: int = 1,
    page_size: int = 50,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Get conversation thread for support ticket (`CAP-033`, `AC-032`)."""
    from app.services.support_tickets import SupportTicketError, support_tickets_service
    try:
        return support_tickets_service.get_ticket_messages(
            actor=actor,
            ticket_id=str(id),
            page=page,
            page_size=page_size,
        )
    except SupportTicketError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


class SaveOpportunityPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    opportunity_id: UUID
    candidate_id: UUID | None = None
    toggle: bool | None = False


@router.post("/saved-opportunities")
def save_opportunity_endpoint(
    payload: SaveOpportunityPayload,
    actor: ActorContext = Depends(require_actor_context),
) -> Response:
    """Save an opportunity for candidate, with idempotency or toggle (`API-004`, `CAP-006`)."""
    from app.services.saved_opportunities import (
        SavedOpportunityError,
        saved_opportunities_service,
    )
    try:
        data, status_code = saved_opportunities_service.save_opportunity(
            actor=actor,
            opportunity_id=str(payload.opportunity_id),
            candidate_id=str(payload.candidate_id) if payload.candidate_id else None,
            toggle=bool(payload.toggle),
        )
        return JSONResponse(status_code=status_code, content=data)
    except SavedOpportunityError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/me/saved-opportunities")
def get_saved_opportunities_endpoint(
    page: int = 1,
    page_size: int = 20,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """List candidate's saved opportunities with preserved status (`API-037`, `CAP-006`)."""
    from app.services.saved_opportunities import (
        SavedOpportunityError,
        saved_opportunities_service,
    )
    try:
        return saved_opportunities_service.get_my_saved_opportunities(
            actor=actor,
            page=page,
            page_size=page_size,
        )
    except SavedOpportunityError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.delete("/me/saved-opportunities/{id}", status_code=204)
def delete_saved_opportunity_endpoint(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> Response:
    """Unsave an opportunity with idempotent repeat 204 (`API-038`, `CAP-006`)."""
    from app.services.saved_opportunities import (
        SavedOpportunityError,
        saved_opportunities_service,
    )
    try:
        saved_opportunities_service.delete_saved_opportunity(
            actor=actor,
            identifier=str(id),
        )
        return Response(status_code=204)
    except SavedOpportunityError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.post("/operator/refunds/{id}/approve")
def approve_refund(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    from uuid import UUID
    return billing_service.approve_refund(str(id),actor)


# -------------------------------------------------------------------------
# Candidate Applications & Reapply System (API-006, API-029, API-039, API-040, API-041, API-044 / CAP-007)
# -------------------------------------------------------------------------

@router.post("/opportunities/{id}/applications", status_code=201)
def submit_opportunity_application_endpoint(
    id: UUID,
    payload: dict[str, Any] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Submit initial candidate application with snapshot and schedule evaluation (API-006 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.submit_application(
            actor=actor,
            opportunity_id=str(id),
            idempotency_key=idempotency_key,
            enrollment_id=payload.get("enrollment_id"),
            proposed_slots=payload.get("proposed_slots"),
            note=payload.get("note"),
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/me/applications/summary")
def get_my_applications_summary_endpoint(
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve candidate application summary metrics (API-029 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.get_applications_summary(actor=actor)
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/me/applications")
def list_my_applications_endpoint(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    after: str | None = Query(default=None),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """List candidate's own applications with keyset cursor pagination (API-039 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.list_my_applications(
            actor=actor,
            status=status,
            limit=limit,
            after=after,
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/me/applications/{id}/reapply", status_code=201)
def reapply_application_endpoint(
    id: UUID,
    payload: dict[str, Any] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Reapply to an existing application enforcing 24h cooldown and 3/30d limit (API-040 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.reapply_application(
            actor=actor,
            application_id=str(id),
            idempotency_key=idempotency_key,
            reason=payload.get("reason"),
            proposed_slots=payload.get("proposed_slots"),
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/me/applications/{id}")
def get_my_application_detail_endpoint(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve application detail with full attempt history and timeline events (API-041 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.get_application_detail(
            actor=actor,
            application_id=str(id),
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/me/applications/{id}/withdraw")
def withdraw_my_application_endpoint(
    id: UUID,
    payload: dict[str, Any] = Body(default={}),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Withdraw application and release reserved capacity if occupied (API-044 / CAP-007)."""
    from app.services.candidate_applications import (
        ApplicationError,
        candidate_application_service,
    )
    try:
        return candidate_application_service.withdraw_application(
            actor=actor,
            application_id=str(id),
            reason=payload.get("reason"),
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/organizations/{org}/dashboard")
def api_068_get_organization_dashboard(
    org: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve organization HR analytics dashboard (`API-068` / `CAP-015`)."""
    from app.services.org_dashboard import org_dashboard_service
    from app.services.governance import GovernanceError
    try:
        return org_dashboard_service.get_dashboard_api_068(
            actor=actor,
            organization_id=str(org),
        )
    except GovernanceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/organizations/{org}/entitlements", status_code=200)
def api_070_get_organization_entitlements(
    org: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve organization service entitlement, quota, and concurrent limit (`API-070` / `CAP-025`, `CAP-029`)."""
    from app.services.governance import GovernanceError
    try:
        return billing_service.get_organization_entitlements(
            actor=actor,
            organization_id=str(org),
        )
    except GovernanceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/organizations/{org}/billing", status_code=200)
def api_093_get_organization_billing_overview(
    org: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Retrieve organization billing overview, plan, recent orders, and invoices (`API-093` / `CAP-026`, `CAP-029`)."""
    from app.services.governance import GovernanceError
    try:
        return billing_service.get_organization_billing_overview(
            actor=actor,
            organization_id=str(org),
        )
    except GovernanceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/organizations/{id}/opportunities")
def api_009_get_organization_opportunities(
    id: UUID,
    limit: int = Query(default=20, ge=1, le=50),
    after: str | None = None,
) -> dict[str, Any]:
    """Retrieve public PUBLISHED opportunities for an organization (`API-009` / `CAP-001`)."""
    from app.services.org_dashboard import org_dashboard_service
    from app.services.governance import GovernanceError
    try:
        return org_dashboard_service.get_public_opportunities_api_009(
            organization_id=str(id),
            limit=limit,
            after=after,
        )
    except GovernanceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/organizations/{id}/rating-summary")
def api_010_get_organization_rating_summary(
    id: UUID,
) -> dict[str, Any]:
    """Retrieve public rating aggregate summary for an organization (`API-010` / `CAP-027`)."""
    from app.services.org_dashboard import org_dashboard_service
    from app.services.governance import GovernanceError
    try:
        return org_dashboard_service.get_public_rating_summary_api_010(
            organization_id=str(id),
        )
    except GovernanceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/onboarding/options", status_code=200)
def api_002_onboarding_options() -> dict[str, Any]:
    """API-002: Public onboarding options and persona tracks (`CAP-002`, `AUTH_SELF`)."""
    from app.services.discovery_and_catalog import discovery_and_catalog_service
    return discovery_and_catalog_service.get_onboarding_options_api_002()


@router.get("/services/public", status_code=200)
def api_011_public_services() -> dict[str, Any]:
    """API-011: Public service offerings catalog (`CAP-039`, `PUBLIC_INFO`)."""
    from app.services.discovery_and_catalog import discovery_and_catalog_service
    return discovery_and_catalog_service.get_public_services_api_011()


@router.get("/prices/public", status_code=200)
def api_012_public_prices() -> dict[str, Any]:
    """API-012: Public pricing rules, listing duration, and refund policy (`CAP-039`, `PUBLIC_INFO`)."""
    from app.services.discovery_and_catalog import discovery_and_catalog_service
    return discovery_and_catalog_service.get_public_prices_api_012()


@router.get("/help/{document}", status_code=200)
def api_013_public_help_document(document: str) -> dict[str, Any]:
    """API-013: Public versioned help & FAQ CMS documentation (`CAP-039`, `PUBLIC_INFO`)."""
    from app.services.discovery_and_catalog import discovery_and_catalog_service
    return discovery_and_catalog_service.get_public_help_api_013(document=document)


@router.get("/policies/{document}", status_code=200)
def api_014_public_policy_document(document: str) -> dict[str, Any]:
    """API-014: Public versioned legal policies CMS documentation (`CAP-039`, `PUBLIC_INFO`)."""
    from app.services.discovery_and_catalog import discovery_and_catalog_service
    return discovery_and_catalog_service.get_public_policies_api_014(document=document)


class ApplicationTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_status: str = Field(..., description="Target status for application")
    reason: str | None = Field(default=None, max_length=1000)


@router.post("/applications/{id}/transition", status_code=200)
def api_083_transition_application(
    id: UUID,
    payload: ApplicationTransitionRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-083: Transition application status according to state machine (`CAP-008`, `APPLICATION_HR`)."""
    try:
        return application_hr_service.transition_application_status(
            actor=actor,
            application_id=str(id),
            to_status=payload.to_status,
            reason=payload.reason,
        )
    except ApplicationHRError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/applications/{id}/hr", status_code=200)
def api_084_get_application_hr_detail(
    id: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-084: Retrieve applicant attempt snapshot and event timeline (`CAP-008`, `APPLICATION_HR`)."""
    try:
        return application_hr_service.get_application_hr_detail(
            actor=actor,
            application_id=str(id),
        )
    except ApplicationHRError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


class SubmitWorkplaceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(APPROVED|CHANGES_REQUESTED|REJECTED)$")
    comment: str | None = Field(default=None, max_length=2000)


@router.get("/me/mentor-review-queue", status_code=200)
def api_090_list_mentor_review_queue(
    limit: int = 20,
    cursor: str | None = None,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-090: Mentor review queue containing only own accepted assignments (`CAP-023`, `LOG_MENTOR`)."""
    try:
        return workplace_review_service.list_mentor_review_queue(
            actor=actor,
            limit=limit,
            cursor=cursor,
        )
    except WorkplaceReviewError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/log-revisions/{revision}/workplace", status_code=200)
def api_091_get_workplace_log_revision(
    revision: UUID,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-091: Workplace view of daily log revision (`CAP-023`, `LOG_MENTOR`)."""
    try:
        return workplace_review_service.get_workplace_log_revision_detail(
            revision_id=str(revision),
            actor=actor,
        )
    except WorkplaceReviewError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/log-revisions/{revision}/workplace-reviews", status_code=200)
def api_092_submit_workplace_review(
    revision: UUID,
    payload: SubmitWorkplaceReviewRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-092: Workplace review decision (`CAP-023`, `LOG_MENTOR`)."""
    try:
        return workplace_review_service.submit_workplace_review(
            revision_id=str(revision),
            decision=payload.decision,
            comment=payload.comment,
            actor=actor,
        )
    except WorkplaceReviewError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


class CreateModerationCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_ -]+$")
    reason: str = Field(..., min_length=10, max_length=4000)
    opportunity_id: UUID | None = None
    organization_id: UUID | None = None
    rating_id: UUID | None = None
    file_id: UUID | None = None
    severity: str = Field(default="MEDIUM", pattern="^(?i:(LOW|MEDIUM|HIGH|CRITICAL))$")


@router.post("/moderation-cases", status_code=201)
def api_007_create_moderation_case(
    payload: CreateModerationCaseRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-007: Report abuse / create moderation case (`CAP-032`, `REPORT_ABUSE`, `DB-078`)."""
    try:
        return moderation_cases_service.create_case(
            actor=actor,
            category=payload.category,
            reason=payload.reason,
            opportunity_id=payload.opportunity_id,
            organization_id=payload.organization_id,
            rating_id=payload.rating_id,
            file_id=payload.file_id,
            severity=payload.severity,
        )
    except ModerationCaseError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


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
