"""Interviews and Offers System (API-042, API-043, API-085, API-086 / CAP-009, CAP-011 / DB-044, DB-045, DB-046).

Implements canonical contracts:
- `API-042`: `POST /api/v1/interviews/{id}/responses` (Candidate or HR response to scheduled interview: ACCEPTED, DECLINED, RESCHEDULE_REQUESTED, COMPLETED).
- `API-043`: `POST /api/v1/offers/{id}/respond` (Candidate responds to offer: ACCEPT or DECLINE. Enforces atomic opportunity capacity lock with `with_for_update()`; prevents over-allocation race conditions).
- `API-085`: Helper / canonical route for creating interview for application (`POST /api/v1/applications/{id}/interviews`).
- `API-086`: Helper / canonical route for issuing offer for application (`POST /api/v1/applications/{id}/offers`).

Invariants:
- Main/master is strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6.
- Zero direct database access to production `pg_live`. All tests run on isolated PostgreSQL.
- Strict IDOR isolation: candidate can only view/respond to their own application's interviews and offers.
- Concurrency control: row-level locking on `opportunities` table ensures `occupied_count < capacity` is respected under parallel accept calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select

from app.api.dependencies import ActorContext, candidate_id_for, require_org
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, read_snapshot, table, transaction
from app.services.authority import account_authority
from app.services.placements import insert_row


class InterviewOfferError(Exception):
    """Base exception for interview and offer operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class InterviewNotFoundError(InterviewOfferError):
    def __init__(self, message: str = "Suhbat topilmadi") -> None:
        super().__init__(code="INTERVIEW_NOT_FOUND", message=message, status_code=404)


class OfferNotFoundError(InterviewOfferError):
    def __init__(self, message: str = "Taklif topilmadi") -> None:
        super().__init__(code="OFFER_NOT_FOUND", message=message, status_code=404)


