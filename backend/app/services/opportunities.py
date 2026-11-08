"""Opportunities, Revisions (`contract_type` & compensation matrix `INV-03`), Shift Groups (`group_code` `INV-02`), Quota Enforcement (`INV-04`, `AC-042`, `FIX-06`), and `API-003` Matching Engine (`AC-039`, `REV-002`) (S2.4.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.api.v1.billing import billing_service
from app.db.storage import table, transaction, now
from app.services.placements import get_row, insert_row
from app.api.dependencies import ActorContext, require_org
from sqlalchemy import select
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


opportunity_service = OpportunityMatchingService()
