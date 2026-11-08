"""28-day deterministic schedule matching, bounded pages and four scoped SQL reads."""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy import select, or_

from app.db.storage import table, now, read_snapshot
from app.services.schedule import load_snapshot, local_today

ALGORITHM_VERSION = '1.4.1-can'


def window(revision, requested_day):
    start = max(requested_day, revision['start_date'])
    end = start + timedelta(days=28)
    if revision['end_date'] is not None:
        end = min(end, revision['end_date'] + timedelta(days=1))
    return start, max(start, end)


def evaluate(revision, shifts, snapshot, requested_day, mode, commute_minutes):
    start, end = window(revision, requested_day)
    buffer = 0 if revision['work_mode'] == 'REMOTE' else commute_minutes
    result = {'contract_id': 'API-003', 'opportunity_id': revision['opportunity_id'],
        'revision_id': revision['id'], 'checked_from': start.isoformat(), 'checked_to': end.isoformat(),
        'algorithm_version': ALGORITHM_VERSION, 'availability_revision': snapshot.revision,
        'commute_buffer_minutes': buffer, 'schedule_match_mode': mode,
        'matched_group_codes': [], 'checked_occurrences': 0}
    def outcome(status, reason):
        return {**result, 'result': status, 'reason_codes': [reason]}
    if not shifts:
        return outcome('UNKNOWN', 'NO_SHIFTS_DEFINED')
    if any(s['timezone'] != 'Asia/Tashkent' for s in shifts) or any(r['timezone'] != 'Asia/Tashkent' for r in snapshot.rules):
        return outcome('UNKNOWN', 'UNSUPPORTED_TIMEZONE')
    groups = defaultdict(list)
    for shift in shifts:
        groups[shift['group_code']].append(shift)
    covered = []
    for code, group in sorted(groups.items()):
        matches = []
        for shift in group:
            day = start + timedelta(days=(shift['weekday'] - start.isoweekday()) % 7)
            while day < end:
                result['checked_occurrences'] += 1
                matches.append(snapshot.covers(day, shift['start_minute'], shift['end_minute'], buffer))
                day += timedelta(days=7)
        if matches and all(matches):
            covered.append(code)
    result['matched_group_codes'] = covered
    if not result['checked_occurrences']:
        return outcome('UNKNOWN', 'NO_REQUIRED_OCCURRENCES')
    if not snapshot.rules and not snapshot.exceptions:
        return outcome('UNKNOWN', 'NO_AVAILABILITY_DATA')
    matched = len(covered) == len(groups) if mode == 'ALL_SHIFTS_IN_GROUP' else bool(covered)
    return outcome('MATCH' if matched else 'CONFLICT', 'SCHEDULE_GROUP_COVERED' if matched else 'SHIFT_GROUP_NOT_COVERED')


def match_page(candidate_id, *, mode='ALL_SHIFTS_IN_GROUP', check_date=None, commute_minutes=30,
               limit=100, after_id=None, opportunity_id=None, revision_id=None):
    from app.services.opportunities import OpportunityConstraintError, compensation_type_for
    if mode not in ('ALL_SHIFTS_IN_GROUP', 'ANY_SHIFT_IN_GROUP'):
        raise OpportunityConstraintError('INVALID_SCHEDULE_MATCH_MODE', 'Select ALL or ANY', 422)
    if not 0 <= commute_minutes <= 180 or not 1 <= limit <= 100:
        raise OpportunityConstraintError('INVALID_MATCHING_OPTIONS', 'Invalid buffer or page size', 422)
    try:
        requested = date.fromisoformat(check_date) if isinstance(check_date, str) else (check_date or local_today())
    except ValueError as exc:
        raise OpportunityConstraintError('INVALID_DATE', 'Use an ISO date', 422) from exc
    # Historical matching is not a promise about a current opportunity's future schedule.
    requested = max(requested, local_today())
    if requested > date.max - timedelta(days=30):
        raise OpportunityConstraintError('INVALID_DATE_RANGE', 'Date range is too large', 422)
    opportunities, revisions, shifts = table('opportunities'), table('opportunity_revisions'), table('opportunity_shifts')
    query = select(revisions).join(opportunities, opportunities.c.current_revision_id == revisions.c.id).where(
        opportunities.c.status == 'PUBLISHED',
        or_(opportunities.c.expires_at.is_(None), opportunities.c.expires_at > now()))
    if opportunity_id:
        query = query.where(opportunities.c.id == opportunity_id)
    if revision_id:
        query = query.where(revisions.c.id == revision_id)
    if after_id:
        query = query.where(opportunities.c.id > after_id)
    with read_snapshot() as conn:
        rows = list(conn.execute(query.order_by(opportunities.c.id).limit(limit + 1)).mappings())
        has_more = len(rows) > limit
        rows = rows[:limit]
        if not rows:
            return {'items': [], 'evaluations': [], 'next_cursor': None}
        shift_rows = list(conn.execute(select(shifts).where(shifts.c.revision_id.in_([r['id'] for r in rows]))).mappings())
        windows = [window(r, requested) for r in rows]
        snapshot = load_snapshot(candidate_id, min(w[0] for w in windows) - timedelta(days=1),
            max(w[1] for w in windows) + timedelta(days=1))
        by_revision = defaultdict(list)
        for shift in shift_rows:
            by_revision[shift['revision_id']].append(shift)
        evaluations = [evaluate(r, by_revision[r['id']], snapshot, requested, mode, commute_minutes) for r in rows]
        items = [{**evaluation, 'title': revision['title'], 'contract_type': revision['contract_type'],
            'compensation_type': compensation_type_for(revision)}
            for revision, evaluation in zip(rows, evaluations) if evaluation['result'] == 'MATCH']
        return {'items': items, 'evaluations': evaluations,
                'next_cursor': rows[-1]['opportunity_id'] if has_more else None}
