"""Candidate Applications & Reapply System (API-006, API-029, API-039, API-040, API-041, API-044 / CAP-007).

Implements canonical contracts:
- `API-006`: `POST /api/v1/opportunities/{id}/applications` (Initial application, eligibility check, schedule snapshot, attempt_no=1, Idempotency-Key).
- `API-029`: `GET /api/v1/me/applications/summary` (Candidate metrics: total applications, interviews, offers, rejected, withdrawn).
- `API-039`: `GET /api/v1/me/applications` (List candidate's applications, keyset pagination, status filter).
- `API-040`: `POST /api/v1/me/applications/{id}/reapply` (Reapply with 24h cooldown, 3 attempts per 30 days limit, new attempt snapshot).
- `API-041`: `GET /api/v1/me/applications/{id}` (Application details, full attempt history, status timeline events, interview/offer status).
- `API-044`: `POST /api/v1/me/applications/{id}/withdraw` (Withdraw application, release occupied capacity if reserved, append audit event).

Strict invariants:
- Zero mutations to frozen main (`764fb98496fa40857acb07844fd09fcafa99b7d6`).
- Zero direct database access to production `pg_live`.
- IDOR isolation: Candidates can only access and modify their own applications (`candidate_id == actor.candidate_id`).
- Keyset cursor pagination over `(created_at, id)` with ownership validation.
- Atomicity and race-condition prevention using row-level locking (`with_for_update`).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select

from app.api.dependencies import ActorContext, candidate_id_for, owns_candidate
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, read_snapshot, table, transaction
from app.services.authority import account_authority
from app.services.opportunities import OpportunityConstraintError, compensation_type_for
from app.services.placements import insert_row
from app.services.schedule import load_snapshot, local_today
from app.services.schedule_matching import ALGORITHM_VERSION, evaluate, window


class ApplicationError(Exception):
    """Base exception for application domain operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ApplicationNotFoundError(ApplicationError):
    def __init__(self, message: str = "Ariza topilmadi") -> None:
        super().__init__(code="APPLICATION_NOT_FOUND", message=message, status_code=404)


