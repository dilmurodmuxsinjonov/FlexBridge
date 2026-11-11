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

    def get_opportunity_detail(self, opportunity_id: str, actor: ActorContext | None = None) -> dict[str, Any]:
        """Canonical API-005: Retrieve published immutable opportunity revision, wage, eligibility, shifts, skills, and organization details."""
        with transaction() as conn:
            t_opp = table("opportunities")
            opp = conn.execute(select(t_opp).where(t_opp.c.id == opportunity_id)).mappings().first()
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
            vacancies_available = max(0, capacity - occupied_count)

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


opportunity_service = OpportunityMatchingService()
