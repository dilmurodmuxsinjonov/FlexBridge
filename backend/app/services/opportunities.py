"""Opportunities, Revisions (`contract_type` & compensation matrix `INV-03`), Shift Groups (`group_code` `INV-02`), Quota Enforcement (`INV-04`, `AC-042`, `FIX-06`), and `API-003` Matching Engine (`AC-039`, `REV-002`) (S2.4.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import base64
from datetime import date, datetime
from app.api.v1.billing import billing_service
from app.db.storage import table, transaction, now
from app.services.placements import get_row, insert_row
from app.api.dependencies import ActorContext, require_org
from sqlalchemy import select, and_, or_
from app.services.schedule import local_today
from app.services.availability import (
    CandidateAvailabilityService,
    availability_service,
    ranges_overlap,
    validate_minute_bounds,
)

VALID_CONTRACT_TYPES: frozenset[str] = frozenset(
    {
        "LABOR_PART_TIME",
        "CIVIL_GPC",
        "INTERNSHIP_AGREEMENT",
        "ACADEMIC_TRIPARTITE",
        "PAID_INTERNSHIP_CONTRACT",
        "UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT",
    }
)


class OpportunityConstraintError(Exception):
    """Raised when an opportunity revision or shift violates `INV-02`, `INV-03`, `INV-04`, or `AC-039`."""

    def __init__(self, code: str, message: str, status_code: int = 422, sqlstate: str = "23514") -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.sqlstate = sqlstate


def validate_compensation_contract_matrix(
    *,
    opportunity_kind: str,
    contract_type: str,
    compensation_type: str,
    hourly_pay: int | None,
    stipend_amount: int | None,
    fee_terms_note: str | None = None,
) -> None:
    """Enforce `chk_opp_rev_contract_type` and `chk_opp_rev_compensation_matrix` (`INV-03`, `AC-039`)."""
    if not contract_type or contract_type not in VALID_CONTRACT_TYPES:
        raise OpportunityConstraintError(
            code="INVALID_CONTRACT_TYPE",
            message=f"Noto'g'ri contract_type: {contract_type} (chk_opp_rev_contract_type, AC-039)",
            status_code=422,
            sqlstate="23514",
        )

    if compensation_type == "HOURLY":
        valid = (
            contract_type in ("LABOR_PART_TIME", "CIVIL_GPC", "PAID_INTERNSHIP_CONTRACT", "INTERNSHIP_AGREEMENT")
            and hourly_pay is not None
            and hourly_pay > 0
            and stipend_amount is None
            and fee_terms_note is None
        )
    elif compensation_type == "STIPEND":
        valid = (
            contract_type in ("PAID_INTERNSHIP_CONTRACT", "INTERNSHIP_AGREEMENT")
            and stipend_amount is not None
            and stipend_amount > 0
            and hourly_pay is None
            and fee_terms_note is None
        )
    elif compensation_type == "UNPAID_ACADEMIC":
        valid = (
            opportunity_kind in ("ACADEMIC_INTERNSHIP", "INTERNSHIP")
            and contract_type in ("UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT", "ACADEMIC_TRIPARTITE")
            and hourly_pay is None
            and stipend_amount is None
        )
    else:
        valid = False

    if not valid:
        raise OpportunityConstraintError(
            code="INVALID_COMPENSATION_CONTRACT_MATRIX",
            message=(
                "chk_opp_rev_compensation_matrix (INV-03, AC-039): opportunity_kind, contract_type "
                "va maosh maydonlari (hourly_pay / stipend_amount) o'zaro mos emas"
            ),
            status_code=422,
            sqlstate="23514",
        )


def compensation_type_for(revision):
    if not revision['is_paid']:
        return 'UNPAID_ACADEMIC'
    return 'STIPEND' if revision['salary_period'] == 'MONTH' else 'HOURLY'


@dataclass
class OpportunityMatchingService:
    """Manages `opportunities`, `opportunity_revisions`, `opportunity_shifts`, and `API-003` feed matching (`AC-039`)."""

    avail_svc: CandidateAvailabilityService = field(default_factory=lambda: availability_service)
    @property
    def opportunities(self):
        with transaction() as conn:
            return {r['id']:dict(r) for r in conn.execute(select(table('opportunities'))).mappings()}

    @property
    def revisions(self):
        with transaction() as conn:
            return {r['id']:{**r,'compensation_type':compensation_type_for(r)} for r in conn.execute(select(table('opportunity_revisions'))).mappings()}

    @property
    def shifts(self):
        with transaction() as conn:
            return {r['id']:dict(r) for r in conn.execute(select(table('opportunity_shifts'))).mappings()}

    def create_opportunity_revision(self,*,organization_id,title,opportunity_kind,contract_type,compensation_type,
            actor_user_id,hourly_pay=None,stipend_amount=None,fee_terms_note=None,published=False):
        validate_compensation_contract_matrix(opportunity_kind=opportunity_kind,contract_type=contract_type,
            compensation_type=compensation_type,hourly_pay=hourly_pay,stipend_amount=stipend_amount,fee_terms_note=fee_terms_note)
        if published:
            raise OpportunityConstraintError('MODERATION_APPROVAL_REQUIRED','Create a draft, obtain moderation approval, then publish',409)
        with transaction() as conn:
            require_org(ActorContext(actor_user_id,'',()),organization_id,'OWNER','HR','HOST_COORDINATOR')
            kind={'PART_TIME_JOB':'PART_TIME','GENERAL_INTERNSHIP':'INTERNSHIP','ACADEMIC_INTERNSHIP':'INTERNSHIP'}.get(opportunity_kind,opportunity_kind)
            if kind not in ('PART_TIME','INTERNSHIP'): raise OpportunityConstraintError('INVALID_OPPORTUNITY_KIND','Invalid kind',422)
            opp=insert_row(conn,'opportunities',organization_id=organization_id,kind=kind,status='DRAFT',capacity=1,occupied_count=0)
            contract={'PAID_INTERNSHIP_CONTRACT':'INTERNSHIP_AGREEMENT','UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT':'ACADEMIC_TRIPARTITE'}.get(contract_type,contract_type)
            revision=insert_row(conn,'opportunity_revisions',opportunity_id=opp['id'],revision=1,author_id=actor_user_id,title=title,
                description=title,region='',work_mode='ONSITE',eligibility='OPEN',currency='UZS',is_paid=compensation_type!='UNPAID_ACADEMIC',
                salary_min=hourly_pay or stipend_amount,salary_period='HOUR' if hourly_pay else ('MONTH' if stipend_amount else None),
                salary_basis='GROSS' if hourly_pay or stipend_amount else None,start_date=local_today(),schedule_policy='FIXED',
                shift_match_mode='ALL_SHIFTS_IN_GROUP',snapshot_schema=1,contract_type=contract)
            conn.execute(table('opportunities').update().where(table('opportunities').c.id==opp['id']).values(current_revision_id=revision['id']))
            return revision

    def publish_opportunity_api_081(self,*,opportunity_id,actor_user_id):
        with transaction() as conn:
            opp=get_row(conn,'opportunities',opportunity_id)
            return {'contract_id':'API-081',**billing_service.publish_opportunity_with_quota(
                organization_id=opp['organization_id'],opportunity_id=opportunity_id,actor_user_id=actor_user_id)}

    def _get_draft_and_authorize(self, conn, opportunity_id: str, actor: ActorContext) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch opportunity and current revision with row lock, verifying org access, role scopes, and DRAFT status."""
        try:
            opp_uuid = str(UUID(str(opportunity_id)))
        except (ValueError, TypeError, AttributeError):
            raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        t_opp = table("opportunities")
        opp = conn.execute(select(t_opp).where(t_opp.c.id == opp_uuid).with_for_update()).mappings().first()
        if not opp:
            raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        # Verify caller has an active role in the owning organization
        t_mem = table("org_memberships")
        t_ogrants = table("org_role_grants")
        t_rcat = table("role_catalog")
        org_roles = conn.execute(
            select(t_rcat.c.code)
            .select_from(
                t_mem.join(t_ogrants, t_ogrants.c.membership_id == t_mem.c.id)
                .join(t_rcat, t_ogrants.c.role_id == t_rcat.c.id)
            )
            .where(
                t_mem.c.user_id == actor.user_id,
                t_mem.c.organization_id == opp["organization_id"],
                t_mem.c.status == "ACTIVE",
                t_mem.c.revoked_at.is_(None),
                t_ogrants.c.revoked_at.is_(None),
                t_rcat.c.scope_kind == "ORG",
                t_rcat.c.code.in_(("OWNER", "HR", "HOST_COORDINATOR")),
            )
        ).scalars().all()

        if not org_roles:
            # IDOR defense: return uniform 404 if caller has no staff roles in owning org
            raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        # HOST_COORDINATOR role constraint: can only manage INTERNSHIP opportunities (CAP-016)
        if "HOST_COORDINATOR" in org_roles and not ("OWNER" in org_roles or "HR" in org_roles):
            if opp["kind"] != "INTERNSHIP":
                raise OpportunityConstraintError(
                    "HOST_COORDINATOR_INTERNSHIP_ONLY",
                    "HOST_COORDINATOR faqat INTERNSHIP e'lonlarini tahrirlashi mumkin",
                    status_code=403,
                )

        # AC-008: Check that opportunity is in DRAFT status
        if opp["status"] != "DRAFT":
            raise OpportunityConstraintError(
                "OPPORTUNITY_NOT_DRAFT",
                "Faqat qoralama (DRAFT) holatidagi e'lonlarni tahrirlash mumkin (AC-008)",
                status_code=409,
            )

        t_rev = table("opportunity_revisions")
        rev = None
        if opp["current_revision_id"]:
            rev = conn.execute(select(t_rev).where(t_rev.c.id == opp["current_revision_id"]).with_for_update()).mappings().first()
        if not rev:
            # Fallback to latest revision for this opportunity
            rev = conn.execute(
                select(t_rev)
                .where(t_rev.c.opportunity_id == opp_uuid)
                .order_by(t_rev.c.revision.desc())
                .limit(1)
                .with_for_update()
            ).mappings().first()

        if not rev:
            raise OpportunityConstraintError("REVISION_NOT_FOUND", "Revision topilmadi", status_code=404)

        return dict(opp), dict(rev)

    def update_opportunity_draft_api_078(
        self,
        *,
        opportunity_id: str,
        actor: ActorContext,
        title: str | None = None,
        description: str | None = None,
        region: str | None = None,
        work_mode: str | None = None,
        eligibility: str | None = None,
        capacity: int | None = None,
        contract_type: str | None = None,
        program_required: str | None = None,
    ) -> dict[str, Any]:
        """API-078: Update opportunity draft core metadata (CAP-016)."""
        with transaction() as conn:
            opp, rev = self._get_draft_and_authorize(conn, opportunity_id, actor)

            opp_updates = {"updated_at": now()}
            rev_updates = {"updated_at": now()}

            if capacity is not None:
                if capacity <= 0:
                    raise OpportunityConstraintError("INVALID_CAPACITY", "Sig'im noldan katta bo'lishi kerak", status_code=422)
                if capacity < opp["occupied_count"]:
                    raise OpportunityConstraintError(
                        "CAPACITY_LESS_THAN_OCCUPIED",
                        f"Sig'im ({capacity}) band qilingan o'rinlar ({opp['occupied_count']}) dan kam bo'lishi mumkin emas",
                        status_code=409,
                    )
                opp_updates["capacity"] = capacity

            if title is not None:
                title_clean = title.strip()
                if not title_clean:
                    raise OpportunityConstraintError("INVALID_TITLE", "Sarlavha bo'sh bo'lishi mumkin emas", status_code=422)
                rev_updates["title"] = title_clean

            if description is not None:
                desc_clean = description.strip()
                if not desc_clean:
                    raise OpportunityConstraintError("INVALID_DESCRIPTION", "Tavsif bo'sh bo'lishi mumkin emas", status_code=422)
                rev_updates["description"] = desc_clean

            if region is not None:
                rev_updates["region"] = region.strip()

            if work_mode is not None:
                if work_mode not in ("ONSITE", "HYBRID", "REMOTE"):
                    raise OpportunityConstraintError("INVALID_WORK_MODE", f"Noto'g'ri work_mode: {work_mode}", status_code=422)
                rev_updates["work_mode"] = work_mode

            if eligibility is not None:
                if eligibility not in ("ALL_CANDIDATES", "STUDENTS_ONLY", "ACADEMIC_TRIPARTITE", "OPEN"):
                    raise OpportunityConstraintError("INVALID_ELIGIBILITY", f"Noto'g'ri eligibility: {eligibility}", status_code=422)
                rev_updates["eligibility"] = eligibility

            if contract_type is not None:
                contract = {"PAID_INTERNSHIP_CONTRACT": "INTERNSHIP_AGREEMENT", "UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT": "ACADEMIC_TRIPARTITE"}.get(contract_type, contract_type)
                if contract not in VALID_CONTRACT_TYPES:
                    raise OpportunityConstraintError("INVALID_CONTRACT_TYPE", f"Noto'g'ri contract_type: {contract_type}", status_code=422)
                rev_updates["contract_type"] = contract

            if program_required is not None:
                rev_updates["program_required"] = program_required.strip() or None

            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")

            if len(opp_updates) > 1:
                conn.execute(t_opp.update().where(t_opp.c.id == opp["id"]).values(**opp_updates))
            if len(rev_updates) > 1:
                conn.execute(t_rev.update().where(t_rev.c.id == rev["id"]).values(**rev_updates))

            updated_opp = conn.execute(select(t_opp).where(t_opp.c.id == opp["id"])).mappings().first()
            updated_rev = conn.execute(select(t_rev).where(t_rev.c.id == rev["id"])).mappings().first()

            return {
                "contract_id": "API-078",
                "opportunity_id": str(updated_opp["id"]),
                "revision_id": str(updated_rev["id"]),
                "status": updated_opp["status"],
                "kind": updated_opp["kind"],
                "capacity": updated_opp["capacity"],
                "occupied_count": updated_opp["occupied_count"],
                "title": updated_rev["title"],
                "description": updated_rev["description"],
                "region": updated_rev["region"],
                "work_mode": updated_rev["work_mode"],
                "eligibility": updated_rev["eligibility"],
                "contract_type": updated_rev["contract_type"],
                "program_required": updated_rev["program_required"],
                "updated_at": updated_rev["updated_at"].isoformat() if updated_rev.get("updated_at") else None,
            }

    def update_opportunity_terms_api_079(
        self,
        *,
        opportunity_id: str,
        actor: ActorContext,
        is_paid: bool,
        salary_min: Decimal | float | int | None = None,
        salary_max: Decimal | float | int | None = None,
        currency: str = "UZS",
        salary_period: str | None = None,
        salary_basis: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        program_required: str | None = None,
        fee_terms_note: str | None = None,
    ) -> dict[str, Any]:
        """API-079: Update opportunity draft financial and duration terms (CAP-016)."""
        with transaction() as conn:
            opp, rev = self._get_draft_and_authorize(conn, opportunity_id, actor)

            # Part-time paid mandate (CAP-016, AC-008)
            if opp["kind"] == "PART_TIME" and not is_paid:
                raise OpportunityConstraintError(
                    "UNPAID_PART_TIME_FORBIDDEN",
                    "PART_TIME e'lonlari uchun haq to'lanishi shart (bepul part-time taqiqlanadi)",
                    status_code=422,
                )

            # Dates validation
            s_date = None
            if start_date is not None:
                s_date = date.fromisoformat(str(start_date)) if isinstance(start_date, str) else start_date
            else:
                s_date = rev["start_date"] or local_today()

            e_date = None
            if end_date is not None:
                e_date = date.fromisoformat(str(end_date)) if isinstance(end_date, str) else end_date
                if s_date and e_date < s_date:
                    raise OpportunityConstraintError("INVALID_DATE_RANGE", "end_date start_date dan oldin bo'lishi mumkin emas", status_code=422)
            else:
                e_date = rev.get("end_date")

            rev_updates = {
                "updated_at": now(),
                "is_paid": is_paid,
                "currency": currency or "UZS",
                "start_date": s_date,
                "end_date": e_date,
            }

            if program_required is not None:
                rev_updates["program_required"] = program_required.strip() or None

            if is_paid:
                if salary_min is None or Decimal(str(salary_min)) <= 0:
                    raise OpportunityConstraintError("INVALID_SALARY", "To'lovli e'lon uchun salary_min noldan katta bo'lishi shart", status_code=422)
                min_sal = Decimal(str(salary_min))
                rev_updates["salary_min"] = min_sal

                if salary_max is not None:
                    max_sal = Decimal(str(salary_max))
                    if max_sal < min_sal:
                        raise OpportunityConstraintError("INVALID_SALARY_RANGE", "salary_max salary_min dan kichik bo'lishi mumkin emas", status_code=422)
                    rev_updates["salary_max"] = max_sal
                else:
                    rev_updates["salary_max"] = None

                period = salary_period or ("HOUR" if opp["kind"] == "PART_TIME" else "MONTH")
                if period not in ("HOUR", "MONTH"):
                    raise OpportunityConstraintError("INVALID_SALARY_PERIOD", f"salary_period HOUR yoki MONTH bo'lishi kerak: {period}", status_code=422)
                rev_updates["salary_period"] = period

                basis = salary_basis or "GROSS"
                if basis not in ("GROSS", "NET"):
                    raise OpportunityConstraintError("INVALID_SALARY_BASIS", f"salary_basis GROSS yoki NET bo'lishi kerak: {basis}", status_code=422)
                rev_updates["salary_basis"] = basis
            else:
                # Unpaid (Internship only)
                rev_updates["salary_min"] = None
                rev_updates["salary_max"] = None
                rev_updates["salary_period"] = None
                rev_updates["salary_basis"] = None

            t_rev = table("opportunity_revisions")
            conn.execute(t_rev.update().where(t_rev.c.id == rev["id"]).values(**rev_updates))
            updated_rev = conn.execute(select(t_rev).where(t_rev.c.id == rev["id"])).mappings().first()

            return {
                "contract_id": "API-079",
                "opportunity_id": str(opp["id"]),
                "revision_id": str(updated_rev["id"]),
                "is_paid": updated_rev["is_paid"],
                "salary_min": float(updated_rev["salary_min"]) if updated_rev["salary_min"] is not None else None,
                "salary_max": float(updated_rev["salary_max"]) if updated_rev["salary_max"] is not None else None,
                "currency": updated_rev["currency"],
                "salary_period": updated_rev["salary_period"],
                "salary_basis": updated_rev["salary_basis"],
                "start_date": updated_rev["start_date"].isoformat() if updated_rev.get("start_date") else None,
                "end_date": updated_rev["end_date"].isoformat() if updated_rev.get("end_date") else None,
                "program_required": updated_rev["program_required"],
                "updated_at": updated_rev["updated_at"].isoformat() if updated_rev.get("updated_at") else None,
            }

    def update_opportunity_schedule_api_080(
        self,
        *,
        opportunity_id: str,
        actor: ActorContext,
        schedule_policy: str = "STRICT",
        shift_match_mode: str = "ALL",
        shifts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """API-080: Update opportunity draft schedule policy, match mode, and shift intervals (CAP-016)."""
        with transaction() as conn:
            opp, rev = self._get_draft_and_authorize(conn, opportunity_id, actor)

            if schedule_policy not in ("STRICT", "NEGOTIABLE", "FIXED"):
                raise OpportunityConstraintError("INVALID_SCHEDULE_POLICY", f"Noto'g'ri schedule_policy: {schedule_policy}", status_code=422)

            mode_map = {"ALL": "ALL_SHIFTS_IN_GROUP", "ANY": "ANY_SHIFT_IN_GROUP"}
            canonical_mode = mode_map.get(shift_match_mode, shift_match_mode)
            if canonical_mode not in ("ALL_SHIFTS_IN_GROUP", "ANY_SHIFT_IN_GROUP"):
                raise OpportunityConstraintError("INVALID_SHIFT_MATCH_MODE", f"Noto'g'ri shift_match_mode: {shift_match_mode}", status_code=422)

            validated_shifts = []
            if shifts:
                for s in shifts:
                    weekday = int(s.get("weekday", 1))
                    start_minute = int(s.get("start_minute", 0))
                    end_minute = int(s.get("end_minute", 0))
                    group_code = str(s.get("group_code", "GROUP_A")).strip() or "GROUP_A"
                    tz = str(s.get("timezone", "Asia/Tashkent")).strip() or "Asia/Tashkent"

                    if not (1 <= weekday <= 7):
                        raise OpportunityConstraintError("INVALID_WEEKDAY", f"weekday 1..7 oralig'ida bo'lishi kerak: {weekday}", status_code=422)
                    validate_minute_bounds(start_minute, end_minute)

                    # Check overlap with already validated shifts in the same group and weekday (INV-02)
                    for prev in validated_shifts:
                        if prev["group_code"] == group_code and prev["weekday"] == weekday:
                            if ranges_overlap(start_minute, end_minute, prev["start_minute"], prev["end_minute"]):
                                raise OpportunityConstraintError(
                                    "OVERLAPPING_OPPORTUNITY_SHIFT",
                                    f"excl_opportunity_shifts_no_overlap (INV-02): ({group_code}, weekday={weekday}) "
                                    f"uchun [{start_minute}, {end_minute}) va [{prev['start_minute']}, {prev['end_minute']}) o'zaro kesishadi",
                                    status_code=409,
                                    sqlstate="23P01",
                                )
                    validated_shifts.append({
                        "id": str(uuid4()),
                        "revision_id": rev["id"],
                        "weekday": weekday,
                        "start_minute": start_minute,
                        "end_minute": end_minute,
                        "group_code": group_code,
                        "timezone": tz,
                        "created_at": now(),
                        "updated_at": now(),
                    })

            t_shifts = table("opportunity_shifts")
            t_rev = table("opportunity_revisions")

            # Replace shifts atomically
            conn.execute(t_shifts.delete().where(t_shifts.c.revision_id == rev["id"]))
            if validated_shifts:
                for s in validated_shifts:
                    insert_row(conn, "opportunity_shifts", **s)

            conn.execute(
                t_rev.update().where(t_rev.c.id == rev["id"]).values(
                    schedule_policy=schedule_policy,
                    shift_match_mode=canonical_mode,
                    updated_at=now(),
                )
            )

            # Re-fetch shift list
            current_shifts = conn.execute(
                select(t_shifts).where(t_shifts.c.revision_id == rev["id"]).order_by(t_shifts.c.weekday, t_shifts.c.start_minute)
            ).mappings().all()

            return {
                "contract_id": "API-080",
                "opportunity_id": str(opp["id"]),
                "revision_id": str(rev["id"]),
                "schedule_policy": schedule_policy,
                "shift_match_mode": shift_match_mode,
                "shifts_count": len(current_shifts),
                "shifts": [
                    {
                        "id": str(sh["id"]),
                        "weekday": sh["weekday"],
                        "start_minute": sh["start_minute"],
                        "end_minute": sh["end_minute"],
                        "group_code": sh["group_code"],
                        "timezone": sh["timezone"],
                    }
                    for sh in current_shifts
                ],
                "updated_at": now().isoformat(),
            }

    def add_opportunity_shift(
        self,
        *,
        revision_id: str,
        group_code: str,
        weekday: int,
        start_minute: int,
        end_minute: int,
        is_required: bool = True,
        actor_user_id: str,
    ) -> dict[str, Any]:
        """Add a shift to `opportunity_shifts` (`DB-027`) enforcing `excl_opportunity_shifts_no_overlap` (`INV-02`)."""
        if revision_id not in self.revisions:
            raise OpportunityConstraintError("REVISION_NOT_FOUND", "Revision topilmadi", status_code=404)
        if not group_code.strip():
            raise OpportunityConstraintError("INVALID_GROUP_CODE", "group_code bo'sh bo'lishi mumkin emas")
        if not (1 <= weekday <= 7):
            raise OpportunityConstraintError("INVALID_WEEKDAY", "weekday 1..7 oralig'ida bo'lishi kerak")
        validate_minute_bounds(start_minute, end_minute)

        for existing in self.shifts.values():
            if (
                existing["revision_id"] == revision_id
                and existing["group_code"] == group_code
                and existing["weekday"] == weekday
                and ranges_overlap(
                    start_minute,
                    end_minute,
                    existing["start_minute"],
                    existing["end_minute"],
                )
            ):
                raise OpportunityConstraintError(
                    code="OVERLAPPING_OPPORTUNITY_SHIFT",
                    message=(
                        f"excl_opportunity_shifts_no_overlap (INV-02): ({revision_id}, {group_code}, weekday={weekday}) "
                        f"uchun [{start_minute}, {end_minute}) mavjud smena bilan kesishadi"
                    ),
                    status_code=409,
                    sqlstate="23P01",
                )

        with transaction() as conn:
            revision=get_row(conn,'opportunity_revisions',revision_id,True)
            opp=get_row(conn,'opportunities',revision['opportunity_id'],True)
            require_org(ActorContext(actor_user_id,'',()),opp['organization_id'],'OWNER','HR','HOST_COORDINATOR')
            if opp['status']!='DRAFT': raise OpportunityConstraintError('PUBLISHED_REVISION_IMMUTABLE','Only drafts can change',409)
            return insert_row(conn,'opportunity_shifts',revision_id=revision_id,group_code=group_code,weekday=weekday,
                start_minute=start_minute,end_minute=end_minute,timezone='Asia/Tashkent')

    def match_candidate_feed_api_003(self, *, candidate_id, schedule_match_mode='ALL_SHIFTS_IN_GROUP',
                                   check_date=None, commute_buffer_minutes=30):
        return self.match_feed_page(candidate_id=candidate_id, schedule_match_mode=schedule_match_mode,
            check_date=check_date, commute_buffer_minutes=commute_buffer_minutes)['items']

    def match_feed_page(self, *, candidate_id, schedule_match_mode='ALL_SHIFTS_IN_GROUP', check_date=None,
                        commute_buffer_minutes=30, limit=100, after_id=None, opportunity_id=None, revision_id=None):
        from app.services.schedule_matching import match_page
        return match_page(candidate_id, mode=schedule_match_mode, check_date=check_date,
            commute_minutes=commute_buffer_minutes, limit=limit, after_id=after_id,
            opportunity_id=opportunity_id, revision_id=revision_id)

    def get_opportunity_detail(self, opportunity_id: str, actor: ActorContext | None = None) -> dict[str, Any]:
        """Canonical API-005: Retrieve published immutable opportunity revision, wage, eligibility, shifts, skills, and organization details."""
        try:
            opp_uuid = str(UUID(str(opportunity_id)))
        except (ValueError, TypeError, AttributeError):
            raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        with transaction() as conn:
            t_opp = table("opportunities")
            opp = conn.execute(select(t_opp).where(t_opp.c.id == opp_uuid)).mappings().first()
            if not opp:
                raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

            # Access control:
            # PUBLISHED and CLOSED opportunities are publicly accessible.
            # DRAFT, PENDING_MODERATION, and ARCHIVED are only visible to owning org members or platform admins/moderators.
            status = opp["status"]
            if status not in ("PUBLISHED", "CLOSED"):
                authorized = False
                if actor is not None:
                    # Check platform role (ADMIN, MODERATOR)
                    t_pgrants = table("platform_role_grants")
                    t_rcat = table("role_catalog")
                    plat_found = conn.execute(
                        select(t_pgrants.c.id)
                        .select_from(t_pgrants.join(t_rcat, t_pgrants.c.role_id == t_rcat.c.id))
                        .where(
                            t_pgrants.c.user_id == actor.user_id,
                            t_pgrants.c.revoked_at.is_(None),
                            t_pgrants.c.expires_at > now(),
                            t_rcat.c.scope_kind == "PLATFORM",
                            t_rcat.c.code.in_(("ADMIN", "MODERATOR")),
                        )
                    ).first()
                    if plat_found:
                        authorized = True
                    else:
                        # Check org role (OWNER, HR, HOST_COORDINATOR)
                        t_mem = table("org_memberships")
                        t_ogrants = table("org_role_grants")
                        org_found = conn.execute(
                            select(t_mem.c.id)
                            .select_from(
                                t_mem.join(t_ogrants, t_ogrants.c.membership_id == t_mem.c.id)
                                .join(t_rcat, t_ogrants.c.role_id == t_rcat.c.id)
                            )
                            .where(
                                t_mem.c.user_id == actor.user_id,
                                t_mem.c.organization_id == opp["organization_id"],
                                t_mem.c.status == "ACTIVE",
                                t_mem.c.revoked_at.is_(None),
                                t_ogrants.c.revoked_at.is_(None),
                                t_rcat.c.scope_kind == "ORG",
                                t_rcat.c.code.in_(("OWNER", "HR", "HOST_COORDINATOR")),
                            )
                        ).first()
                        if org_found:
                            authorized = True

                if not authorized:
                    raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

            # Fetch current revision
            t_rev = table("opportunity_revisions")
            rev = None
            if opp["current_revision_id"]:
                rev = conn.execute(
                    select(t_rev).where(t_rev.c.id == opp["current_revision_id"])
                ).mappings().first()
            if not rev:
                # Fallback to latest revision
                rev = conn.execute(
                    select(t_rev)
                    .where(t_rev.c.opportunity_id == opp["id"])
                    .order_by(t_rev.c.revision.desc())
                ).mappings().first()

            # Fetch organization details (DB-021)
            t_org = table("organizations")
            org = conn.execute(
                select(t_org).where(t_org.c.id == opp["organization_id"])
            ).mappings().first()

            # Fetch skills (DB-037, DB-013)
            skills_list = []
            shifts_list = []
            if rev:
                t_opp_skills = table("opportunity_skills")
                t_skills = table("skills")
                skills_rows = conn.execute(
                    select(
                        t_skills.c.id,
                        t_skills.c.code,
                        t_skills.c.name_uz,
                        t_skills.c.name_ru,
                        t_opp_skills.c.required,
                        t_opp_skills.c.minimum_level,
                    )
                    .select_from(
                        t_opp_skills.join(t_skills, t_opp_skills.c.skill_id == t_skills.c.id)
                    )
                    .where(t_opp_skills.c.revision_id == rev["id"])
                    .order_by(t_skills.c.name_uz)
                ).mappings().all()

                for s in skills_rows:
                    skills_list.append({
                        "id": str(s["id"]),
                        "code": s["code"],
                        "name_uz": s["name_uz"],
                        "name_ru": s["name_ru"],
                        "required": bool(s["required"]),
                        "minimum_level": s["minimum_level"],
                    })

                # Fetch shifts (DB-038)
                t_shifts = table("opportunity_shifts")
                shifts_rows = conn.execute(
                    select(t_shifts)
                    .where(t_shifts.c.revision_id == rev["id"])
                    .order_by(t_shifts.c.weekday, t_shifts.c.start_minute)
                ).mappings().all()

                for sh in shifts_rows:
                    shifts_list.append({
                        "id": str(sh["id"]),
                        "revision_id": str(sh["revision_id"]),
                        "weekday": sh["weekday"],
                        "start_minute": sh["start_minute"],
                        "end_minute": sh["end_minute"],
                        "timezone": sh["timezone"],
                        "group_code": sh["group_code"],
                    })

            capacity = opp["capacity"]
            occupied_count = opp["occupied_count"]
            now_dt = now()
            is_active_open = (
                opp["status"] == "PUBLISHED"
                and (opp["expires_at"] is None or opp["expires_at"] > now_dt)
            )
            vacancies_available = max(0, capacity - occupied_count) if is_active_open else 0

            org_data = None
            if org:
                org_data = {
                    "id": str(org["id"]),
                    "legal_name": org["legal_name"],
                    "public_name": org["public_name"],
                    "region": org["region"],
                    "description": org.get("description"),
                    "website": org.get("website"),
                    "status": org["status"],
                }

            rev_data = None
            if rev:
                rev_data = {
                    "id": str(rev["id"]),
                    "opportunity_id": str(opp["id"]),
                    "revision": rev["revision"],
                    "title": rev["title"],
                    "description": rev["description"],
                    "region": rev["region"],
                    "work_mode": rev["work_mode"],
                    "eligibility": rev["eligibility"],
                    "program_required": rev.get("program_required"),
                    "contract_type": rev["contract_type"],
                    "is_paid": rev["is_paid"],
                    "salary_min": float(rev["salary_min"]) if rev.get("salary_min") is not None else None,
                    "salary_max": float(rev["salary_max"]) if rev.get("salary_max") is not None else None,
                    "currency": rev["currency"],
                    "salary_period": rev.get("salary_period"),
                    "salary_basis": rev.get("salary_basis"),
                    "start_date": rev["start_date"].isoformat() if rev.get("start_date") else None,
                    "end_date": rev["end_date"].isoformat() if rev.get("end_date") else None,
                    "schedule_policy": rev["schedule_policy"],
                    "shift_match_mode": rev["shift_match_mode"],
                    "published_at": rev["published_at"].isoformat() if rev.get("published_at") else None,
                }

            return {
                "contract_id": "API-005",
                "id": str(opp["id"]),
                "organization_id": str(opp["organization_id"]),
                "kind": opp["kind"],
                "status": opp["status"],
                "capacity": capacity,
                "occupied_count": occupied_count,
                "vacancies_available": vacancies_available,
                "published_at": opp["published_at"].isoformat() if opp.get("published_at") else None,
                "expires_at": opp["expires_at"].isoformat() if opp.get("expires_at") else None,
                "closed_at": opp["closed_at"].isoformat() if opp.get("closed_at") else None,
                "revision": rev_data,
                "organization": org_data,
                "skills": skills_list,
                "shifts": shifts_list,
            }

    def search_public_opportunities(
        self,
        *,
        region: str | None = None,
        kind: str | None = None,
        is_paid: bool | None = None,
        min_hourly_pay: int | None = None,
        schedule_policy: str | None = None,
        query: str | None = None,
        skill_id: str | None = None,
        limit: int = 20,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Canonical API-001: Public opportunity search and discovery catalog (`CAP-001`, `PUBLIC_SEARCH`).
        
        Strict invariants:
        - Only returns opportunities with status == 'PUBLISHED', closed_at IS NULL, and (expires_at IS NULL OR expires_at > now()).
        - Owning organization must have status == 'VERIFIED'.
        - Real-time vacancies_available = max(0, capacity - occupied_count).
        - Stable Keyset cursor pagination over (published_at DESC, id DESC).
        """
        valid_limit = max(1, min(100, int(limit)))
        with transaction() as conn:
            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")
            t_org = table("organizations")

            stmt = (
                select(
                    t_opp.c.id.label("opp_id"),
                    t_opp.c.organization_id,
                    t_opp.c.kind.label("opp_kind"),
                    t_opp.c.capacity,
                    t_opp.c.occupied_count,
                    t_opp.c.published_at,
                    t_opp.c.expires_at,
                    t_rev.c.id.label("rev_id"),
                    t_rev.c.title,
                    t_rev.c.description,
                    t_rev.c.region.label("rev_region"),
                    t_rev.c.work_mode,
                    t_rev.c.contract_type,
                    t_rev.c.is_paid,
                    t_rev.c.salary_min,
                    t_rev.c.salary_max,
                    t_rev.c.currency,
                    t_rev.c.schedule_policy,
                    t_org.c.legal_name.label("org_legal_name"),
                    t_org.c.public_name.label("org_public_name"),
                    t_org.c.region.label("org_region"),
                )
                .select_from(
                    t_opp.join(t_rev, t_opp.c.current_revision_id == t_rev.c.id)
                    .join(t_org, t_opp.c.organization_id == t_org.c.id)
                )
                .where(
                    t_opp.c.status == "PUBLISHED",
                    t_opp.c.closed_at.is_(None),
                    or_(t_opp.c.expires_at.is_(None), t_opp.c.expires_at > now()),
                    t_org.c.status == "VERIFIED",
                )
            )

            # Optional filter: region
            if region:
                reg_clean = str(region).strip()
                stmt = stmt.where(
                    or_(t_org.c.region.ilike(f"%{reg_clean}%"), t_rev.c.region.ilike(f"%{reg_clean}%"))
                )

            # Optional filter: kind
            if kind:
                stmt = stmt.where(t_opp.c.kind == str(kind).strip())

            # Optional filter: is_paid
            if is_paid is not None:
                stmt = stmt.where(t_rev.c.is_paid == bool(is_paid))

            # Optional filter: min_hourly_pay (strictly for hourly positions)
            if min_hourly_pay is not None:
                stmt = stmt.where(
                    and_(
                        t_rev.c.salary_period == "HOUR",
                        or_(
                            t_rev.c.salary_min >= min_hourly_pay,
                            t_rev.c.salary_max >= min_hourly_pay,
                        ),
                    )
                )

            # Optional filter: schedule_policy
            if schedule_policy:
                stmt = stmt.where(t_rev.c.schedule_policy == schedule_policy)

            # Optional filter: query (title or description)
            if query:
                q_clean = str(query).strip()
                stmt = stmt.where(
                    or_(
                        t_rev.c.title.ilike(f"%{q_clean}%"),
                        t_rev.c.description.ilike(f"%{q_clean}%"),
                    )
                )

            # Optional filter: skill_id
            if skill_id:
                try:
                    s_uuid = str(UUID(str(skill_id)))
                    t_opp_skills = table("opportunity_skills")
                    stmt = stmt.where(
                        t_rev.c.id.in_(
                            select(t_opp_skills.c.revision_id).where(t_opp_skills.c.skill_id == s_uuid)
                        )
                    )
                except (ValueError, TypeError, AttributeError):
                    pass

            # Keyset cursor pagination: (published_at DESC, id DESC)
            if after:
                try:
                    decoded = base64.b64decode(after.encode("utf-8")).decode("utf-8")
                    after_ts_str, after_id_str = decoded.split("|", 1)
                    after_ts = datetime.fromisoformat(after_ts_str)
                    after_id = str(UUID(after_id_str))
                except Exception as exc:
                    raise OpportunityConstraintError(
                        "INVALID_CURSOR",
                        "Noto'g'ri yoki buzilgan sahifalash kursori",
                        status_code=400,
                    ) from exc

                stmt = stmt.where(
                    or_(
                        t_opp.c.published_at < after_ts,
                        and_(t_opp.c.published_at == after_ts, t_opp.c.id < after_id),
                    )
                )

            stmt = stmt.order_by(t_opp.c.published_at.desc(), t_opp.c.id.desc()).limit(valid_limit + 1)
            rows = conn.execute(stmt).mappings().all()

            has_more = len(rows) > valid_limit
            items_rows = rows[:valid_limit]

            items = []
            for r in items_rows:
                capacity = int(r["capacity"] or 0)
                occupied = int(r["occupied_count"] or 0)
                vacancies = max(0, capacity - occupied)
                items.append({
                    "id": str(r["opp_id"]),
                    "organization_id": str(r["organization_id"]),
                    "organization_name": r["org_public_name"] or r["org_legal_name"],
                    "organization_region": r["org_region"],
                    "title": r["title"],
                    "description": r["description"],
                    "region": r["rev_region"],
                    "kind": r["opp_kind"],
                    "work_mode": r["work_mode"],
                    "contract_type": r["contract_type"],
                    "is_paid": bool(r["is_paid"]),
                    "salary_min": float(r["salary_min"]) if r["salary_min"] is not None else None,
                    "salary_max": float(r["salary_max"]) if r["salary_max"] is not None else None,
                    "currency": r["currency"] or "UZS",
                    "schedule_policy": r["schedule_policy"],
                    "capacity": capacity,
                    "occupied_count": occupied,
                    "vacancies_available": vacancies,
                    "published_at": r["published_at"].isoformat() if r["published_at"] else None,
                    "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
                })

            next_after = None
            if has_more and items_rows:
                last = items_rows[-1]
                last_pub = last["published_at"].isoformat() if last["published_at"] else ""
                last_id = str(last["opp_id"])
                next_after = base64.b64encode(f"{last_pub}|{last_id}".encode("utf-8")).decode("utf-8")

            return {
                "contract_id": "API-001",
                "items": items,
                "limit": valid_limit,
                "has_more": has_more,
                "next_after": next_after,
            }


opportunity_service = OpportunityMatchingService()
