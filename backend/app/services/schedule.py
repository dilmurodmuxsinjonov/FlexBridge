"""Bounded, request-local availability snapshots; dates are local Asia/Tashkent dates."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json

from sqlalchemy import or_, select
from app.db.storage import table, transaction

TASHKENT = timezone(timedelta(hours=5), 'Asia/Tashkent')


def local_today():
    return datetime.now(TASHKENT).date()


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


@dataclass
class AvailabilitySnapshot:
    rules: list
    exceptions: list

    @property
    def revision(self):
        rows = sorted((str(r['id']), str(r['updated_at'])) for r in self.rules + self.exceptions)
        return sha256(json.dumps(rows).encode()).hexdigest()

    def intervals(self, day):
        intervals = [(r['start_minute'], r['end_minute']) for r in self.rules
                     if r['weekday'] == day.isoweekday() and r['valid_from'] <= day
                     and (r['valid_to'] is None or day <= r['valid_to'])
                     and r['timezone'] == 'Asia/Tashkent']
        exceptions = [e for e in self.exceptions if e['local_date'] == day]
        intervals.extend((e['start_minute'], e['end_minute']) for e in exceptions if e['kind'] == 'AVAILABLE')
        intervals = merge(intervals)
        for exception in exceptions:
            if exception['kind'] != 'UNAVAILABLE':
                continue
            left, right = exception['start_minute'], exception['end_minute']
            parts = []
            for start, end in intervals:
                if right <= start or left >= end:
                    parts.append((start, end))
                else:
                    if start < left:
                        parts.append((start, left))
                    if right < end:
                        parts.append((right, end))
            intervals = parts
        return merge(intervals)

    def covers(self, day, start, end, buffer_minutes=0):
        # Split travel windows at midnight, including Sunday -> Monday.
        left, right = start - buffer_minutes, end + buffer_minutes
        for offset in range(left // 1440, (right - 1) // 1440 + 1):
            part_start = max(left - offset * 1440, 0)
            part_end = min(right - offset * 1440, 1440)
            if not any(a <= part_start and part_end <= b
                       for a, b in self.intervals(day + timedelta(days=offset))):
                return False
        return True


def load_snapshot(candidate_id, from_date, to_date):
    """to_date is exclusive. Call within a repeatable-read transaction for multi-read consistency."""
    rules, exceptions = table('availability_rules'), table('availability_exceptions')
    with transaction() as conn:
        weekly = list(conn.execute(select(rules).where(
            rules.c.candidate_id == candidate_id, rules.c.is_active.is_(True),
            rules.c.valid_from < to_date,
            or_(rules.c.valid_to.is_(None), rules.c.valid_to >= from_date))).mappings())
        dated = list(conn.execute(select(exceptions).where(
            exceptions.c.candidate_id == candidate_id,
            exceptions.c.local_date >= from_date, exceptions.c.local_date < to_date)).mappings())
    return AvailabilitySnapshot(weekly, dated)