class InterviewOfferForbiddenError(InterviewOfferError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Ruxsat etilmagan amal") -> None:
        super().__init__(code=code, message=message, status_code=403)


class InterviewOfferConflictError(InterviewOfferError):
    def __init__(self, code: str = "CONFLICT", message: str = "Holat mos kelmaydi") -> None:
        super().__init__(code=code, message=message, status_code=409)


class InterviewOfferValidationError(InterviewOfferError):
    def __init__(self, code: str = "VALIDATION_ERROR", message: str = "Yaroqsiz ma'lumot") -> None:
        super().__init__(code=code, message=message, status_code=422)


def _to_utc_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def _validate_uuid(val: Any, field_name: str) -> str:
    try:
        return str(UUID(str(val)))
    except (ValueError, TypeError, AttributeError):
        raise InterviewOfferValidationError(
            code=f"INVALID_{field_name.upper()}",
            message=f"Yaroqsiz {field_name} UUID formati",
        )


class InterviewOfferService:
    """Service encapsulating interview scheduling & responses, and job offer issuing & responses."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _resolve_candidate_profile(self, conn: Any, actor: ActorContext) -> Optional[dict[str, Any]]:
        t_profiles = table("candidate_profiles")
        profile = conn.execute(
            select(t_profiles).where(t_profiles.c.user_id == actor.user_id)
        ).mappings().first()
        return dict(profile) if profile else None

    # -------------------------------------------------------------------------
    # API-085 Helper: Schedule Interview (POST /applications/{id}/interviews)
    # -------------------------------------------------------------------------
    def schedule_interview(
        self,
        actor: ActorContext,
        application_id: str,
        starts_at: datetime | str,
        ends_at: datetime | str,
        mode: str = "ONLINE",
        location_or_link: Optional[str] = None,
        timezone_str: str = "Asia/Tashkent",
    ) -> dict[str, Any]:
        """Schedule an interview for an application (API-085 / CAP-009)."""
        app_uuid = _validate_uuid(application_id, "application_id")

        with transaction() as conn:
            account_authority(conn, actor)
            t_apps = table("applications")
            t_opp = table("opportunities")

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == app_uuid)
            ).mappings().first()
            if not app:
                raise InterviewOfferValidationError(code="APPLICATION_NOT_FOUND", message="Ariza topilmadi")

            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            if not opp:
                raise InterviewOfferValidationError(code="OPPORTUNITY_NOT_FOUND", message="E'lon topilmadi")

            # Verify caller is an active member of the hosting organization (OWNER, HR, HOST_COORDINATOR)
            t_memberships = table("org_memberships")
            membership = conn.execute(
                select(t_memberships).where(
                    t_memberships.c.organization_id == opp["organization_id"],
                    t_memberships.c.user_id == actor.user_id,
                    t_memberships.c.status == "ACTIVE",
                    t_memberships.c.revoked_at.is_(None),
                )
            ).mappings().first()

            if not membership:
                raise InterviewOfferForbiddenError(
                    code="ORG_MEMBERSHIP_REQUIRED",
                    message="Suhbat belgilash uchun tashkilot a'zosi bo'lishingiz kerak",
                )

            # Parse datetimes
            s_dt = datetime.fromisoformat(starts_at) if isinstance(starts_at, str) else starts_at
            e_dt = datetime.fromisoformat(ends_at) if isinstance(ends_at, str) else ends_at
            if e_dt <= s_dt:
                raise InterviewOfferValidationError(
                    code="INVALID_INTERVIEW_TIME",
                    message="Tugash vaqti boshlanish vaqtidan keyin bo'lishi shart",
                )

            now_dt = now()
            interview_id = str(uuid4())
            insert_row(
                conn,
                "interviews",
                id=interview_id,
                application_id=app_uuid,
                organizer_membership_id=membership["id"],
                starts_at=s_dt,
                ends_at=e_dt,
                timezone=timezone_str,
                mode=mode.upper(),
                location_or_link=location_or_link,
                status="SCHEDULED",
                version=1,
                created_at=now_dt,
                updated_at=now_dt,
            )

            # Update application status to INTERVIEW_SCHEDULED
            conn.execute(
                t_apps.update()
                .where(t_apps.c.id == app_uuid)
                .values(
                    status="INTERVIEW_SCHEDULED",
                    version=app["version"] + 1,
                    updated_at=now_dt,
                )
            )

            # Record application event
            insert_row(
                conn,
                "application_events",
                id=str(uuid4()),
                application_id=app_uuid,
                attempt_id=app["current_attempt_id"],
                actor_id=actor.user_id,
                from_status=app["status"],
                to_status="INTERVIEW_SCHEDULED",
                reason="INTERVIEW_SCHEDULED",
                occurred_at=now_dt,
            )

            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="INTERVIEW_SCHEDULED",
                entity_type="interview",
                entity_id=interview_id,
                metadata={"application_id": app_uuid, "mode": mode},
            )

            return {
                "contract_id": "API-085",
                "id": interview_id,
                "application_id": app_uuid,
                "status": "SCHEDULED",
                "starts_at": _to_utc_iso(s_dt),
                "ends_at": _to_utc_iso(e_dt),
                "mode": mode.upper(),
                "timezone": timezone_str,
                "location_or_link": location_or_link,
            }

    # -------------------------------------------------------------------------
    # API-042: Candidate / HR responds to interview (POST /interviews/{id}/responses)
    # -------------------------------------------------------------------------
    def respond_to_interview(
        self,
        actor: ActorContext,
        interview_id: str,
        response: str,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Candidate or HR responds to a scheduled interview (API-042 / CAP-009)."""
        int_uuid = _validate_uuid(interview_id, "interview_id")
        resp_clean = str(response).strip().upper()
        allowed_responses = ("ACCEPTED", "DECLINED", "RESCHEDULE_REQUESTED", "COMPLETED", "NO_SHOW")
        if resp_clean not in allowed_responses:
            raise InterviewOfferValidationError(
                code="INVALID_RESPONSE",
                message=f"Yaroqsiz javob. Ruxsat etilgan: {', '.join(allowed_responses)}",
            )

        with transaction() as conn:
            account_authority(conn, actor)
            t_interviews = table("interviews")
            t_apps = table("applications")
            t_opp = table("opportunities")
            t_memberships = table("org_memberships")

            # Lock interview row
            interview = conn.execute(
                select(t_interviews).where(t_interviews.c.id == int_uuid).with_for_update()
            ).mappings().first()

            if not interview:
                raise InterviewNotFoundError(message="Suhbat topilmadi")

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == interview["application_id"])
            ).mappings().first()
            if not app:
                raise InterviewNotFoundError(message="Suhbatga tegishli ariza topilmadi")

            # Check party-to-interview authorization (IDOR protection)
            cand_profile = self._resolve_candidate_profile(conn, actor)
            is_candidate = cand_profile and str(app["candidate_id"]) == str(cand_profile["id"])

            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            org_membership = None
            if opp:
                org_membership = conn.execute(
                    select(t_memberships).where(
                        t_memberships.c.organization_id == opp["organization_id"],
                        t_memberships.c.user_id == actor.user_id,
                        t_memberships.c.status == "ACTIVE",
                        t_memberships.c.revoked_at.is_(None),
                    )
                ).mappings().first()

            if not is_candidate and not org_membership:
                # Neither the candidate nor an org staff member -> uniform 404 to prevent IDOR probing
                raise InterviewNotFoundError(message="Suhbat topilmadi")

            # Candidate restrictions
            if is_candidate and resp_clean in ("COMPLETED", "NO_SHOW"):
                raise InterviewOfferForbiddenError(
                    code="HOST_RESPONSE_ONLY",
                    message="COMPLETED yoki NO_SHOW faqat tashkilot HR xodimi tomonidan belgilanadi",
                )

            # State check: cannot reschedule or accept an already completed or cancelled interview
            if interview["status"] in ("COMPLETED", "CANCELLED"):
                raise InterviewOfferConflictError(
                    code="INTERVIEW_ALREADY_FINALIZED",
                    message=f"Suhbat yakunlangan ({interview['status']}). Unga qayta javob berib bo'lmaydi",
                )

            now_dt = now()
            # Upsert interview_responses (unique interview_id, user_id)
            t_responses = table("interview_responses")
            existing_resp = conn.execute(
                select(t_responses).where(
                    t_responses.c.interview_id == int_uuid,
                    t_responses.c.user_id == actor.user_id,
                )
            ).mappings().first()

            if existing_resp:
                conn.execute(
                    t_responses.update()
                    .where(t_responses.c.id == existing_resp["id"])
                    .values(
                        response=resp_clean,
                        responded_at=now_dt,
                        updated_at=now_dt,
                    )
                )
            else:
                insert_row(
                    conn,
                    "interview_responses",
                    id=str(uuid4()),
                    interview_id=int_uuid,
                    user_id=actor.user_id,
                    response=resp_clean,
                    responded_at=now_dt,
                    created_at=now_dt,
                    updated_at=now_dt,
                )

            # Determine new interview status
            new_interview_status = interview["status"]
            if resp_clean == "ACCEPTED":
                new_interview_status = "CONFIRMED"
            elif resp_clean == "DECLINED":
                new_interview_status = "CANCELLED"
            elif resp_clean == "RESCHEDULE_REQUESTED":
                new_interview_status = "RESCHEDULE_REQUESTED"
            elif resp_clean == "COMPLETED":
                new_interview_status = "COMPLETED"
            elif resp_clean == "NO_SHOW":
                new_interview_status = "NO_SHOW"

            conn.execute(
                t_interviews.update()
                .where(t_interviews.c.id == int_uuid)
                .values(
                    status=new_interview_status,
                    version=interview["version"] + 1,
                    updated_at=now_dt,
                )
            )

            # Append audit log
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="INTERVIEW_RESPONSE_RECORDED",
                entity_type="interview",
                entity_id=int_uuid,
                metadata={
                    "response": resp_clean,
                    "new_status": new_interview_status,
                    "is_candidate": bool(is_candidate),
                    "note": note,
                },
            )

            return {
                "contract_id": "API-042",
                "interview_id": int_uuid,
                "response": resp_clean,
                "status": new_interview_status,
                "version": interview["version"] + 1,
                "updated_at": _to_utc_iso(now_dt),
                "message": f"Suhbat javobi qayd etildi: {resp_clean}",
            }

    # -------------------------------------------------------------------------
    # API-086 Helper: Issue Job Offer (POST /applications/{id}/offers)
    # -------------------------------------------------------------------------
    def issue_offer(
        self,
        actor: ActorContext,
        application_id: str,
        expires_at: Optional[datetime | str] = None,
        terms_snapshot: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Issue an official job offer for an application (API-086 / CAP-011)."""
        app_uuid = _validate_uuid(application_id, "application_id")
        idem_key = str(idempotency_key or uuid4())

        with transaction() as conn:
            account_authority(conn, actor)
            t_apps = table("applications")
            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")
            t_attempts = table("application_attempts")
            t_offers = table("offers")

            # Check idempotency
            existing_offer = conn.execute(
                select(t_offers).where(t_offers.c.idempotency_key == idem_key)
            ).mappings().first()
            if existing_offer:
                return {
                    "contract_id": "API-086",
                    "id": str(existing_offer["id"]),
                    "application_id": str(existing_offer["application_id"]),
                    "status": existing_offer["status"],
                    "expires_at": _to_utc_iso(existing_offer["expires_at"]),
                    "terms_snapshot": existing_offer["terms_snapshot"],
                }

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == app_uuid)
            ).mappings().first()
            if not app:
                raise InterviewOfferValidationError(code="APPLICATION_NOT_FOUND", message="Ariza topilmadi")

            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            if not opp:
                raise InterviewOfferValidationError(code="OPPORTUNITY_NOT_FOUND", message="E'lon topilmadi")

            # Caller must be authorized member of hosting organization
            t_memberships = table("org_memberships")
            membership = conn.execute(
                select(t_memberships).where(
                    t_memberships.c.organization_id == opp["organization_id"],
                    t_memberships.c.user_id == actor.user_id,
                    t_memberships.c.status == "ACTIVE",
                    t_memberships.c.revoked_at.is_(None),
                )
            ).mappings().first()

            if not membership:
                raise InterviewOfferForbiddenError(
                    code="ORG_MEMBERSHIP_REQUIRED",
                    message="Taklif berish uchun tashkilot a'zosi bo'lishingiz kerak",
                )

            # Latest attempt
            attempt = conn.execute(
                select(t_attempts)
                .where(t_attempts.c.application_id == app_uuid)
                .order_by(t_attempts.c.attempt_no.desc())
            ).mappings().first()
            if not attempt:
                raise InterviewOfferValidationError(code="ATTEMPT_REQUIRED", message="Ariza urinishi topilmadi")

            rev = conn.execute(
                select(t_rev).where(t_rev.c.id == attempt["revision_id"])
            ).mappings().first()

            now_dt = now()
            exp_dt = (
                datetime.fromisoformat(expires_at)
                if isinstance(expires_at, str)
                else (expires_at or (now_dt + timedelta(days=7)))
            )

            # Snapshot terms
            snapshot = terms_snapshot or {
                "revision_id": str(rev["id"]),
                "title": rev["title"],
                "work_mode": rev["work_mode"],
                "contract_type": rev["contract_type"],
                "salary_min": float(rev["salary_min"]) if rev.get("salary_min") else None,
                "issued_at": now_dt.isoformat(),
            }

            offer_id = str(uuid4())
            insert_row(
                conn,
                "offers",
                id=offer_id,
                application_id=app_uuid,
                attempt_id=attempt["id"],
                revision_id=rev["id"],
                issuer_membership_id=membership["id"],
                terms_snapshot=snapshot,
                status="OFFERED",
                expires_at=exp_dt,
                accepted_at=None,
                idempotency_key=idem_key,
                created_at=now_dt,
                updated_at=now_dt,
            )

            # Update application status to OFFERED
            conn.execute(
                t_apps.update()
                .where(t_apps.c.id == app_uuid)
                .values(
                    status="OFFERED",
                    version=app["version"] + 1,
                    updated_at=now_dt,
                )
            )

            # Record event
            insert_row(
                conn,
                "application_events",
                id=str(uuid4()),
                application_id=app_uuid,
                attempt_id=attempt["id"],
                actor_id=actor.user_id,
                from_status=app["status"],
                to_status="OFFERED",
                reason="OFFER_ISSUED",
                occurred_at=now_dt,
            )

            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="OFFER_ISSUED",
                entity_type="offer",
                entity_id=offer_id,
                metadata={"application_id": app_uuid, "expires_at": exp_dt.isoformat()},
            )

            return {
                "contract_id": "API-086",
                "id": offer_id,
                "application_id": app_uuid,
                "status": "OFFERED",
                "expires_at": _to_utc_iso(exp_dt),
                "terms_snapshot": snapshot,
            }

    # -------------------------------------------------------------------------
    # API-043: Candidate responds to offer (POST /offers/{id}/respond)
    # -------------------------------------------------------------------------
    def respond_to_offer(
        self,
        actor: ActorContext,
        offer_id: str,
        response: str,
        idempotency_key: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Candidate responds to job offer: ACCEPT or DECLINE (API-043 / CAP-011).

        CRITICAL SPEC INVARIANT:
        'Row lock capacity; bir o'rin uchun ikki parallel acceptdan biri 409; expiry va version tekshiriladi.'
        """
        off_uuid = _validate_uuid(offer_id, "offer_id")
        resp_clean = str(response).strip().upper()
        if resp_clean not in ("ACCEPT", "DECLINE"):
            raise InterviewOfferValidationError(
                code="INVALID_RESPONSE",
                message="Yaroqsiz javob. Faqat 'ACCEPT' yoki 'DECLINE' qabul qilinadi",
            )

        with transaction() as conn:
            account_authority(conn, actor)
            t_offers = table("offers")
            t_apps = table("applications")
            t_opp = table("opportunities")

            # 1. Lock the offer row
            offer = conn.execute(
                select(t_offers).where(t_offers.c.id == off_uuid).with_for_update()
            ).mappings().first()

            if not offer:
                raise OfferNotFoundError(message="Taklif topilmadi")

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == offer["application_id"])
            ).mappings().first()
            if not app:
                raise OfferNotFoundError(message="Taklifga tegishli ariza topilmadi")

            # 2. Strict IDOR protection: only the candidate owning this application can respond
            cand_profile = self._resolve_candidate_profile(conn, actor)
            if not cand_profile or str(app["candidate_id"]) != str(cand_profile["id"]):
                raise OfferNotFoundError(message="Taklif topilmadi")

            # 3. Idempotent repeat checks
            if offer["status"] == "ACCEPTED":
                if resp_clean == "ACCEPT":
                    return {
                        "contract_id": "API-043",
                        "id": off_uuid,
                        "status": "ACCEPTED",
                        "accepted_at": _to_utc_iso(offer["accepted_at"]),
                        "message": "Taklif allaqachon qabul qilingan",
                    }
                else:
                    raise InterviewOfferConflictError(
                        code="OFFER_ALREADY_ACCEPTED",
                        message="Qabul qilingan taklifni rad etib bo'lmaydi",
                    )

            if offer["status"] == "DECLINED":
                if resp_clean == "DECLINE":
                    return {
                        "contract_id": "API-043",
                        "id": off_uuid,
                        "status": "DECLINED",
                        "message": "Taklif allaqachon rad etilgan",
                    }
                else:
                    raise InterviewOfferConflictError(
                        code="OFFER_NOT_ACTIVE",
                        message="Rad etilgan taklifni qayta qabul qilib bo'lmaydi",
                    )

            if offer["status"] in ("EXPIRED", "REVOKED"):
                raise InterviewOfferConflictError(
                    code="OFFER_NOT_ACTIVE",
                    message=f"Taklif faol emas ({offer['status']})",
                )

            # 4. Expiry validation (server-side check)
            now_dt = now()
            exp_time = offer["expires_at"]
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=timezone.utc)
            curr_utc = now_dt if now_dt.tzinfo else now_dt.replace(tzinfo=timezone.utc)

            if curr_utc >= exp_time:
                # Mark as EXPIRED
                conn.execute(
                    t_offers.update()
                    .where(t_offers.c.id == off_uuid)
                    .values(status="EXPIRED", updated_at=now_dt)
                )
                raise InterviewOfferConflictError(
                    code="OFFER_EXPIRED",
                    message="Taklif muddati tugagan (CAP-011)",
                )

            # 5. Process decision
            if resp_clean == "ACCEPT":
                # CRITICAL: Row lock capacity on opportunities table!
                opp = conn.execute(
                    select(t_opp)
                    .where(t_opp.c.id == app["opportunity_id"])
                    .with_for_update()
                ).mappings().first()

                if not opp:
                    raise InterviewOfferConflictError(code="OPPORTUNITY_NOT_FOUND", message="E'lon topilmadi")

                capacity = opp["capacity"]
                occupied_count = opp["occupied_count"]

                if occupied_count >= capacity:
                    raise InterviewOfferConflictError(
                        code="CAPACITY_EXHAUSTED",
                        message="E'londa bo'sh o'rinlar qolmagan (bir o'rin uchun parallel accept to'siladi)",
                    )

                # Atomically increment occupied_count
                conn.execute(
                    t_opp.update()
                    .where(t_opp.c.id == opp["id"])
                    .values(
                        occupied_count=occupied_count + 1,
                        updated_at=now_dt,
                    )
                )

                # Update offer to ACCEPTED
                conn.execute(
                    t_offers.update()
                    .where(t_offers.c.id == off_uuid)
                    .values(
                        status="ACCEPTED",
                        accepted_at=now_dt,
                        updated_at=now_dt,
                    )
                )

                # Update application to ACCEPTED
                conn.execute(
                    t_apps.update()
                    .where(t_apps.c.id == app["id"])
                    .values(
                        status="ACCEPTED",
                        occupied_at=now_dt,
                        version=app["version"] + 1,
                        updated_at=now_dt,
                    )
                )

                # If job/part-time opportunity (non-internship), create job_engagements for start confirmation (DB-047 / API-046)
                engagement_id = None
                if opp.get("kind") != "INTERNSHIP":
                    t_je = table("job_engagements")
                    existing_je = conn.execute(
                        select(t_je).where(t_je.c.offer_id == off_uuid)
                    ).mappings().first()
                    if not existing_je:
                        engagement_id = str(uuid4())
                        insert_row(
                            conn,
                            "job_engagements",
                            id=engagement_id,
                            application_id=app["id"],
                            offer_id=off_uuid,
                            status="PENDING_START_CONFIRMATION",
                            start_date=now_dt.date(),
                            end_date=None,
                            terms_snapshot=offer.get("terms_snapshot") or {},
                            confirmed_started_at=None,
                            created_at=now_dt,
                            updated_at=now_dt,
                        )
                    else:
                        engagement_id = str(existing_je["id"])

                # Record event
                insert_row(
                    conn,
                    "application_events",
                    id=str(uuid4()),
                    application_id=app["id"],
                    attempt_id=offer["attempt_id"],
                    actor_id=actor.user_id,
                    from_status=app["status"],
                    to_status="ACCEPTED",
                    reason="OFFER_ACCEPTED",
                    occurred_at=now_dt,
                )

                self.audit_store.append_audit_event(
                    actor_id=actor.user_id,
                    action="OFFER_ACCEPTED",
                    entity_type="offer",
                    entity_id=off_uuid,
                    metadata={
                        "opportunity_id": str(opp["id"]),
                        "occupied_count": occupied_count + 1,
                        "capacity": capacity,
                    },
                )

                res = {
                    "contract_id": "API-043",
                    "id": off_uuid,
                    "status": "ACCEPTED",
                    "accepted_at": _to_utc_iso(now_dt),
                    "opportunity_id": str(opp["id"]),
                    "vacancies_remaining": max(0, capacity - (occupied_count + 1)),
                    "message": "Taklif muvaffaqiyatli qabul qilindi",
                }
                if engagement_id:
                    res["engagement_id"] = engagement_id
                return res

            else:  # DECLINE
                conn.execute(
                    t_offers.update()
                    .where(t_offers.c.id == off_uuid)
                    .values(
                        status="DECLINED",
                        updated_at=now_dt,
                    )
                )

                # Update application status
                conn.execute(
                    t_apps.update()
                    .where(t_apps.c.id == app["id"])
                    .values(
                        version=app["version"] + 1,
                        updated_at=now_dt,
                    )
                )

                # Record event
                insert_row(
                    conn,
                    "application_events",
                    id=str(uuid4()),
                    application_id=app["id"],
                    attempt_id=offer["attempt_id"],
                    actor_id=actor.user_id,
                    from_status=app["status"],
                    to_status="OFFER_DECLINED",
                    reason=note or "OFFER_DECLINED",
                    occurred_at=now_dt,
                )

                self.audit_store.append_audit_event(
                    actor_id=actor.user_id,
                    action="OFFER_DECLINED",
                    entity_type="offer",
                    entity_id=off_uuid,
                    metadata={"reason": note},
                )

                return {
                    "contract_id": "API-043",
                    "id": off_uuid,
                    "status": "DECLINED",
                    "updated_at": _to_utc_iso(now_dt),
                    "message": "Taklif rad etildi",
                }


interview_offer_service = InterviewOfferService()
