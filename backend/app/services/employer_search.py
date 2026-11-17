"""Employer Candidate Search Service (FlexBridge Milestone 2 / API-087).

Provides parameterized, PgBouncer-safe candidate talent search for employers:
- Multi-skill filtering (ANY / ALL modes) with proficiency levels and verification checks.
- Regional filtering across Uzbekistan administrative territories.
- Schedule shift matching (MORNING, AFTERNOON, EVENING, FULL_DAY, FLEXIBLE) and specific weekdays.
- Deterministic schedule compatibility matching based on 28-day snapshot and O'zR MK 118-modda bounds.
- Opportunity shift matching if opportunity_id is supplied.
- Keyset cursor pagination and multi-dimensional facets (regions, skills, shifts).
- Strict privacy: excludes PRIVATE candidate profiles and masks raw PII.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.engine import Connection

from app.api.dependencies import ActorContext
from app.db.storage import read_snapshot, table
from app.services.schedule import AvailabilitySnapshot, local_today


class EmployerSearchError(Exception):
    """Base exception for employer candidate search errors."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


LEVEL_HIERARCHY: dict[str, int] = {
    "BEGINNER": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
}

SHIFT_PRESETS: dict[str, tuple[int, int]] = {
    "MORNING": (480, 780),      # 08:00 - 13:00 (5 hours, 300 min)
    "AFTERNOON": (780, 1080),   # 13:00 - 18:00 (5 hours, 300 min)
    "EVENING": (1080, 1320),    # 18:00 - 22:00 (4 hours, 240 min)
    "FULL_DAY": (540, 1080),    # 09:00 - 18:00 (9 hours, 540 min)
}