class ApplicationForbiddenError(ApplicationError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Ruxsat etilmagan amal") -> None:
        super().__init__(code=code, message=message, status_code=403)


class ApplicationConflictError(ApplicationError):
    def __init__(self, code: str = "CONFLICT", message: str = "Ariza holati mos kelmaydi") -> None:
        super().__init__(code=code, message=message, status_code=409)


class ApplicationRateLimitError(ApplicationError):
    def __init__(self, code: str = "RATE_LIMIT_EXCEEDED", message: str = "Cheklov oshirildi") -> None:
        super().__init__(code=code, message=message, status_code=429)


class ApplicationValidationError(ApplicationError):
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
        raise ApplicationValidationError(
            code=f"INVALID_{field_name.upper()}",
            message=f"Yaroqsiz {field_name} UUID formati",
        )


class CandidateApplicationService:
    """Service encapsulating candidate application submission, history, reapply, and withdrawal."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _resolve_candidate_profile(self, conn: Any, actor: ActorContext) -> dict[str, Any]:
        t_profiles = table("candidate_profiles")
        profile = conn.execute(
            select(t_profiles).where(t_profiles.c.user_id == actor.user_id)
        ).mappings().first()
        if not profile:
            raise ApplicationForbiddenError(
                code="CANDIDATE_PROFILE_REQUIRED",
                message="Ariza topshirish uchun nomzod profili talab qilinadi",
            )
        return dict(profile)

    def _build_profile_snapshot(self, conn: Any, candidate_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        """Create a minimal, immutable candidate profile snapshot (DB-042 rules)."""
        t_skills = table("candidate_skills")
        t_cat = table("skills")
        skill_rows = conn.execute(
            select(t_skills.c.skill_id, t_skills.c.level, t_cat.c.code, t_cat.c.name_uz)
            .join(t_cat, t_cat.c.id == t_skills.c.skill_id)
            .where(t_skills.c.candidate_id == candidate_id)
        ).mappings().all()

        skills = [
            {"skill_id": str(r["skill_id"]), "code": r["code"], "name_uz": r["name_uz"], "level": r["level"]}
            for r in skill_rows
        ]

        return {
            "headline": profile.get("headline"),
            "region": profile.get("region"),
            "experience_months": profile.get("experience_months", 0),
            "cv_file_id": str(profile["cv_file_id"]) if profile.get("cv_file_id") else None,
            "skills": skills,
            "captured_at": now().isoformat(),
        }

    def _evaluate_candidate_schedule(
        self, conn: Any, candidate_id: str, revision: dict[str, Any]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Evaluate candidate availability against opportunity revision shifts."""
        t_shifts = table("opportunity_shifts")
        shifts = list(
            conn.execute(
                select(t_shifts).where(t_shifts.c.revision_id == revision["id"])
            ).mappings()
        )
        if not shifts:
            return "UNKNOWN", []

        today = local_today()
        w_start, w_end = window(revision, today)
        snapshot = load_snapshot(candidate_id, w_start - timedelta(days=1), w_end + timedelta(days=1))
        eval_res = evaluate(
            revision,
            shifts,
            snapshot,
            today,
            revision.get("shift_match_mode") or "ALL_SHIFTS_IN_GROUP",
            30,
        )
        return eval_res.get("result", "UNKNOWN"), [dict(s) for s in shifts]

    # -------------------------------------------------------------------------
    # API-006: Submit initial application (POST /opportunities/{id}/applications)
    # -------------------------------------------------------------------------
    def submit_application(
        self,
        actor: ActorContext,
        opportunity_id: str,
        idempotency_key: str,
        enrollment_id: Optional[str] = None,
        proposed_slots: Optional[list[Any] | dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Submit initial application for candidate (API-006 / CAP-007)."""
        if not idempotency_key or not str(idempotency_key).strip():
            raise ApplicationValidationError(
                code="IDEMPOTENCY_KEY_REQUIRED",
                message="Idempotency-Key sarlavhasi majburiy",
            )
        idem_key = str(idempotency_key).strip()
        opp_uuid = _validate_uuid(opportunity_id, "opportunity_id")

        with transaction() as conn:
            account_authority(conn, actor)
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            # Check Idempotency-Key first
            t_attempts = table("application_attempts")
            existing_attempt = conn.execute(
                select(t_attempts).where(t_attempts.c.idempotency_key == idem_key)
            ).mappings().first()

            if existing_attempt:
                t_apps = table("applications")
                app_row = conn.execute(
                    select(t_apps).where(t_apps.c.id == existing_attempt["application_id"])
                ).mappings().first()
                if app_row and str(app_row["candidate_id"]) == candidate_id:
                    return self._render_application_response(conn, app_row, existing_attempt)
                raise ApplicationConflictError(
                    code="IDEMPOTENCY_KEY_REUSED",
                    message="Idempotency-Key boshqa ariza uchun ishlatilgan",
                )

            # Check Opportunity status
            t_opp = table("opportunities")
            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == opp_uuid)
            ).mappings().first()
            if not opp:
                raise ApplicationNotFoundError(message="E'lon topilmadi")

            if opp["status"] != "PUBLISHED":
                raise ApplicationConflictError(
                    code="OPPORTUNITY_NOT_ACTIVE",
                    message="Faqat nashr qilingan e'longa ariza topshirish mumkin",
                )

            now_dt = now()
            if opp["expires_at"] and opp["expires_at"] <= now_dt:
                raise ApplicationConflictError(
                    code="OPPORTUNITY_EXPIRED",
                    message="E'lon muddati o'tgan",
                )

            # Fetch active revision
            t_rev = table("opportunity_revisions")
            rev = conn.execute(
                select(t_rev).where(t_rev.c.id == opp["current_revision_id"])
            ).mappings().first()
            if not rev:
                raise ApplicationNotFoundError(message="E'lon talqini topilmadi")

            # Check eligibility: if STUDENTS_ONLY or ACADEMIC_TRIPARTITE, verify enrollment (AC-001)
            is_student_required = (
                rev["eligibility"] == "STUDENTS_ONLY"
                or rev["contract_type"] == "ACADEMIC_TRIPARTITE"
                or rev["work_mode"] == "ACADEMIC_INTERNSHIP"
            )
            resolved_enrollment_id = None
            if enrollment_id:
                enr_uuid = _validate_uuid(enrollment_id, "enrollment_id")
                t_enr = table("enrollments")
                enr = conn.execute(
                    select(t_enr).where(
                        t_enr.c.id == enr_uuid,
                        t_enr.c.candidate_id == candidate_id,
                        t_enr.c.status == "APPROVED",
                    )
                ).mappings().first()
                if not enr:
                    raise ApplicationValidationError(
                        code="INVALID_ENROLLMENT",
                        message="Tasdiqlangan talabalik a'zoligi topilmadi",
                    )
                resolved_enrollment_id = str(enr["id"])
            elif is_student_required:
                # Look for an approved enrollment automatically
                t_enr = table("enrollments")
                enr = conn.execute(
                    select(t_enr).where(
                        t_enr.c.candidate_id == candidate_id,
                        t_enr.c.status == "APPROVED",
                    )
                ).mappings().first()
                if not enr:
                    raise ApplicationValidationError(
                        code="STUDENT_ENROLLMENT_REQUIRED",
                        message="Ushbu e'lon faqat talabalar uchun mo'ljallangan (AC-001)",
                    )
                resolved_enrollment_id = str(enr["id"])

            # Check if an application already exists for this (candidate_id, opportunity_id)
            t_apps = table("applications")
            existing_app = conn.execute(
                select(t_apps).where(
                    t_apps.c.candidate_id == candidate_id,
                    t_apps.c.opportunity_id == opp_uuid,
                )
            ).mappings().first()

            if existing_app:
                if existing_app["status"] in ("SUBMITTED", "UNDER_REVIEW", "INTERVIEW_SCHEDULED", "OFFERED", "ACCEPTED"):
                    raise ApplicationConflictError(
                        code="APPLICATION_ALREADY_EXISTS",
                        message="Ushbu e'longa allaqachon faol ariza topshirilgan",
                    )
                else:
                    raise ApplicationConflictError(
                        code="USE_REAPPLY_ENDPOINT",
                        message="Ariza ilgari topshirilgan. Qayta topshirish uchun reapply amalini bajaring",
                    )

            # Evaluate Schedule Matching (AC-013)
            schedule_result, shifts = self._evaluate_candidate_schedule(conn, candidate_id, rev)
            if rev["schedule_policy"] == "STRICT" and schedule_result == "CONFLICT":
                raise ApplicationValidationError(
                    code="SCHEDULE_CONFLICT_STRICT",
                    message="Nomzod jadvali e'lon talablariga mos kelmadi (STRICT siyosati)",
                )

            # Profile snapshot
            snapshot = self._build_profile_snapshot(conn, candidate_id, profile)
            if note:
                snapshot["candidate_note"] = str(note)[:1000]

            # 1. Insert applications row
            app_id = str(uuid4())
            insert_row(
                conn,
                "applications",
                id=app_id,
                candidate_id=candidate_id,
                opportunity_id=opp_uuid,
                status="SUBMITTED",
                current_attempt_id=None,
                version=1,
                created_at=now_dt,
                updated_at=now_dt,
            )

            # 2. Insert application_attempts row
            attempt_id = str(uuid4())
            insert_row(
                conn,
                "application_attempts",
                id=attempt_id,
                application_id=app_id,
                attempt_no=1,
                revision_id=rev["id"],
                enrollment_id=resolved_enrollment_id,
                profile_snapshot=snapshot,
                schedule_result=schedule_result,
                matching_version=ALGORITHM_VERSION,
                proposed_slots=proposed_slots,
                submitted_at=now_dt,
                idempotency_key=idem_key,
                opportunity_id=opp_uuid,
            )

            # 3. Update applications current_attempt_id
            conn.execute(
                t_apps.update()
                .where(t_apps.c.id == app_id)
                .values(current_attempt_id=attempt_id)
            )

            # 4. Insert application_events row
            insert_row(
                conn,
                "application_events",
                id=str(uuid4()),
                application_id=app_id,
                attempt_id=attempt_id,
                actor_id=actor.user_id,
                from_status=None,
                to_status="SUBMITTED",
                reason="INITIAL_APPLICATION",
                occurred_at=now_dt,
            )

            # 5. Append audit log
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="APPLICATION_SUBMITTED",
                entity_type="application",
                entity_id=app_id,
                metadata={
                    "opportunity_id": opp_uuid,
                    "attempt_id": attempt_id,
                    "attempt_no": 1,
                    "schedule_result": schedule_result,
                },
            )

            # Render response
            app_fresh = conn.execute(
                select(t_apps).where(t_apps.c.id == app_id)
            ).mappings().first()
            att_fresh = conn.execute(
                select(t_attempts).where(t_attempts.c.id == attempt_id)
            ).mappings().first()
            return self._render_application_response(conn, app_fresh, att_fresh)

    # -------------------------------------------------------------------------
    # API-029: Application Summary & Metrics (GET /me/applications/summary)
    # -------------------------------------------------------------------------
    def get_applications_summary(self, actor: ActorContext) -> dict[str, Any]:
        """Aggregate metrics of candidate's applications (API-029 / CAP-007)."""
        with read_snapshot() as conn:
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            t_apps = table("applications")
            rows = conn.execute(
                select(t_apps.c.status, func.count(t_apps.c.id).label("cnt"))
                .where(t_apps.c.candidate_id == candidate_id)
                .group_by(t_apps.c.status)
            ).all()

            counts: dict[str, int] = {r[0]: r[1] for r in rows}
            total = sum(counts.values())

            # Intersect with interviews and offers counts
            t_interviews = table("interviews")
            interview_count = conn.execute(
                select(func.count(t_interviews.c.id))
                .select_from(t_interviews.join(t_apps, t_apps.c.id == t_interviews.c.application_id))
                .where(
                    t_apps.c.candidate_id == candidate_id,
                    t_interviews.c.status != "CANCELLED",
                )
            ).scalar() or 0

            t_offers = table("offers")
            offer_count = conn.execute(
                select(func.count(t_offers.c.id))
                .select_from(t_offers.join(t_apps, t_apps.c.id == t_offers.c.application_id))
                .where(
                    t_apps.c.candidate_id == candidate_id,
                    t_offers.c.status.in_(("ACTIVE", "ACCEPTED", "OFFERED")),
                )
            ).scalar() or 0

            return {
                "contract_id": "API-029",
                "candidate_id": candidate_id,
                "total_applications": total,
                "submitted": counts.get("SUBMITTED", 0),
                "under_review": counts.get("UNDER_REVIEW", 0),
                "interview_scheduled": counts.get("INTERVIEW_SCHEDULED", 0),
                "interviews_total": interview_count,
                "offered": counts.get("OFFERED", 0),
                "offers_total": offer_count,
                "accepted": counts.get("ACCEPTED", 0),
                "rejected": counts.get("REJECTED", 0),
                "withdrawn": counts.get("WITHDRAWN", 0),
                "expired": counts.get("EXPIRED", 0),
            }

    # -------------------------------------------------------------------------
    # API-039: List candidate applications (GET /me/applications)
    # -------------------------------------------------------------------------
    def list_my_applications(
        self,
        actor: ActorContext,
        status: Optional[str] = None,
        limit: int = 20,
        after: Optional[str] = None,
    ) -> dict[str, Any]:
        """List candidate's applications with stable keyset cursor pagination (API-039)."""
        limit = max(1, min(limit, 100))

        with read_snapshot() as conn:
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            t_apps = table("applications")
            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")
            t_org = table("organizations")
            t_att = table("application_attempts")

            query = (
                select(
                    t_apps.c.id,
                    t_apps.c.opportunity_id,
                    t_apps.c.status,
                    t_apps.c.version,
                    t_apps.c.created_at,
                    t_apps.c.updated_at,
                    t_opp.c.status.label("opportunity_status"),
                    t_rev.c.title.label("opportunity_title"),
                    t_rev.c.work_mode,
                    t_rev.c.contract_type,
                    t_rev.c.compensation_type if hasattr(t_rev.c, "compensation_type") else t_rev.c.work_mode,
                    t_org.c.public_name.label("organization_name"),
                    t_att.c.attempt_no,
                    t_att.c.submitted_at.label("attempt_submitted_at"),
                    t_att.c.schedule_result,
                )
                .select_from(
                    t_apps.join(t_opp, t_opp.c.id == t_apps.c.opportunity_id)
                    .join(t_rev, t_rev.c.id == t_opp.c.current_revision_id)
                    .join(t_org, t_org.c.id == t_opp.c.organization_id)
                    .outerjoin(t_att, t_att.c.id == t_apps.c.current_attempt_id)
                )
                .where(t_apps.c.candidate_id == candidate_id)
            )

            if status:
                query = query.where(t_apps.c.status == status.upper().strip())

            # Keyset pagination decode
            if after:
                try:
                    decoded = base64.urlsafe_b64decode(after.encode("utf-8")).decode("utf-8")
                    cursor_data = json.loads(decoded)
                    cursor_dt = datetime.fromisoformat(cursor_data["c"])
                    cursor_id = cursor_data["i"]
                    query = query.where(
                        or_(
                            t_apps.c.created_at < cursor_dt,
                            and_(t_apps.c.created_at == cursor_dt, t_apps.c.id < cursor_id),
                        )
                    )
                except Exception:
                    raise ApplicationValidationError(code="INVALID_CURSOR", message="Yaroqsiz sahifalash kursori")

            query = query.order_by(t_apps.c.created_at.desc(), t_apps.c.id.desc()).limit(limit + 1)
            rows = list(conn.execute(query).mappings())

            has_more = len(rows) > limit
            items = rows[:limit]

            next_after = None
            if has_more and items:
                last = items[-1]
                last_payload = {
                    "c": _to_utc_iso(last["created_at"]),
                    "i": str(last["id"]),
                }
                next_after = base64.urlsafe_b64encode(
                    json.dumps(last_payload).encode("utf-8")
                ).decode("utf-8")

            formatted_items = []
            for r in items:
                formatted_items.append(
                    {
                        "id": str(r["id"]),
                        "opportunity_id": str(r["opportunity_id"]),
                        "status": r["status"],
                        "version": r["version"],
                        "created_at": _to_utc_iso(r["created_at"]),
                        "updated_at": _to_utc_iso(r["updated_at"]),
                        "opportunity": {
                            "id": str(r["opportunity_id"]),
                            "title": r["opportunity_title"],
                            "organization_name": r["organization_name"],
                            "work_mode": r["work_mode"],
                            "contract_type": r["contract_type"],
                            "status": r["opportunity_status"],
                        },
                        "current_attempt": {
                            "attempt_no": r["attempt_no"],
                            "submitted_at": _to_utc_iso(r["attempt_submitted_at"]),
                            "schedule_result": r["schedule_result"],
                        } if r["attempt_no"] is not None else None,
                    }
                )

            return {
                "contract_id": "API-039",
                "items": formatted_items,
                "next_after": next_after,
            }

    # -------------------------------------------------------------------------
    # API-040: Reapply (POST /me/applications/{id}/reapply)
    # -------------------------------------------------------------------------
    def reapply_application(
        self,
        actor: ActorContext,
        application_id: str,
        idempotency_key: str,
        reason: Optional[str] = None,
        proposed_slots: Optional[list[Any] | dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Reapply to an existing application subject to 24h cooldown and 3/30-day limit (API-040)."""
        if not idempotency_key or not str(idempotency_key).strip():
            raise ApplicationValidationError(
                code="IDEMPOTENCY_KEY_REQUIRED",
                message="Idempotency-Key sarlavhasi majburiy",
            )
        idem_key = str(idempotency_key).strip()
        app_uuid = _validate_uuid(application_id, "application_id")

        with transaction() as conn:
            account_authority(conn, actor)
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            t_apps = table("applications")
            t_attempts = table("application_attempts")

            # Check Idempotency-Key first
            existing_attempt = conn.execute(
                select(t_attempts).where(t_attempts.c.idempotency_key == idem_key)
            ).mappings().first()
            if existing_attempt:
                if str(existing_attempt["application_id"]) == app_uuid:
                    app_row = conn.execute(
                        select(t_apps).where(t_apps.c.id == app_uuid)
                    ).mappings().first()
                    return self._render_application_response(conn, app_row, existing_attempt)
                raise ApplicationConflictError(
                    code="IDEMPOTENCY_KEY_REUSED",
                    message="Idempotency-Key boshqa ariza urinishi uchun ishlatilgan",
                )

            # Lock the applications row
            app = conn.execute(
                select(t_apps)
                .where(t_apps.c.id == app_uuid, t_apps.c.candidate_id == candidate_id)
                .with_for_update()
            ).mappings().first()

            if not app:
                raise ApplicationNotFoundError(message="Ariza topilmadi")

            # Status rule: must be terminal (REJECTED, WITHDRAWN, EXPIRED)
            if app["status"] not in ("REJECTED", "WITHDRAWN", "EXPIRED"):
                raise ApplicationConflictError(
                    code="APPLICATION_ACTIVE",
                    message=f"Arizani qayta topshirish uchun u yakunlangan bo'lishi kerak. Joriy holat: {app['status']}",
                )

            # Opportunity must still be active and open
            t_opp = table("opportunities")
            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            if not opp or opp["status"] != "PUBLISHED":
                raise ApplicationConflictError(
                    code="OPPORTUNITY_CLOSED",
                    message="E'lon yopilgan yoki faol emas. Qayta ariza topshirib bo'lmaydi",
                )

            now_dt = now()
            if opp["expires_at"] and opp["expires_at"] <= now_dt:
                raise ApplicationConflictError(
                    code="OPPORTUNITY_EXPIRED",
                    message="E'lon muddati o'tgan",
                )

            # 24-hour Cooldown Rule:
            last_attempt = conn.execute(
                select(t_attempts)
                .where(t_attempts.c.application_id == app_uuid)
                .order_by(t_attempts.c.attempt_no.desc())
            ).mappings().first()

            if last_attempt:
                last_time = last_attempt["submitted_at"]
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                curr_utc = now_dt if now_dt.tzinfo else now_dt.replace(tzinfo=timezone.utc)
                if curr_utc - last_time < timedelta(hours=24):
                    remaining_sec = int((timedelta(hours=24) - (curr_utc - last_time)).total_seconds())
                    raise ApplicationRateLimitError(
                        code="REAPPLY_COOLDOWN_ACTIVE",
                        message=f"Qayta ariza topshirish uchun 24 soat kutish kerak. Qolgan vaqt: {remaining_sec} sekund (CAP-007)",
                    )

            # 3 attempts per 30-day Limit Rule:
            window_30d = (now_dt if now_dt.tzinfo else now_dt.replace(tzinfo=timezone.utc)) - timedelta(days=30)
            recent_attempts_count = conn.execute(
                select(func.count(t_attempts.c.id))
                .where(
                    t_attempts.c.application_id == app_uuid,
                    t_attempts.c.submitted_at >= window_30d,
                )
            ).scalar() or 0

            if recent_attempts_count >= 3:
                raise ApplicationRateLimitError(
                    code="REAPPLY_LIMIT_EXCEEDED",
                    message="Oxirgi 30 kun ichida eng ko'pi bilan 3 marta qayta ariza topshirish mumkin (CAP-007)",
                )

            # Fetch active revision and re-evaluate schedule
            t_rev = table("opportunity_revisions")
            rev = conn.execute(
                select(t_rev).where(t_rev.c.id == opp["current_revision_id"])
            ).mappings().first()
            schedule_result, shifts = self._evaluate_candidate_schedule(conn, candidate_id, rev)
            if rev["schedule_policy"] == "STRICT" and schedule_result == "CONFLICT":
                raise ApplicationValidationError(
                    code="SCHEDULE_CONFLICT_STRICT",
                    message="Nomzod jadvali e'lon talablariga mos kelmadi (STRICT siyosati)",
                )

            # Prepare new attempt
            next_attempt_no = (last_attempt["attempt_no"] + 1) if last_attempt else 1
            snapshot = self._build_profile_snapshot(conn, candidate_id, profile)
            if reason:
                snapshot["reapply_reason"] = str(reason)[:1000]

            new_attempt_id = str(uuid4())
            insert_row(
                conn,
                "application_attempts",
                id=new_attempt_id,
                application_id=app_uuid,
                attempt_no=next_attempt_no,
                revision_id=rev["id"],
                enrollment_id=last_attempt["enrollment_id"] if last_attempt else None,
                profile_snapshot=snapshot,
                schedule_result=schedule_result,
                matching_version=ALGORITHM_VERSION,
                proposed_slots=proposed_slots,
                submitted_at=now_dt,
                idempotency_key=idem_key,
                opportunity_id=opp["id"],
            )

            # Update applications table
            conn.execute(
                t_apps.update()
                .where(t_apps.c.id == app_uuid)
                .values(
                    status="SUBMITTED",
                    current_attempt_id=new_attempt_id,
                    version=app["version"] + 1,
                    updated_at=now_dt,
                )
            )

            # Insert application_events row
            insert_row(
                conn,
                "application_events",
                id=str(uuid4()),
                application_id=app_uuid,
                attempt_id=new_attempt_id,
                actor_id=actor.user_id,
                from_status=app["status"],
                to_status="SUBMITTED",
                reason=reason or "CANDIDATE_REAPPLY",
                occurred_at=now_dt,
            )

            # Append audit log
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="APPLICATION_REAPPLIED",
                entity_type="application",
                entity_id=app_uuid,
                metadata={
                    "attempt_id": new_attempt_id,
                    "attempt_no": next_attempt_no,
                    "reason": reason,
                },
            )

            app_fresh = conn.execute(
                select(t_apps).where(t_apps.c.id == app_uuid)
            ).mappings().first()
            att_fresh = conn.execute(
                select(t_attempts).where(t_attempts.c.id == new_attempt_id)
            ).mappings().first()
            return self._render_application_response(conn, app_fresh, att_fresh)

    # -------------------------------------------------------------------------
    # API-041: Get application details with timeline & attempts (GET /me/applications/{id})
    # -------------------------------------------------------------------------
    def get_application_detail(self, actor: ActorContext, application_id: str) -> dict[str, Any]:
        """Retrieve application detail, timeline events, attempts history, and interview/offer (API-041)."""
        app_uuid = _validate_uuid(application_id, "application_id")

        with read_snapshot() as conn:
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            t_apps = table("applications")
            app = conn.execute(
                select(t_apps).where(
                    t_apps.c.id == app_uuid,
                    t_apps.c.candidate_id == candidate_id,
                )
            ).mappings().first()

            if not app:
                raise ApplicationNotFoundError(message="Ariza topilmadi")

            # Opportunity & Revision & Organization info
            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")
            t_org = table("organizations")
            opp = conn.execute(
                select(
                    t_opp.c.id,
                    t_opp.c.status,
                    t_opp.c.organization_id,
                    t_rev.c.title,
                    t_rev.c.work_mode,
                    t_rev.c.contract_type,
                    t_org.c.public_name.label("organization_name"),
                )
                .select_from(
                    t_opp.join(t_rev, t_rev.c.id == t_opp.c.current_revision_id)
                    .join(t_org, t_org.c.id == t_opp.c.organization_id)
                )
                .where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()

            # Attempts history
            t_attempts = table("application_attempts")
            attempts_rows = list(
                conn.execute(
                    select(t_attempts)
                    .where(t_attempts.c.application_id == app_uuid)
                    .order_by(t_attempts.c.attempt_no.asc())
                ).mappings()
            )

            # Timeline events
            t_events = table("application_events")
            events_rows = list(
                conn.execute(
                    select(t_events)
                    .where(t_events.c.application_id == app_uuid)
                    .order_by(t_events.c.occurred_at.asc())
                ).mappings()
            )

            # Active interview
            t_interviews = table("interviews")
            interview_row = conn.execute(
                select(t_interviews)
                .where(t_interviews.c.application_id == app_uuid)
                .order_by(t_interviews.c.created_at.desc())
            ).mappings().first()

            # Active offer
            t_offers = table("offers")
            offer_row = conn.execute(
                select(t_offers)
                .where(t_offers.c.application_id == app_uuid)
                .order_by(t_offers.c.created_at.desc())
            ).mappings().first()

            return {
                "contract_id": "API-041",
                "id": str(app["id"]),
                "candidate_id": str(app["candidate_id"]),
                "opportunity_id": str(app["opportunity_id"]),
                "status": app["status"],
                "version": app["version"],
                "created_at": _to_utc_iso(app["created_at"]),
                "updated_at": _to_utc_iso(app["updated_at"]),
                "occupied_at": _to_utc_iso(app["occupied_at"]),
                "released_at": _to_utc_iso(app["released_at"]),
                "opportunity": {
                    "id": str(opp["id"]) if opp else str(app["opportunity_id"]),
                    "title": opp["title"] if opp else None,
                    "organization_id": str(opp["organization_id"]) if opp else None,
                    "organization_name": opp["organization_name"] if opp else None,
                    "work_mode": opp["work_mode"] if opp else None,
                    "contract_type": opp["contract_type"] if opp else None,
                    "status": opp["status"] if opp else None,
                },
                "attempts": [
                    {
                        "id": str(att["id"]),
                        "attempt_no": att["attempt_no"],
                        "revision_id": str(att["revision_id"]),
                        "enrollment_id": str(att["enrollment_id"]) if att["enrollment_id"] else None,
                        "profile_snapshot": att["profile_snapshot"],
                        "schedule_result": att["schedule_result"],
                        "matching_version": att["matching_version"],
                        "proposed_slots": att["proposed_slots"],
                        "submitted_at": _to_utc_iso(att["submitted_at"]),
                    }
                    for att in attempts_rows
                ],
                "timeline": [
                    {
                        "id": str(ev["id"]),
                        "attempt_id": str(ev["attempt_id"]) if ev["attempt_id"] else None,
                        "actor_id": str(ev["actor_id"]),
                        "from_status": ev["from_status"],
                        "to_status": ev["to_status"],
                        "reason": ev["reason"],
                        "occurred_at": _to_utc_iso(ev["occurred_at"]),
                    }
                    for ev in events_rows
                ],
                "interview": {
                    "id": str(interview_row["id"]),
                    "starts_at": _to_utc_iso(interview_row["starts_at"]),
                    "ends_at": _to_utc_iso(interview_row["ends_at"]),
                    "timezone": interview_row["timezone"],
                    "mode": interview_row["mode"],
                    "location_or_link": interview_row["location_or_link"],
                    "status": interview_row["status"],
                } if interview_row else None,
                "offer": {
                    "id": str(offer_row["id"]),
                    "status": offer_row["status"],
                    "terms_snapshot": offer_row["terms_snapshot"],
                    "expires_at": _to_utc_iso(offer_row["expires_at"]),
                    "accepted_at": _to_utc_iso(offer_row["accepted_at"]),
                } if offer_row else None,
            }

    # -------------------------------------------------------------------------
    # API-044: Withdraw application (POST /me/applications/{id}/withdraw)
    # -------------------------------------------------------------------------
    def withdraw_application(
        self,
        actor: ActorContext,
        application_id: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Withdraw application and release reserved capacity if occupied (API-044 / CAP-007)."""
        app_uuid = _validate_uuid(application_id, "application_id")

        with transaction() as conn:
            account_authority(conn, actor)
            profile = self._resolve_candidate_profile(conn, actor)
            candidate_id = str(profile["id"])

            t_apps = table("applications")
            app = conn.execute(
                select(t_apps)
                .where(t_apps.c.id == app_uuid, t_apps.c.candidate_id == candidate_id)
                .with_for_update()
            ).mappings().first()

            if not app:
                raise ApplicationNotFoundError(message="Ariza topilmadi")

            # Idempotent repeat: already withdrawn
            if app["status"] == "WITHDRAWN":
                return {
                    "contract_id": "API-044",
                    "id": str(app["id"]),
                    "status": "WITHDRAWN",
                    "version": app["version"],
                    "message": "Ariza allaqachon qaytarib olingan",
                }

            if app["status"] == "ACCEPTED":
                raise ApplicationConflictError(
                    code="CANNOT_WITHDRAW_ACCEPTED",
                    message="Qabul qilingan arizani qaytarib olib bo'lmaydi (ish boshlangan)",
                )

            now_dt = now()
            # If capacity was occupied, release it
            if app["occupied_at"]:
                t_opp = table("opportunities")
                conn.execute(
                    t_opp.update()
                    .where(t_opp.c.id == app["opportunity_id"])
                    .values(
                        occupied_count=func.greatest(0, t_opp.c.occupied_count - 1),
                        updated_at=now_dt,
                    )
                )

            # Update applications table
            conn.execute(
                t_apps.update()
                .where(t_apps.c.id == app_uuid)
                .values(
                    status="WITHDRAWN",
                    released_at=now_dt if app["occupied_at"] else None,
                    version=app["version"] + 1,
                    updated_at=now_dt,
                )
            )

            # Insert application_events row
            insert_row(
                conn,
                "application_events",
                id=str(uuid4()),
                application_id=app_uuid,
                attempt_id=app["current_attempt_id"],
                actor_id=actor.user_id,
                from_status=app["status"],
                to_status="WITHDRAWN",
                reason=reason or "CANDIDATE_WITHDREW",
                occurred_at=now_dt,
            )

            # Append audit log
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="APPLICATION_WITHDRAWN",
                entity_type="application",
                entity_id=app_uuid,
                metadata={
                    "from_status": app["status"],
                    "reason": reason,
                    "released_capacity": bool(app["occupied_at"]),
                },
            )

            return {
                "contract_id": "API-044",
                "id": str(app["id"]),
                "status": "WITHDRAWN",
                "version": app["version"] + 1,
                "updated_at": _to_utc_iso(now_dt),
                "message": "Ariza muvaffaqiyatli qaytarib olindi",
            }

    def _render_application_response(
        self, conn: Any, app: Any, attempt: Any
    ) -> dict[str, Any]:
        return {
            "contract_id": "API-006",
            "id": str(app["id"]),
            "candidate_id": str(app["candidate_id"]),
            "opportunity_id": str(app["opportunity_id"]),
            "status": app["status"],
            "version": app["version"],
            "created_at": _to_utc_iso(app["created_at"]),
            "updated_at": _to_utc_iso(app["updated_at"]),
            "current_attempt": {
                "id": str(attempt["id"]),
                "attempt_no": attempt["attempt_no"],
                "revision_id": str(attempt["revision_id"]),
                "enrollment_id": str(attempt["enrollment_id"]) if attempt["enrollment_id"] else None,
                "schedule_result": attempt["schedule_result"],
                "matching_version": attempt["matching_version"],
                "submitted_at": _to_utc_iso(attempt["submitted_at"]),
                "profile_snapshot": attempt["profile_snapshot"],
            } if attempt else None,
        }


candidate_application_service = CandidateApplicationService()
