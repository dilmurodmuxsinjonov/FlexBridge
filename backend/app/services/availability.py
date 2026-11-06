"""Candidate Profile and `int4range(start_minute, end_minute, '[)')` Availability Service (S2.3.1, FIX-09).

Enforces `INV-01` (`FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` section 3.1) and `TD-001` (`FIX-09`):
- Intervals use half-open `[start_minute, end_minute)` semantics (`0 <= start_minute < end_minute <= 1440`).
- `availability_rules`: no two active rules for the same `(candidate_id, weekday)` may overlap (`&&`).
- `availability_exceptions`: no two exceptions for the same `(candidate_id, exception_date)` may overlap (`&&`).
- Adjacent intervals (e.g. `[540, 720)` and `[720, 900)`) do NOT overlap under `[)` semantics, are allowed,
  and are merged (`[540, 900)`) when evaluating candidate shift availability (`R-13`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


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

    rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    exceptions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_availability_rule(
        self,
        *,
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

        if is_active:
            for existing in self.rules.values():
                if (
                    existing["candidate_id"] == candidate_id
                    and existing["weekday"] == weekday
                    and existing["is_active"]
                    and ranges_overlap(
                        start_minute,
                        end_minute,
                        existing["start_minute"],
                        existing["end_minute"],
                    )
                ):
                    raise AvailabilityConstraintError(
                        code="OVERLAPPING_AVAILABILITY_RULE",
                        message=(
                            f"excl_availability_rules_no_overlap (INV-01): [{start_minute}, {end_minute}) "
                            f"mavjud [{existing['start_minute']}, {existing['end_minute']}) bilan kesishadi"
                        ),
                        status_code=409,
                        sqlstate="23P01",
                    )

        rule_id = str(uuid4())
        record = {
            "id": rule_id,
            "candidate_id": candidate_id,
            "weekday": weekday,
            "start_minute": start_minute,
            "end_minute": end_minute,
            "minute_range": f"[{start_minute},{end_minute})",
            "is_active": is_active,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.rules[rule_id] = record
        return dict(record)

    def add_availability_exception(
        self,
        *,
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

        for existing in self.exceptions.values():
            if (
                existing["candidate_id"] == candidate_id
                and existing["exception_date"] == exception_date
                and ranges_overlap(
                    start_minute,
                    end_minute,
                    existing["start_minute"],
                    existing["end_minute"],
                )
            ):
                raise AvailabilityConstraintError(
                    code="OVERLAPPING_AVAILABILITY_EXCEPTION",
                    message=(
                        f"excl_availability_exceptions_no_overlap (INV-01): {exception_date} sanada "
                        f"[{start_minute}, {end_minute}) mavjud [{existing['start_minute']}, {existing['end_minute']}) bilan kesishadi"
                    ),
                    status_code=409,
                    sqlstate="23P01",
                )

        exc_id = str(uuid4())
        record = {
            "id": exc_id,
            "candidate_id": candidate_id,
            "exception_date": exception_date,
            "start_minute": start_minute,
            "end_minute": end_minute,
            "minute_range": f"[{start_minute},{end_minute})",
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.exceptions[exc_id] = record
        return dict(record)

    def is_candidate_available_for_shift(
        self,
        *,
        candidate_id: str,
        weekday: int,
        start_minute: int,
        end_minute: int,
        check_date: str | None = None,
    ) -> bool:
        """Return True iff the candidate's merged rules + extra exceptions minus unavailable exceptions cover `[start_minute, end_minute)` (`FIX-09`, `R-13`)."""
        base_intervals: list[tuple[int, int]] = [
            (r["start_minute"], r["end_minute"])
            for r in self.rules.values()
            if r["candidate_id"] == candidate_id and r["weekday"] == weekday and r["is_active"]
        ]

        if check_date is not None:
            for e in self.exceptions.values():
                if (
                    e["candidate_id"] == candidate_id
                    and e["exception_date"] == check_date
                    and e["kind"] in ("AVAILABLE", "AVAILABLE_EXTRA")
                ):
                    base_intervals.append((e["start_minute"], e["end_minute"]))

        effective_intervals = merge_adjacent_intervals(base_intervals)
        if not effective_intervals:
            return False

        if check_date is not None:
            for e in self.exceptions.values():
                if (
                    e["candidate_id"] == candidate_id
                    and e["exception_date"] == check_date
                    and e["kind"] == "UNAVAILABLE"
                ):
                    effective_intervals = subtract_interval(
                        effective_intervals,
                        e["start_minute"],
                        e["end_minute"],
                    )
            effective_intervals = merge_adjacent_intervals(effective_intervals)

        return any(
            range_contains(iv_start, iv_end, start_minute, end_minute)
            for iv_start, iv_end in effective_intervals
        )


availability_service = CandidateAvailabilityService()
