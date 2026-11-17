"""Placement diary logs view service (API-053 / CAP-022 / PG-022.S01).

Implements canonical `API-053` (`GET /api/v1/placements/{placement_id}/logs`):
- Multi-stakeholder access control (CANDIDATE, HOST, MENTOR, TEACHER, COORDINATOR)
- Anti-probing & draft confidentiality: non-candidate stakeholders only see SUBMITTED logs
- High-performance batched querying (anti-N+1)
- Date range filtering, status filtering, and pagination controls
"""
from __future__ import annotations

import collections
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.api.dependencies import ActorContext
from app.db.storage import table, transaction
from app.services.authority import account_authority, org_authority
from app.services.placement_admission import PlacementScopeError, get_row


def resolve_logs_actor(conn, actor: ActorContext, placement: dict[str, Any]) -> str:
    """Resolve actor relationship to placement (CANDIDATE, HOST, MENTOR, TEACHER, COORDINATOR)."""
    # 1. Candidate check
    candidate_profile = get_row(conn, 'candidate_profiles', placement['candidate_id'])
    if candidate_profile and candidate_profile['user_id'] == actor.user_id:
        return 'CANDIDATE'

    # 2. Host organization check (OWNER, HOST_COORDINATOR, HR) - organizational authority takes precedence
    try:
        org_authority(conn, actor.user_id, placement['organization_id'], 'OWNER', 'HOST_COORDINATOR', 'HR')
        return 'HOST'
    except Exception:
        pass

    # 3. Mentor check (active assignment)
    t_m = table('mentor_assignments')
    t_mp = table('mentor_assignment_proofs')
    mentor_row = conn.execute(
        select(t_m.c.id)
        .select_from(t_m.join(t_mp, t_mp.c.assignment_id == t_m.c.id))
        .where(
            t_m.c.placement_id == placement['id'],
            t_mp.c.mentor_user_id == actor.user_id,
            t_m.c.accepted_at.is_not(None),
            t_m.c.revoked_at.is_(None),
        )
    ).first()
    if mentor_row:
        return 'MENTOR'

    # 4. Teacher check (academic track)
    if placement.get('academic_track'):
        t_aa = table('academic_assignments')
        t_aap = table('academic_assignment_proofs')
        teacher_row = conn.execute(
            select(t_aa.c.id)
            .select_from(t_aa.join(t_aap, t_aap.c.assignment_id == t_aa.c.id))
            .where(
                t_aa.c.placement_id == placement['id'],
                t_aap.c.teacher_user_id == actor.user_id,
                t_aa.c.accepted_at.is_not(None),
                t_aa.c.revoked_at.is_(None),
            )
        ).first()
        if teacher_row:
            return 'TEACHER'

    # 5. Coordinator check (institutional supervisor)
    if placement.get('enrollment_id'):
        t_en = table('enrollments')
        en_row = conn.execute(
            select(t_en.c.institution_id).where(t_en.c.id == placement['enrollment_id'])
        ).mappings().first()
        if en_row:
            inst_id = en_row['institution_id']
            try:
                from app.services.authority import institution_authority
                institution_authority(conn, actor, inst_id, 'COORDINATOR')
                return 'COORDINATOR'
            except Exception:
                pass

    raise PlacementScopeError('PLACEMENT_ACTOR_FORBIDDEN', status_code=403)


