"""Candidate Profile and `int4range(start_minute, end_minute, '[)')` Availability Service (S2.3.1, FIX-09).

Enforces `INV-01` (`FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` section 3.1) and `TD-001` (`FIX-09`):
- Intervals use half-open `[start_minute, end_minute)` semantics (`0 <= start_minute < end_minute <= 1440`).
- `availability_rules`: no two active rules for the same `(candidate_id, weekday)` may overlap (`&&`).
- `availability_exceptions`: no two exceptions for the same `(candidate_id, exception_date)` may overlap (`&&`).
- Adjacent intervals (e.g. `[540, 720)` and `[720, 900)`) do NOT overlap under `[)` semantics, are allowed,
  and are merged (`[540, 900)`) when evaluating candidate shift availability (`R-13`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from sqlalchemy import select
from app.services.schedule import load_snapshot, local_today
from app.db.storage import table, transaction, now, read_snapshot
from app.services.placements import insert_row
from app.services.authority import account_authority
from app.api.dependencies import ActorContext
from typing import Any


class AvailabilityConstraintError(Exception):
    """Raised when an availability rule or exception violates `INV-01` range bounds or GiST `EXCLUDE`."""

    def __init__(self, code: str, message: str, status_code: int = 409, sqlstate: str = "23P01") -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.sqlstate = sqlstate


def ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    """Return True iff half-open intervals `[start_a, end_a)` and `[start_b, end_b)` overlap (`&&`)."""
    return max(start_a, start_b) < min(end_a, end_b)


def range_contains(outer_start: int, outer_end: int, inner_start: int, inner_end: int) -> bool:
    """Return True iff `[outer_start, outer_end) @> [inner_start, inner_end)`."""
    return outer_start <= inner_start and inner_end <= outer_end


def merge_adjacent_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Sort and merge adjacent (`a_end == b_start`) or overlapping (`a_end > b_start`) half-open intervals."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: (iv[0], iv[1]))
    merged: list[tuple[int, int]] = [ordered[0]]
    for start, end in ordered[1:]:
        cur_start, cur_end = merged[-1]
        if start <= cur_end:
            merged[-1] = (cur_start, max(cur_end, end))
        else:
            merged.append((start, end))
    return merged


def subtract_interval(intervals: list[tuple[int, int]], sub_start: int, sub_end: int) -> list[tuple[int, int]]:
    """Subtract `[sub_start, sub_end)` from a list of half-open intervals."""
    result: list[tuple[int, int]] = []
    for iv_start, iv_end in intervals:
        if sub_end <= iv_start or sub_start >= iv_end:
            result.append((iv_start, iv_end))
        else:
            if iv_start < sub_start:
                result.append((iv_start, sub_start))
            if sub_end < iv_end:
                result.append((sub_end, iv_end))
    return result


def validate_minute_bounds(start_minute: int, end_minute: int) -> None:
    if not (0 <= start_minute < end_minute <= 1440):
        raise AvailabilityConstraintError(
            code="INVALID_MINUTE_RANGE",
            message="start_minute va end_minute uchun 0 <= start_minute < end_minute <= 1440 sharti bajarilishi kerak",
            status_code=422,
            sqlstate="23514",
        )


@dataclass
class CandidateAvailabilityService:
    """Manages `availability_rules` (`DB-013`) and `availability_exceptions` (`DB-014`)."""

    def get_schedule(self, candidate_id, from_date=None, days=28):
        start = from_date or local_today()
        try:
            end = start + timedelta(days=days)
        except OverflowError as exc:
            raise AvailabilityConstraintError('INVALID_DATE_RANGE', 'Date range is too large', 422) from exc
        with read_snapshot():
            snapshot = load_snapshot(candidate_id, start, end)
        return {'candidate_id': candidate_id, 'timezone': 'Asia/Tashkent',
            'availability_revision': snapshot.revision,
            'rules': [dict(r) for r in snapshot.rules], 'exceptions': [dict(e) for e in snapshot.exceptions],
            'effective_days': [{'date': (start + timedelta(days=i)).isoformat(),
                'intervals': [{'start_minute': a, 'end_minute': b} for a, b in snapshot.intervals(start + timedelta(days=i))]}
                for i in range(days)]}

    def get_my_schedule(self, actor:ActorContext, from_date=None, days=28):
        from app.services.candidates import own_profile,candidate_transaction
        with candidate_transaction() as conn:
            profile=own_profile(conn,actor.user_id,'share')
            account_authority(conn,actor)
            return self.get_schedule(profile['id'],from_date,days)

    def replace_rules(self, actor:ActorContext, rules):
        from collections import defaultdict
        from app.services.candidates import own_profile, audit, candidate_transaction
        groups = defaultdict(list)
        for rule in rules:
            key = (rule['weekday'], rule['valid_from'], rule['valid_to'], rule['timezone'])
            groups[key].append((rule['start_minute'], rule['end_minute']))
        with candidate_transaction() as conn:
            profile = own_profile(conn, actor.user_id, True)
            account_authority(conn,actor)
            target = table('availability_rules')
            conn.execute(target.delete().where(target.c.candidate_id == profile['id']))
            for (weekday, valid_from, valid_to, timezone), intervals in groups.items():
                for start, end in merge_adjacent_intervals(intervals):
                    insert_row(conn, 'availability_rules', candidate_id=profile['id'], weekday=weekday,
                        valid_from=valid_from, valid_to=valid_to, timezone=timezone,
                        start_minute=start, end_minute=end, is_active=True)
            conn.execute(table('candidate_profiles').update().where(table('candidate_profiles').c.id == profile['id']).values(updated_at=now()))
            audit.append_audit_event(actor_id=actor.user_id, action='CANDIDATE_AVAILABILITY_REPLACED',
                entity_type='candidate_profile', entity_id=profile['id'])
            return self.get_schedule(profile['id'])

    def replace_exceptions(self, actor:ActorContext, from_date, to_date, exceptions):
        from collections import defaultdict
        from app.services.candidates import own_profile, audit, candidate_transaction
        groups = defaultdict(list)
        for exception in exceptions:
            groups[(exception['local_date'], exception['kind'])].append((exception['start_minute'], exception['end_minute']))
        with candidate_transaction() as conn:
            profile = own_profile(conn, actor.user_id, True)
            account_authority(conn,actor)
            target = table('availability_exceptions')
            conn.execute(target.delete().where(target.c.candidate_id == profile['id'],
                target.c.local_date >= from_date, target.c.local_date <= to_date))
            for (day, kind), intervals in groups.items():
                for start, end in merge_adjacent_intervals(intervals):
                    insert_row(conn, 'availability_exceptions', candidate_id=profile['id'], local_date=day,
                        kind=kind, start_minute=start, end_minute=end)
            conn.execute(table('candidate_profiles').update().where(table('candidate_profiles').c.id == profile['id']).values(updated_at=now()))
            audit.append_audit_event(actor_id=actor.user_id, action='CANDIDATE_EXCEPTIONS_REPLACED',
                entity_type='candidate_profile', entity_id=profile['id'])
            return self.get_schedule(profile['id'], from_date, (to_date - from_date).days + 1)

    def add_availability_rule(
        self,
        *,
        actor:ActorContext,
        candidate_id: str,
        weekday: int,
        start_minute: int,
        end_minute: int,
        is_active: bool = True,
    ) -> dict[str, Any]:
        """Insert a weekly availability rule enforcing `excl_availability_rules_no_overlap` (`INV-01`)."""
        if not (1 <= weekday <= 7):
            raise AvailabilityConstraintError(
                code="INVALID_WEEKDAY",
                message="weekday 1..7 oralig'ida bo'lishi shart",
                status_code=422,
                sqlstate="23514",
            )
        validate_minute_bounds(start_minute, end_minute)

        from app.services.candidates import own_profile,audit,candidate_transaction
        with candidate_transaction() as conn:
            profile=own_profile(conn,actor.user_id,True)
            if profile['id']!=candidate_id:
                raise AvailabilityConstraintError('CANDIDATE_SCOPE_FORBIDDEN','Use your own candidate profile',403)
            account_authority(conn,actor)
            row=insert_row(conn,'availability_rules',candidate_id=candidate_id,weekday=weekday,start_minute=start_minute,end_minute=end_minute,is_active=is_active,valid_from=local_today(),timezone='Asia/Tashkent')
            audit.append_audit_event(actor_id=actor.user_id,action='CANDIDATE_AVAILABILITY_RULE_CREATED',
                entity_type='candidate_profile',entity_id=profile['id'],metadata={'rule_id':row['id']})
            return row

    def add_availability_exception(
        self,
        *,
        actor:ActorContext,
        candidate_id: str,
        exception_date: str,
        start_minute: int,
        end_minute: int,
        kind: str = "UNAVAILABLE",
    ) -> dict[str, Any]:
        """Insert a date-specific availability exception enforcing `excl_availability_exceptions_no_overlap`."""
        if kind not in ("UNAVAILABLE", "AVAILABLE", "AVAILABLE_EXTRA"):
            raise AvailabilityConstraintError(
                code="INVALID_EXCEPTION_KIND",
                message="kind faqat UNAVAILABLE, AVAILABLE yoki AVAILABLE_EXTRA bo'lishi mumkin",
                status_code=422,
                sqlstate="23514",
            )
        validate_minute_bounds(start_minute, end_minute)

        from app.services.candidates import own_profile,audit,candidate_transaction
        with candidate_transaction() as conn:
            profile=own_profile(conn,actor.user_id,True)
            if profile['id']!=candidate_id:
                raise AvailabilityConstraintError('CANDIDATE_SCOPE_FORBIDDEN','Use your own candidate profile',403)
            account_authority(conn,actor)
            try:
                day = date.fromisoformat(exception_date)
            except ValueError as exc:
                raise AvailabilityConstraintError('INVALID_DATE', 'Use an ISO date', 422) from exc
            row=insert_row(conn,'availability_exceptions',candidate_id=candidate_id,local_date=day,start_minute=start_minute,end_minute=end_minute,kind='AVAILABLE' if kind=='AVAILABLE_EXTRA' else kind)
            audit.append_audit_event(actor_id=actor.user_id,action='CANDIDATE_AVAILABILITY_EXCEPTION_CREATED',
                entity_type='candidate_profile',entity_id=profile['id'],metadata={'exception_id':row['id']})
            return row

    def is_candidate_available_for_shift(
        self,
        *,
        candidate_id: str,
        weekday: int,
        start_minute: int,
        end_minute: int,
        check_date: str | None = None,
    ) -> bool:
        """Evaluate the requested local date, including rule validity and date exceptions."""
        validate_minute_bounds(start_minute, end_minute)
        try:
            day = date.fromisoformat(check_date) if check_date else local_today()
        except ValueError as exc:
            raise AvailabilityConstraintError('INVALID_DATE', 'Use an ISO date', 422) from exc
        if not check_date:
            day += timedelta(days=(weekday - day.isoweekday()) % 7)
        if day.isoweekday() != weekday:
            return False
        with read_snapshot():
            return load_snapshot(candidate_id, day, day + timedelta(days=1)).covers(day, start_minute, end_minute)


availability_service = CandidateAvailabilityService()