def mask_display_name(name: str) -> str:
    """Masks candidate surname into initial to prevent raw enumeration while keeping clarity."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return name


def encode_cursor(created_at: datetime, candidate_id: str) -> str:
    payload = f"{created_at.isoformat()}|{candidate_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def _safe_uuid(val: Any) -> UUID | None:
    """Safely converts string or object to UUID, returning None on parse failure."""
    try:
        return UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        dt_str, cid = raw.split("|", 1)
        parsed_dt = datetime.fromisoformat(dt_str)
        if _safe_uuid(cid) is None:
            raise ValueError("Malformed UUID in pagination cursor")
        return parsed_dt, cid
    except Exception as exc:
        raise EmployerSearchError("INVALID_CURSOR", "Malformed pagination cursor", 422) from exc


class EmployerCandidateSearchService:
    """Service handling talent discovery for authenticated employer representatives."""

    def verify_employer_authorization(self, conn: Connection, actor: ActorContext) -> None:
        """Verifies that the actor has an active employer organization role (OWNER, HR, HOST_COORDINATOR, MENTOR)."""
        if actor.has_any_role("OWNER", "HR", "HOST_COORDINATOR", "MENTOR"):
            return

        t_mem = table("org_memberships")
        t_ogrants = table("org_role_grants")
        t_rcat = table("role_catalog")

        active_grant = conn.execute(
            select(t_rcat.c.code)
            .select_from(
                t_mem.join(t_ogrants, t_ogrants.c.membership_id == t_mem.c.id)
                .join(t_rcat, t_ogrants.c.role_id == t_rcat.c.id)
            )
            .where(
                t_mem.c.user_id == actor.user_id,
                t_mem.c.status == "ACTIVE",
                t_mem.c.revoked_at.is_(None),
                t_ogrants.c.revoked_at.is_(None),
                t_rcat.c.scope_kind == "ORG",
                t_rcat.c.code.in_(("OWNER", "HR", "HOST_COORDINATOR", "MENTOR")),
            )
        ).first()

        if not active_grant:
            raise EmployerSearchError(
                "EMPLOYER_ROLE_REQUIRED",
                "Faqat tasdiqlangan ish beruvchi tashkilot vakillari nomzodlar qidiruvidan foydalanishi mumkin",
                403,
            )

    def search_candidates(
        self,
        actor: ActorContext,
        *,
        q: str | None = None,
        skills: list[str] | None = None,
        skill_match_mode: str = "ANY",
        min_skill_level: str | None = None,
        verified_skills_only: bool = False,
        region: str | None = None,
        experience_min_months: int | None = None,
        experience_max_months: int | None = None,
        shift: str | None = None,
        weekdays: list[int] | None = None,
        opportunity_id: str | None = None,
        verified_student_only: bool = False,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Search candidates using repeatable-read snapshot over PgBouncer."""
        if not 1 <= limit <= 100:
            raise EmployerSearchError("INVALID_LIMIT", "Limit 1 va 100 oralig'ida bo'lishi kerak", 422)

        if skill_match_mode not in ("ANY", "ALL"):
            raise EmployerSearchError("INVALID_MATCH_MODE", "skill_match_mode 'ANY' yoki 'ALL' bo'lishi kerak", 422)

        if min_skill_level and min_skill_level not in LEVEL_HIERARCHY:
            raise EmployerSearchError("INVALID_SKILL_LEVEL", f"Noma'lum mahorat darajasi: {min_skill_level}", 422)

        if shift and shift not in ("MORNING", "AFTERNOON", "EVENING", "FULL_DAY", "FLEXIBLE"):
            raise EmployerSearchError("INVALID_SHIFT", f"Noma'lum smena: {shift}", 422)

        cleaned_skills = list(dict.fromkeys([s.strip().lower() for s in (skills or []) if s.strip()]))
        cleaned_weekdays = [int(w) for w in (weekdays or []) if 1 <= int(w) <= 7]

        with read_snapshot() as conn:
            self.verify_employer_authorization(conn, actor)

            t_cand = table("candidate_profiles")
            t_users = table("users")
            t_cskills = table("candidate_skills")
            t_skills = table("skills")
            t_enroll = table("enrollments")
            t_rules = table("availability_rules")

            # Base query: Only active users with PUBLIC profiles
            query = (
                select(
                    t_cand.c.id.label("candidate_id"),
                    t_cand.c.user_id,
                    t_cand.c.headline,
                    t_cand.c.region,
                    t_cand.c.bio,
                    t_cand.c.experience_months,
                    t_cand.c.cv_file_id,
                    t_cand.c.created_at,
                    t_users.c.display_name,
                )
                .select_from(t_cand.join(t_users, t_cand.c.user_id == t_users.c.id))
                .where(
                    t_cand.c.visibility != "PRIVATE",
                    t_users.c.status == "ACTIVE",
                )
            )

            # 1. Text Search Filter (q)
            if q and q.strip():
                kw = f"%{q.strip().lower()}%"
                query = query.where(
                    or_(
                        func.lower(t_cand.c.headline).like(kw),
                        func.lower(t_cand.c.bio).like(kw),
                        func.lower(t_users.c.display_name).like(kw),
                    )
                )

            # 2. Region Filter
            if region and region.strip():
                query = query.where(func.lower(t_cand.c.region) == region.strip().lower())

            # 3. Experience Range Filter
            if experience_min_months is not None:
                query = query.where(t_cand.c.experience_months >= experience_min_months)
            if experience_max_months is not None:
                query = query.where(t_cand.c.experience_months <= experience_max_months)

            # 4. Verified Student Filter
            if verified_student_only:
                verified_enrollment_cands = (
                    select(t_enroll.c.candidate_id)
                    .where(t_enroll.c.status == "VERIFIED")
                    .distinct()
                )
                query = query.where(t_cand.c.id.in_(verified_enrollment_cands))

            # 5. Skills Filter (ANY vs ALL, level hierarchy, verification)
            if cleaned_skills:
                parsed_skill_uuids = [u for s in cleaned_skills if (u := _safe_uuid(s)) is not None]
                skill_conditions = [
                    or_(
                        func.lower(t_skills.c.code).in_(cleaned_skills),
                        t_skills.c.id.in_(parsed_skill_uuids or [UUID(int=0)]),
                    )
                ]

                # Minimum skill level
                if min_skill_level:
                    min_rank = LEVEL_HIERARCHY[min_skill_level]
                    allowed_levels = [lvl for lvl, rank in LEVEL_HIERARCHY.items() if rank >= min_rank]
                    skill_conditions.append(t_cskills.c.level.in_(allowed_levels))

                # Verified skills only
                if verified_skills_only:
                    skill_conditions.append(t_cskills.c.verification_case_id.is_not(None))

                if skill_match_mode == "ALL":
                    # Candidate must possess ALL requested skills
                    skills_subquery = (
                        select(t_cskills.c.candidate_id)
                        .select_from(t_cskills.join(t_skills, t_cskills.c.skill_id == t_skills.c.id))
                        .where(and_(*skill_conditions))
                        .group_by(t_cskills.c.candidate_id)
                        .having(func.count(func.distinct(t_skills.c.id)) >= len(cleaned_skills))
                    )
                    query = query.where(t_cand.c.id.in_(skills_subquery))
                else:
                    # ANY mode
                    skills_subquery = (
                        select(t_cskills.c.candidate_id)
                        .select_from(t_cskills.join(t_skills, t_cskills.c.skill_id == t_skills.c.id))
                        .where(and_(*skill_conditions))
                        .distinct()
                    )
                    query = query.where(t_cand.c.id.in_(skills_subquery))

            # 6. Schedule weekday pre-filtering in SQL if requested
            if cleaned_weekdays:
                weekday_cands = (
                    select(t_rules.c.candidate_id)
                    .where(
                        t_rules.c.is_active.is_(True),
                        t_rules.c.weekday.in_(cleaned_weekdays),
                    )
                    .distinct()
                )
                query = query.where(t_cand.c.id.in_(weekday_cands))

            # Keyset pagination cursor
            if cursor:
                cursor_dt, cursor_id = decode_cursor(cursor)
                query = query.where(
                    or_(
                        t_cand.c.created_at < cursor_dt,
                        and_(t_cand.c.created_at == cursor_dt, t_cand.c.id < cursor_id),
                    )
                )

            query = query.order_by(desc(t_cand.c.created_at), desc(t_cand.c.id)).limit(limit + 1)
            raw_rows = list(conn.execute(query).mappings())

            has_more = len(raw_rows) > limit
            page_rows = raw_rows[:limit]
            next_cursor = (
                encode_cursor(page_rows[-1]["created_at"], str(page_rows[-1]["candidate_id"]))
                if has_more and page_rows
                else None
            )

            # Candidate IDs to enrich
            cids = [r["candidate_id"] for r in page_rows]

            # Fetch Skills for candidates
            cand_skills_map: dict[str, list[dict[str, Any]]] = {str(cid): [] for cid in cids}
            if cids:
                skills_q = (
                    select(
                        t_cskills.c.candidate_id,
                        t_cskills.c.skill_id,
                        t_cskills.c.level,
                        t_cskills.c.verification_case_id,
                        t_skills.c.code,
                        t_skills.c.name_uz,
                        t_skills.c.name_ru,
                    )
                    .select_from(t_cskills.join(t_skills, t_cskills.c.skill_id == t_skills.c.id))
                    .where(t_cskills.c.candidate_id.in_(cids))
                )
                for srow in conn.execute(skills_q).mappings():
                    cand_skills_map[str(srow["candidate_id"])].append(
                        {
                            "skill_id": str(srow["skill_id"]),
                            "code": srow["code"],
                            "name_uz": srow["name_uz"],
                            "name_ru": srow["name_ru"],
                            "level": srow["level"],
                            "verified": srow["verification_case_id"] is not None,
                        }
                    )

            # Fetch University Enrollments for candidates
            t_inst = table("institutions")
            cand_univ_map: dict[str, dict[str, Any] | None] = {str(cid): None for cid in cids}
            if cids:
                univ_q = (
                    select(
                        t_enroll.c.candidate_id,
                        t_enroll.c.institution_id,
                        t_enroll.c.program,
                        t_enroll.c.status,
                        t_inst.c.name.label("institution_name"),
                    )
                    .select_from(t_enroll.join(t_inst, t_enroll.c.institution_id == t_inst.c.id))
                    .where(t_enroll.c.candidate_id.in_(cids))
                    .order_by(
                        desc(t_enroll.c.status == "VERIFIED"),
                        desc(t_enroll.c.created_at),
                    )
                )
                for urow in conn.execute(univ_q).mappings():
                    cid_str = str(urow["candidate_id"])
                    if cand_univ_map.get(cid_str) is None:
                        cand_univ_map[cid_str] = {
                            "institution_id": str(urow["institution_id"]),
                            "institution_name": urow["institution_name"],
                            "program": urow["program"],
                            "status": urow["status"],
                        }

            # Fetch Availability Rules & Evaluate Compatibility
            today = local_today()
            t_ex = table("availability_exceptions")

            # Load opportunity shifts if opportunity_id is passed
            opp_shifts: list[dict[str, Any]] = []
            if opportunity_id:
                t_opp = table("opportunities")
                t_oshifts = table("opportunity_shifts")
                opp_row = conn.execute(
                    select(t_opp.c.current_revision_id).where(t_opp.c.id == opportunity_id)
                ).mappings().first()
                if opp_row and opp_row["current_revision_id"]:
                    opp_shifts = list(
                        conn.execute(
                            select(t_oshifts).where(
                                t_oshifts.c.revision_id == opp_row["current_revision_id"]
                            )
                        ).mappings()
                    )

            items: list[dict[str, Any]] = []
            facet_regions: dict[str, int] = {}
            facet_skills: dict[str, int] = {}
            facet_shifts: dict[str, int] = {"MORNING": 0, "AFTERNOON": 0, "EVENING": 0, "FULL_DAY": 0}

            for row in page_rows:
                cid_str = str(row["candidate_id"])
                reg = row["region"]
                if reg:
                    facet_regions[reg] = facet_regions.get(reg, 0) + 1

                for sk in cand_skills_map.get(cid_str, []):
                    code = sk["code"]
                    facet_skills[code] = facet_skills.get(code, 0) + 1

                # Load availability rules for candidate
                rules = list(
                    conn.execute(
                        select(t_rules).where(
                            t_rules.c.candidate_id == row["candidate_id"],
                            t_rules.c.is_active.is_(True),
                        )
                    ).mappings()
                )

                exceptions = list(
                    conn.execute(
                        select(t_ex).where(
                            t_ex.c.candidate_id == row["candidate_id"],
                            t_ex.c.local_date >= today,
                            t_ex.c.local_date < today + timedelta(days=28),
                        )
                    ).mappings()
                )

                snapshot = AvailabilitySnapshot(rules, exceptions)

                # Summarize schedule
                free_weekdays = sorted(list({r["weekday"] for r in rules}))
                total_weekly_minutes = sum(r["end_minute"] - r["start_minute"] for r in rules)
                total_weekly_hours = round(total_weekly_minutes / 60, 1)

                available_shifts: list[str] = []
                for s_name, (s_start, s_end) in SHIFT_PRESETS.items():
                    # Check if candidate has any active weekday covering this shift
                    covers_preset = False
                    for w in free_weekdays:
                        # Find rules on that weekday
                        w_rules = [r for r in rules if r["weekday"] == w]
                        for wr in w_rules:
                            if wr["start_minute"] <= s_start and wr["end_minute"] >= s_end:
                                covers_preset = True
                                break
                        if covers_preset:
                            break
                    if covers_preset:
                        available_shifts.append(s_name)
                        facet_shifts[s_name] = facet_shifts.get(s_name, 0) + 1

                # Schedule match calculation
                schedule_match = self._compute_schedule_match(
                    snapshot=snapshot,
                    rules=rules,
                    shift=shift,
                    weekdays=cleaned_weekdays,
                    opp_shifts=opp_shifts,
                    total_weekly_hours=total_weekly_hours,
                )

                # Filter by shift if shift parameter was specified (post-filtering for accuracy)
                if shift and shift != "FLEXIBLE":
                    if shift not in available_shifts:
                        # Exclude from items if strict shift specified
                        continue

                items.append(
                    {
                        "candidate_id": cid_str,
                        "user_id": str(row["user_id"]),
                        "display_name": mask_display_name(row["display_name"]),
                        "headline": row["headline"],
                        "region": row["region"],
                        "bio": row["bio"] or "",
                        "experience_months": row["experience_months"],
                        "has_cv": row["cv_file_id"] is not None,
                        "cv_file_id": str(row["cv_file_id"]) if row["cv_file_id"] else None,
                        "university": cand_univ_map.get(cid_str),
                        "skills": cand_skills_map.get(cid_str, []),
                        "schedule_summary": {
                            "free_weekdays": free_weekdays,
                            "available_shifts": available_shifts,
                            "total_weekly_hours": total_weekly_hours,
                            "rules": [
                                {
                                    "weekday": r["weekday"],
                                    "start_minute": r["start_minute"],
                                    "end_minute": r["end_minute"],
                                }
                                for r in rules
                            ],
                        },
                        "schedule_match": schedule_match,
                    }
                )

            return {
                "contract_id": "API-087",
                "total": len(items),
                "items": items,
                "next_cursor": next_cursor,
                "facets": {
                    "regions": facet_regions,
                    "skills": facet_skills,
                    "shifts": facet_shifts,
                },
            }

    def _compute_schedule_match(
        self,
        snapshot: AvailabilitySnapshot,
        rules: list[Any],
        shift: str | None,
        weekdays: list[int],
        opp_shifts: list[Any],
        total_weekly_hours: float,
    ) -> dict[str, Any]:
        """Calculates deterministic schedule compatibility and O'zR MK 118 compliance."""
        max_daily_minutes = max((r["end_minute"] - r["start_minute"] for r in rules), default=0)
        labor_code_compliant = (total_weekly_hours <= 36.0) and (max_daily_minutes <= 480)
        daily_overrun = max_daily_minutes > 480

        if opp_shifts:
            # Opportunity Shift Matching
            matched_count = 0
            today = local_today()
            for s in opp_shifts:
                day = today + timedelta(days=(s["weekday"] - today.isoweekday()) % 7)
                if snapshot.covers(day, s["start_minute"], s["end_minute"]):
                    matched_count += 1
            score = int((matched_count / len(opp_shifts)) * 100) if opp_shifts else 0
            is_matched = score >= 80
            daily_note = " (Kunlik 8 soatlik limit oshgan)." if daily_overrun else ""
            return {
                "is_matched": is_matched,
                "score_percent": score,
                "shift_group_covered": score == 100,
                "labor_code_compliant": labor_code_compliant,
                "details": (
                    f"Vakansiya smenalari bo'yicha moslik: {score}%. "
                    f"O'zR MK 118-modda talablariga {'mos' if labor_code_compliant else 'nomutanosib'}."
                    f"{daily_note}"
                ),
            }

        if shift and shift in SHIFT_PRESETS:
            preset_start, preset_end = SHIFT_PRESETS[shift]
            matched_weekdays = 0
            check_days = weekdays if weekdays else [r["weekday"] for r in rules]
            unique_days = list(set(check_days))
            today = local_today()

            for w in unique_days:
                day = today + timedelta(days=(w - today.isoweekday()) % 7)
                if snapshot.covers(day, preset_start, preset_end):
                    matched_weekdays += 1

            score = int((matched_weekdays / len(unique_days)) * 100) if unique_days else 0
            is_matched = score > 0
            daily_note = " (Kunlik limit 8 soatdan oshgan)." if daily_overrun else ""
            return {
                "is_matched": is_matched,
                "score_percent": score,
                "shift_group_covered": score == 100,
                "labor_code_compliant": labor_code_compliant,
                "details": (
                    f"Tanlangan {shift} smenasi bo'yicha moslik: {score}%. "
                    f"Haftalik jami: {total_weekly_hours} soat (O'zR MK 118-modda).{daily_note}"
                ),
            }

        # Default summary compatibility
        score = 100 if rules else 0
        daily_note = " (Kunlik limit 8 soatdan oshgan)." if daily_overrun else ""
        compliance_text = "kafolatlangan" if labor_code_compliant else "nomutanosib"
        return {
            "is_matched": bool(rules),
            "score_percent": score,
            "shift_group_covered": bool(rules),
            "labor_code_compliant": labor_code_compliant,
            "details": f"Haftalik bo'sh vaqt: {total_weekly_hours} soat. O'zR MK 118-modda {compliance_text}.{daily_note}",
        }

    def get_candidate_detail(self, actor: ActorContext, candidate_id: str) -> dict[str, Any]:
        """Fetches full candidate profile detail for an authorized employer."""
        with read_snapshot() as conn:
            self.verify_employer_authorization(conn, actor)

            t_cand = table("candidate_profiles")
            t_users = table("users")
            t_cskills = table("candidate_skills")
            t_skills = table("skills")
            t_enroll = table("enrollments")
            t_inst = table("institutions")
            t_rules = table("availability_rules")

            cand = conn.execute(
                select(
                    t_cand.c.id.label("candidate_id"),
                    t_cand.c.user_id,
                    t_cand.c.headline,
                    t_cand.c.region,
                    t_cand.c.bio,
                    t_cand.c.experience_months,
                    t_cand.c.cv_file_id,
                    t_cand.c.created_at,
                    t_cand.c.visibility,
                    t_users.c.display_name,
                )
                .select_from(t_cand.join(t_users, t_cand.c.user_id == t_users.c.id))
                .where(t_cand.c.id == candidate_id, t_cand.c.visibility != "PRIVATE")
            ).mappings().first()

            if not cand:
                raise EmployerSearchError("CANDIDATE_NOT_FOUND", "Nomzod topilmadi yoki profili maxfiy", 404)

            # Skills (verified only when the candidate's own verification case was APPROVED)
            t_cases = table("verification_cases")
            skills = list(
                conn.execute(
                    select(
                        t_cskills.c.skill_id,
                        t_cskills.c.level,
                        t_cskills.c.verification_case_id,
                        t_skills.c.code,
                        t_skills.c.name_uz,
                        t_skills.c.name_ru,
                        t_cases.c.status.label("case_status"),
                        t_cases.c.candidate_id.label("case_candidate_id"),
                    )
                    .select_from(
                        t_cskills.join(t_skills, t_cskills.c.skill_id == t_skills.c.id)
                        .outerjoin(t_cases, t_cases.c.id == t_cskills.c.verification_case_id)
                    )
                    .where(t_cskills.c.candidate_id == candidate_id)
                ).mappings()
            )

            # Current, independently reviewed student status (same predicate as academic binding)
            student_verified = bool(conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM flexbridge.enrollments e "
                     "WHERE e.candidate_id=:cid AND flexbridge.enrollment_is_current(e.id))"),
                {"cid": str(candidate_id)},
            ).scalar())

            # University
            univ = conn.execute(
                select(
                    t_enroll.c.institution_id,
                    t_enroll.c.program,
                    t_enroll.c.status,
                    t_inst.c.name.label("institution_name"),
                )
                .select_from(t_enroll.join(t_inst, t_enroll.c.institution_id == t_inst.c.id))
                .where(t_enroll.c.candidate_id == candidate_id)
                .order_by(desc(t_enroll.c.status == "VERIFIED"), desc(t_enroll.c.created_at))
            ).mappings().first()

            # Rules
            rules = list(
                conn.execute(
                    select(t_rules).where(
                        t_rules.c.candidate_id == candidate_id,
                        t_rules.c.is_active.is_(True),
                    )
                ).mappings()
            )

            total_weekly_minutes = sum(r["end_minute"] - r["start_minute"] for r in rules)

            return {
                "contract_id": "API-087-DETAIL",
                "candidate_id": str(cand["candidate_id"]),
                "display_name": mask_display_name(cand["display_name"]),
                "headline": cand["headline"],
                "region": cand["region"],
                "bio": cand["bio"] or "",
                "experience_months": cand["experience_months"],
                "has_cv": cand["cv_file_id"] is not None,
                "cv_file_id": str(cand["cv_file_id"]) if cand["cv_file_id"] else None,
                "university": {
                    "institution_id": str(univ["institution_id"]),
                    "institution_name": univ["institution_name"],
                    "program": univ["program"],
                    "status": univ["status"],
                } if univ else None,
                "skills": [
                    {
                        "skill_id": str(s["skill_id"]),
                        "code": s["code"],
                        "name_uz": s["name_uz"],
                        "name_ru": s["name_ru"],
                        "level": s["level"],
                        "verified": s["case_status"] == "APPROVED"
                        and str(s["case_candidate_id"]) == str(candidate_id),
                    }
                    for s in skills
                ],
                "student_verified": student_verified,
                "resume": employer_resume_view(str(candidate_id)),
                "availability": {
                    "total_weekly_hours": round(total_weekly_minutes / 60, 1),
                    "rules": [
                        {
                            "weekday": r["weekday"],
                            "start_minute": r["start_minute"],
                            "end_minute": r["end_minute"],
                        }
                        for r in rules
                    ],
                },
            }


def employer_resume_view(candidate_id: str) -> dict[str, Any]:
    """Professional resume sections for employers; personal contacts are never included."""
    from app.db.storage import load_domain_record
    from app.services.candidate_resume_builder import RESUME_DETAILS_NAMESPACE

    stored = load_domain_record(RESUME_DETAILS_NAMESPACE, candidate_id) or {}
    career = dict(stored.get("career_preferences") or {})
    career.pop("telegram_username", None)
    return {
        "work_experiences": list(stored.get("work_experiences") or []),
        "achievements": list(stored.get("achievements") or []),
        "languages": list(stored.get("languages") or []),
        "education_details": dict(stored.get("education_details") or {}),
        "career_preferences": career,
    }


employer_candidate_search_service = EmployerCandidateSearchService()
