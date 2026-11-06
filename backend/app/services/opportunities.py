"""Opportunities, Revisions (`contract_type` & compensation matrix `INV-03`), Shift Groups (`group_code` `INV-02`), Quota Enforcement (`INV-04`, `AC-042`, `FIX-06`), and `API-003` Matching Engine (`AC-039`, `REV-002`) (S2.4.1)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.api.v1.billing import billing_service
from app.services.availability import (
    CandidateAvailabilityService,
    availability_service,
    ranges_overlap,
    validate_minute_bounds,
)
from app.services.billing import BillingInvariantError

VALID_CONTRACT_TYPES: frozenset[str] = frozenset(
    {
        "LABOR_PART_TIME",
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
            contract_type in ("LABOR_PART_TIME", "PAID_INTERNSHIP_CONTRACT")
            and hourly_pay is not None
            and hourly_pay > 0
            and stipend_amount is None
            and fee_terms_note is None
        )
    elif compensation_type == "STIPEND":
        valid = (
            contract_type == "PAID_INTERNSHIP_CONTRACT"
            and stipend_amount is not None
            and stipend_amount > 0
            and hourly_pay is None
            and fee_terms_note is None
        )
    elif compensation_type == "UNPAID_ACADEMIC":
        valid = (
            opportunity_kind == "ACADEMIC_INTERNSHIP"
            and contract_type == "UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT"
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


@dataclass
class OpportunityMatchingService:
    """Manages `opportunities`, `opportunity_revisions`, `opportunity_shifts`, and `API-003` feed matching (`AC-039`)."""

    avail_svc: CandidateAvailabilityService = field(default_factory=lambda: availability_service)
    opportunities: dict[str, dict[str, Any]] = field(default_factory=dict)
    revisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    shifts: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_opportunity_revision(
        self,
        *,
        organization_id: str,
        title: str,
        opportunity_kind: str,
        contract_type: str,
        compensation_type: str,
        hourly_pay: int | None = None,
        stipend_amount: int | None = None,
        fee_terms_note: str | None = None,
        published: bool = True,
    ) -> dict[str, Any]:
        """Create an `opportunities` + `opportunity_revisions` pair after validating `INV-03` (`AC-039`) and `INV-04` quota (`FIX-06`, `REV-002`)."""
        validate_compensation_contract_matrix(
            opportunity_kind=opportunity_kind,
            contract_type=contract_type,
            compensation_type=compensation_type,
            hourly_pay=hourly_pay,
            stipend_amount=stipend_amount,
            fee_terms_note=fee_terms_note,
        )
        opp_id = str(uuid4())
        rev_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        effective_published = False
        if published:
            if organization_id in billing_service._org_active_entitlement:
                try:
                    billing_service.publish_opportunity_with_quota(
                        organization_id=organization_id,
                        opportunity_id=opp_id,
                        actor_user_id="system",
                    )
                    effective_published = True
                except BillingInvariantError as exc:
                    raise OpportunityConstraintError(
                        code="CONCURRENT_QUOTA_OR_ENTITLEMENT_ERROR",
                        message=str(exc),
                        status_code=409,
                        sqlstate="23514",
                    ) from exc
            else:
                total_for_org = sum(
                    1
                    for o in self.opportunities.values()
                    if o["organization_id"] == organization_id
                )
                if total_for_org >= 5:
                    raise OpportunityConstraintError(
                        code="CONCURRENT_QUOTA_REACHED",
                        message=f"INV-04 / AC-042: Organization '{organization_id}' cannot exceed 5 opportunity slots without active entitlement.",
                        status_code=409,
                        sqlstate="23514",
                    )
                effective_published = False

        opp = {
            "id": opp_id,
            "organization_id": organization_id,
            "current_revision_id": rev_id,
            "status": "PUBLISHED" if effective_published else "DRAFT",
            "created_at": now,
        }
        rev = {
            "id": rev_id,
            "opportunity_id": opp_id,
            "revision": 1,
            "title": title,
            "opportunity_kind": opportunity_kind,
            "contract_type": contract_type,
            "compensation_type": compensation_type,
            "hourly_pay": hourly_pay,
            "stipend_amount": stipend_amount,
            "fee_terms_note": fee_terms_note,
            "published_at": now if effective_published else None,
            "created_at": now,
        }
        self.opportunities[opp_id] = opp
        self.revisions[rev_id] = rev
        return dict(rev)

    def publish_opportunity_api_081(
        self,
        *,
        opportunity_id: str,
        actor_user_id: str = "system",
    ) -> dict[str, Any]:
        """API-081 (`POST /api/v1/opportunities/{id}/publish`): Enforce active entitlement & quota (`INV-04`, `AC-042`)."""
        opp = self.opportunities.get(opportunity_id)
        if not opp:
            raise OpportunityConstraintError("OPPORTUNITY_NOT_FOUND", "Vakansiya topilmadi", status_code=404)

        try:
            quota_res = billing_service.publish_opportunity_with_quota(
                organization_id=opp["organization_id"],
                opportunity_id=opportunity_id,
                actor_user_id=actor_user_id,
            )
        except BillingInvariantError as exc:
            raise OpportunityConstraintError(
                code="CONCURRENT_QUOTA_OR_ENTITLEMENT_ERROR",
                message=str(exc),
                status_code=409,
                sqlstate="23514",
            ) from exc

        now = datetime.now(timezone.utc).isoformat()
        opp["status"] = "PUBLISHED"
        rev_id = opp["current_revision_id"]
        if rev_id in self.revisions:
            self.revisions[rev_id]["published_at"] = now
        return {
            "contract_id": "API-081",
            "opportunity_id": opportunity_id,
            "status": "PUBLISHED",
            "quota": quota_res,
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

        shift_id = str(uuid4())
        record = {
            "id": shift_id,
            "revision_id": revision_id,
            "group_code": group_code,
            "weekday": weekday,
            "start_minute": start_minute,
            "end_minute": end_minute,
            "minute_range": f"[{start_minute},{end_minute})",
            "is_required": is_required,
        }
        self.shifts[shift_id] = record
        return dict(record)

    def match_candidate_feed_api_003(
        self,
        *,
        candidate_id: str,
        schedule_match_mode: str = "ALL_SHIFTS_IN_GROUP",
        check_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """API-003 (`GET /api/v1/candidate/feed` & `/api/v1/opportunities/feed`) deterministic schedule matching (`AC-039`, `REV-002`).

        A shift `group_code` is covered only when all required shifts inside that `group_code` are covered (`all(shift_matches)`).
        - `ANY_SHIFT_IN_GROUP`: matches when at least one complete `group_code` is covered (`len(matched_groups) >= 1`).
        - `ALL_SHIFTS_IN_GROUP`: matches when all `group_code`s of the opportunity are completely covered (`len(matched_groups) == len(by_group)`).
        """
        if schedule_match_mode not in ("ALL_SHIFTS_IN_GROUP", "ANY_SHIFT_IN_GROUP"):
            raise OpportunityConstraintError(
                code="INVALID_SCHEDULE_MATCH_MODE",
                message="schedule_match_mode faqat ALL_SHIFTS_IN_GROUP yoki ANY_SHIFT_IN_GROUP bo'lishi mumkin",
                status_code=422,
            )

        matched: list[dict[str, Any]] = []
        for opp in self.opportunities.values():
            if opp["status"] != "PUBLISHED":
                continue
            rev_id = opp["current_revision_id"]
            rev = self.revisions[rev_id]
            rev_shifts = [s for s in self.shifts.values() if s["revision_id"] == rev_id]
            if not rev_shifts:
                continue

            by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for s in rev_shifts:
                by_group[s["group_code"]].append(s)

            matched_groups: list[str] = []
            for gcode, group_shifts in sorted(by_group.items()):
                shift_matches = [
                    self.avail_svc.is_candidate_available_for_shift(
                        candidate_id=candidate_id,
                        weekday=s["weekday"],
                        start_minute=s["start_minute"],
                        end_minute=s["end_minute"],
                        check_date=check_date,
                    )
                    for s in group_shifts
                ]
                if all(shift_matches):
                    matched_groups.append(gcode)

            is_opportunity_match = (
                len(matched_groups) == len(by_group)
                if schedule_match_mode == "ALL_SHIFTS_IN_GROUP"
                else len(matched_groups) >= 1
            )

            if is_opportunity_match and matched_groups:
                matched.append(
                    {
                        "opportunity_id": opp["id"],
                        "revision_id": rev_id,
                        "title": rev["title"],
                        "contract_type": rev["contract_type"],
                        "compensation_type": rev["compensation_type"],
                        "matched_group_codes": matched_groups,
                        "schedule_match_mode": schedule_match_mode,
                    }
                )
        return matched


opportunity_service = OpportunityMatchingService()