class PlacementLogsService:
    """Service handling placement daily diary logs retrieval and filtering."""

    def get_placement_logs_api_053(
        self,
        *,
        actor: ActorContext,
        placement_id: str | UUID,
        from_date: str | date | None = None,
        to_date: str | date | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        include_tasks: bool = True,
        include_reviews: bool = True,
    ) -> dict[str, Any]:
        """Query and return daily logs for a placement with role-based confidentiality."""
        # 1. Parameter validations
        if page < 1:
            raise PlacementScopeError('INVALID_PAGINATION', 'page must be >= 1', status_code=422)
        if page_size < 1 or page_size > 100:
            raise PlacementScopeError('INVALID_PAGE_SIZE', 'page_size must be between 1 and 100', status_code=422)

        if status is not None:
            status_clean = status.strip().upper()
            if status_clean not in ('DRAFT', 'SUBMITTED'):
                raise PlacementScopeError(
                    'INVALID_STATUS_FILTER',
                    f"Invalid status '{status}'; allowed values are DRAFT, SUBMITTED",
                    status_code=422,
                )
            status = status_clean

        parsed_from: date | None = None
        parsed_to: date | None = None

        if from_date is not None:
            if isinstance(from_date, date):
                parsed_from = from_date
            elif isinstance(from_date, str):
                try:
                    parsed_from = date.fromisoformat(from_date.strip())
                except ValueError:
                    raise PlacementScopeError('INVALID_DATE_FORMAT', 'from_date must be YYYY-MM-DD', status_code=422)
            else:
                raise PlacementScopeError('INVALID_DATE_FORMAT', status_code=422)

        if to_date is not None:
            if isinstance(to_date, date):
                parsed_to = to_date
            elif isinstance(to_date, str):
                try:
                    parsed_to = date.fromisoformat(to_date.strip())
                except ValueError:
                    raise PlacementScopeError('INVALID_DATE_FORMAT', 'to_date must be YYYY-MM-DD', status_code=422)
            else:
                raise PlacementScopeError('INVALID_DATE_FORMAT', status_code=422)

        if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
            raise PlacementScopeError('INVALID_DATE_RANGE', 'from_date cannot be greater than to_date', status_code=422)

        pid_str = str(placement_id)

        with transaction() as conn:
            # 2. Check placement existence
            try:
                placement = get_row(conn, 'placements', pid_str)
            except PlacementScopeError:
                raise PlacementScopeError('PLACEMENT_NOT_FOUND', status_code=404)
            if not placement:
                raise PlacementScopeError('PLACEMENT_NOT_FOUND', status_code=404)

            # 3. Role authorization & draft visibility control
            actor_role = resolve_logs_actor(conn, actor, placement)
            account_authority(conn, actor)

            if actor_role != 'CANDIDATE':
                # Candidate draft privacy: non-candidates can never see draft logs
                if status == 'DRAFT':
                    return {
                        'contract_id': 'API-053',
                        'placement_id': pid_str,
                        'total': 0,
                        'page': page,
                        'page_size': page_size,
                        'total_pages': 0,
                        'items': [],
                    }
                effective_status = 'SUBMITTED'
            else:
                effective_status = status

            # 4. Filter setup
            t_dl = table('daily_logs')
            t_lr = table('log_revisions')

            filters = [t_dl.c.placement_id == pid_str]
            if parsed_from is not None:
                filters.append(t_dl.c.local_date >= parsed_from)
            if parsed_to is not None:
                filters.append(t_dl.c.local_date <= parsed_to)
            if effective_status is not None:
                filters.append(t_lr.c.status == effective_status)

            # 5. Total count query
            count_q = (
                select(func.count(t_dl.c.id))
                .select_from(t_dl.join(t_lr, t_lr.c.id == t_dl.c.current_revision_id))
                .where(*filters)
            )
            total = conn.execute(count_q).scalar_one()

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            offset = (page - 1) * page_size

            # 6. Paginated logs retrieval
            rows_q = (
                select(
                    t_dl.c.id.label('log_id'),
                    t_dl.c.placement_id,
                    t_dl.c.local_date,
                    t_dl.c.version,
                    t_lr.c.id.label('revision_id'),
                    t_lr.c.revision,
                    t_lr.c.terms_id,
                    t_lr.c.author_id,
                    t_lr.c.day_type,
                    t_lr.c.summary,
                    t_lr.c.total_minutes,
                    t_lr.c.status,
                    t_lr.c.submitted_at,
                )
                .select_from(t_dl.join(t_lr, t_lr.c.id == t_dl.c.current_revision_id))
                .where(*filters)
                .order_by(t_dl.c.local_date.desc(), t_dl.c.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            log_rows = conn.execute(rows_q).mappings().all()

            if not log_rows:
                return {
                    'contract_id': 'API-053',
                    'placement_id': pid_str,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'items': [],
                }

            rev_ids = [r['revision_id'] for r in log_rows if r['revision_id']]

            # 7. Batched tasks query (if requested)
            tasks_by_rev: dict[Any, list[dict[str, Any]]] = collections.defaultdict(list)
            if include_tasks and rev_ids:
                t_te = table('log_task_entries')
                t_ev = table('log_evidence')
                ev_count_subq = (
                    select(func.count(t_ev.c.id))
                    .where(t_ev.c.entry_id == t_te.c.id)
                    .correlate(t_te)
                    .scalar_subquery()
                )
                tasks_q = (
                    select(
                        t_te.c.id,
                        t_te.c.revision_id,
                        t_te.c.plan_task_id,
                        t_te.c.result_text,
                        t_te.c.minutes,
                        t_te.c.start_minute,
                        t_te.c.end_minute,
                        ev_count_subq.label('evidence_count'),
                    )
                    .where(t_te.c.revision_id.in_(rev_ids))
                    .order_by(t_te.c.start_minute.asc().nulls_last(), t_te.c.id.asc())
                )
                task_rows = conn.execute(tasks_q).mappings().all()
                for tr in task_rows:
                    tasks_by_rev[tr['revision_id']].append({
                        'id': str(tr['id']),
                        'plan_task_id': str(tr['plan_task_id']) if tr['plan_task_id'] else None,
                        'result_text': tr['result_text'],
                        'minutes': tr['minutes'],
                        'start_minute': tr['start_minute'],
                        'end_minute': tr['end_minute'],
                        'evidence_count': int(tr['evidence_count'] or 0),
                    })

            # 8. Batched reviews query (if requested)
            workplace_by_rev: dict[Any, list[dict[str, Any]]] = collections.defaultdict(list)
            academic_by_rev: dict[Any, list[dict[str, Any]]] = collections.defaultdict(list)
            if include_reviews and rev_ids:
                # Workplace reviews
                t_wlr = table('workplace_log_reviews')
                wlr_q = (
                    select(
                        t_wlr.c.id,
                        t_wlr.c.revision_id,
                        t_wlr.c.mentor_assignment_id,
                        t_wlr.c.decision,
                        t_wlr.c.comment,
                        t_wlr.c.decided_at,
                    )
                    .where(t_wlr.c.revision_id.in_(rev_ids))
                    .order_by(t_wlr.c.decided_at.asc(), t_wlr.c.id.asc())
                )
                wlr_rows = conn.execute(wlr_q).mappings().all()
                for wr in wlr_rows:
                    workplace_by_rev[wr['revision_id']].append({
                        'id': str(wr['id']),
                        'mentor_assignment_id': str(wr['mentor_assignment_id']),
                        'decision': wr['decision'],
                        'comment': wr['comment'],
                        'decided_at': wr['decided_at'].isoformat() if hasattr(wr['decided_at'], 'isoformat') else str(wr['decided_at']),
                    })

                # Academic reviews
                t_alr = table('academic_log_reviews')
                alr_q = (
                    select(
                        t_alr.c.id,
                        t_alr.c.revision_id,
                        t_alr.c.academic_assignment_id,
                        t_alr.c.decision,
                        t_alr.c.comment,
                        t_alr.c.decided_at,
                    )
                    .where(t_alr.c.revision_id.in_(rev_ids))
                    .order_by(t_alr.c.decided_at.asc(), t_alr.c.id.asc())
                )
                alr_rows = conn.execute(alr_q).mappings().all()
                for ar in alr_rows:
                    academic_by_rev[ar['revision_id']].append({
                        'id': str(ar['id']),
                        'academic_assignment_id': str(ar['academic_assignment_id']),
                        'decision': ar['decision'],
                        'comment': ar['comment'],
                        'decided_at': ar['decided_at'].isoformat() if hasattr(ar['decided_at'], 'isoformat') else str(ar['decided_at']),
                    })

            # 9. Assembly
            items = []
            for row in log_rows:
                rev_id = row['revision_id']
                rev_data = None
                if rev_id:
                    rev_data = {
                        'id': str(rev_id),
                        'revision': row['revision'],
                        'terms_id': str(row['terms_id']),
                        'author_id': str(row['author_id']),
                        'day_type': row['day_type'],
                        'summary': row['summary'],
                        'total_minutes': row['total_minutes'],
                        'status': row['status'],
                        'submitted_at': row['submitted_at'].isoformat() if row['submitted_at'] else None,
                    }
                    if include_tasks:
                        rev_data['tasks'] = tasks_by_rev.get(rev_id, [])
                    if include_reviews:
                        rev_data['workplace_reviews'] = workplace_by_rev.get(rev_id, [])
                        rev_data['academic_reviews'] = academic_by_rev.get(rev_id, [])

                items.append({
                    'id': str(row['log_id']),
                    'placement_id': str(row['placement_id']),
                    'local_date': row['local_date'].isoformat() if hasattr(row['local_date'], 'isoformat') else str(row['local_date']),
                    'version': row['version'],
                    'current_revision': rev_data,
                })

            return {
                'contract_id': 'API-053',
                'placement_id': pid_str,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'items': items,
            }


placement_logs_service = PlacementLogsService()
