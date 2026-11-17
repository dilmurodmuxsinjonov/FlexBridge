"""Placement completion requests, two-sided sign-off, and closure lifecycle (API-049 / CAP-022)."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, text
from app.db.storage import table, transaction, now
from app.api.dependencies import ActorContext, owns_candidate
from app.core.audit import AppendOnlyAuditStore
from app.services.placement_admission import fingerprint, get_row, PlacementScopeError


def resolve_actor_side(conn, actor: ActorContext, placement: dict) -> str:
    """Resolve actor relationship to placement (CANDIDATE, MENTOR, HOST, TEACHER)."""
    candidate_profile = get_row(conn, 'candidate_profiles', placement['candidate_id'])
    if candidate_profile['user_id'] == actor.user_id:
        return 'CANDIDATE'

    # Check mentor assignment
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

    # Check host organization membership
    try:
        from app.services.authority import org_authority
        org_authority(conn, actor.user_id, placement['organization_id'], 'OWNER', 'HOST_COORDINATOR', 'HR')
        return 'HOST'
    except Exception:
        pass

    # Check academic track teacher
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

    raise PlacementScopeError('PLACEMENT_ACTOR_FORBIDDEN', status_code=403)


def get_placement_diaries_basis(conn, placement_id: str) -> dict:
    """Summarize submitted daily logs and check for open needs-revision reviews across academic & workplace reviews.
    
    Uses a CTE to isolate revision-level minutes summation from multi-review join cardinalities.
    """
    row = conn.execute(text("""
        WITH submitted_logs AS (
            SELECT
              dl.id AS log_id,
              lr.id AS revision_id,
              lr.total_minutes
            FROM flexbridge.daily_logs dl
            JOIN flexbridge.log_revisions lr ON lr.id = dl.current_revision_id
            WHERE dl.placement_id = :placement_id
              AND lr.submitted_at IS NOT NULL
        )
        SELECT
          CAST(COALESCE((SELECT SUM(total_minutes) FROM submitted_logs), 0) AS integer) AS total_logged_minutes,
          CAST(COALESCE((SELECT COUNT(*) FROM submitted_logs), 0) AS integer) AS total_log_count,
          CAST(COUNT(DISTINCT CASE WHEN alr.decision = 'NEEDS_REVISION' OR wlr.decision = 'CHANGES_REQUESTED' THEN sl.log_id END) AS integer) AS needs_revision_count,
          CAST(COUNT(DISTINCT CASE WHEN alr.decision = 'REVIEWED' OR wlr.decision = 'APPROVED' THEN sl.log_id END) AS integer) AS reviewed_count,
          CAST(COUNT(DISTINCT CASE WHEN alr.decision = 'NEEDS_REVISION' THEN sl.log_id END) AS integer) AS academic_needs_revision_count,
          CAST(COUNT(DISTINCT CASE WHEN wlr.decision = 'CHANGES_REQUESTED' THEN sl.log_id END) AS integer) AS workplace_changes_requested_count
        FROM submitted_logs sl
        LEFT JOIN flexbridge.academic_log_reviews alr ON alr.revision_id = sl.revision_id
        LEFT JOIN flexbridge.workplace_log_reviews wlr ON wlr.revision_id = sl.revision_id
    """), {'placement_id': placement_id}).mappings().one()
    return dict(row)


class PlacementCompletionService:
    def __init__(self):
        self.audit = AppendOnlyAuditStore()

    def request_or_confirm_completion(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        terms_id: str,
        version: int,
        idempotency_key: str,
        decision: str = 'REQUEST_COMPLETION',
        reason: str | None = None,
        early_reason: str | None = None,
    ) -> dict:
        if decision not in ('REQUEST_COMPLETION', 'CONFIRM_COMPLETION', 'REJECT_COMPLETION'):
            raise PlacementScopeError('INVALID_DECISION', status_code=422)

        digest = fingerprint(
            'PLACEMENT_COMPLETION',
            placement_id=placement_id,
            terms_id=terms_id,
            version=version,
            decision=decision,
            reason=reason,
            early_reason=early_reason,
        )

        with transaction() as conn:
            # 1. Lock placement row
            placement = get_row(conn, 'placements', placement_id, lock=True)
            terms = get_row(conn, 'placement_terms', placement['current_terms_id'], lock=True)

            # 2. Authorize actor relationship FIRST (strictly zero info leakage to unauthorized actors)
            side = resolve_actor_side(conn, actor, placement)

            # 3. Check terms version
            if str(terms['id']) != str(terms_id) or terms['version'] != version:
                raise PlacementScopeError('TERMS_VERSION_MISMATCH', status_code=409)

            # 4. Idempotency replay check (authorized callers only, actor-bound)
            # Checked before status preconditions so client retries after completion succeed
            t_req = table('placement_completion_requests')
            replay = conn.execute(
                select(t_req).where(
                    t_req.c.placement_id == placement_id,
                    t_req.c.idempotency_key == idempotency_key,
                )
            ).mappings().first()
            if replay:
                if replay['actor_id'] != actor.user_id:
                    raise PlacementScopeError('IDEMPOTENCY_ACTOR_MISMATCH', status_code=403)
                if replay['request_fingerprint'] != digest:
                    raise PlacementScopeError('IDEMPOTENCY_KEY_REUSE', status_code=409)
                return replay['receipt']

            # 5. Check status preconditions for new (non-replay) requests
            if placement['status'] == 'COMPLETED':
                raise PlacementScopeError('PLACEMENT_ALREADY_COMPLETED', status_code=409)
            if placement['status'] == 'CANCELLED':
                raise PlacementScopeError('PLACEMENT_CANCELLED', status_code=409)
            if placement['status'] not in ('ACTIVE', 'COMPLETION_REQUESTED'):
                raise PlacementScopeError('PLACEMENT_NOT_ACTIVE', status_code=409)

            # 6. Check open NEEDS_REVISION daily logs
            basis = get_placement_diaries_basis(conn, placement_id)
            if basis['needs_revision_count'] > 0:
                raise PlacementScopeError(
                    'OPEN_LOGS_NEED_REVISION',
                    message='Placement has daily logs requiring revision before completion can be requested',
                    status_code=409,
                )

            # 7. Check required minutes vs logged minutes
            required_minutes = terms.get('required_minutes', 0)
            total_logged = basis['total_logged_minutes']
            is_early = False
            if required_minutes > 0 and total_logged < required_minutes:
                if not early_reason or not early_reason.strip():
                    raise PlacementScopeError(
                        'EARLY_COMPLETION_REASON_REQUIRED',
                        message='Early completion requires an explicit explanation for unmet required minutes',
                        status_code=422,
                    )
                is_early = True

            # 8. Two-sided state machine
            existing_requests = list(
                conn.execute(
                    select(t_req).where(
                        t_req.c.placement_id == placement_id,
                        t_req.c.status.in_(['PENDING_HOST', 'PENDING_CANDIDATE', 'REQUESTED']),
                    )
                ).mappings()
            )

            has_candidate_signoff = (side == 'CANDIDATE' and decision in ('REQUEST_COMPLETION', 'CONFIRM_COMPLETION')) or any(
                r['side'] == 'CANDIDATE' and r['decision'] in ('REQUEST_COMPLETION', 'CONFIRM_COMPLETION')
                for r in existing_requests
            )
            has_host_signoff = (side in ('HOST', 'MENTOR') and decision in ('REQUEST_COMPLETION', 'CONFIRM_COMPLETION')) or any(
                r['side'] in ('HOST', 'MENTOR') and r['decision'] in ('REQUEST_COMPLETION', 'CONFIRM_COMPLETION')
                for r in existing_requests
            )

            stamp = now()
            req_id = str(uuid4())

            if decision == 'REJECT_COMPLETION':
                new_placement_status = 'ACTIVE'
                req_status = 'REJECTED'
                # Invalidate earlier pending requests so stale approvals cannot be reused
                conn.execute(
                    t_req.update()
                    .where(
                        t_req.c.placement_id == placement_id,
                        t_req.c.status.in_(['PENDING_HOST', 'PENDING_CANDIDATE', 'REQUESTED']),
                    )
                    .values(status='SUPERSEDED')
                )
            elif has_candidate_signoff and has_host_signoff:
                new_placement_status = 'COMPLETED'
                req_status = 'COMPLETED'
                # Mark pending requests superseded now that completion is finalized
                conn.execute(
                    t_req.update()
                    .where(
                        t_req.c.placement_id == placement_id,
                        t_req.c.status.in_(['PENDING_HOST', 'PENDING_CANDIDATE', 'REQUESTED']),
                    )
                    .values(status='SUPERSEDED')
                )
            else:
                new_placement_status = 'COMPLETION_REQUESTED'
                req_status = 'PENDING_HOST' if side == 'CANDIDATE' else 'PENDING_CANDIDATE'

            # 9. Update placement status
            conn.execute(
                table('placements').update()
                .where(table('placements').c.id == placement_id)
                .values(
                    status=new_placement_status,
                    updated_at=stamp,
                    version=placement['version'] + 1,
                )
            )

            receipt = {
                'id': req_id,
                'contract_id': 'API-049',
                'placement_id': placement_id,
                'terms_id': terms_id,
                'actor_id': actor.user_id,
                'side': side,
                'decision': decision,
                'status': req_status,
                'placement_status': new_placement_status,
                'early_completion': is_early,
                'early_reason': early_reason if is_early else None,
                'logged_minutes': total_logged,
                'required_minutes': required_minutes,
                'basis': basis,
                'recorded_at': stamp.isoformat(),
            }

            # 10. Record immutable completion request proof
            conn.execute(
                t_req.insert().values(
                    id=req_id,
                    created_at=stamp,
                    placement_id=placement_id,
                    terms_id=terms_id,
                    actor_id=actor.user_id,
                    side=side,
                    decision=decision,
                    status=req_status,
                    reason=reason or early_reason,
                    early_completion=is_early,
                    logged_minutes=total_logged,
                    required_minutes=required_minutes,
                    basis_snapshot=basis,
                    idempotency_key=idempotency_key,
                    request_fingerprint=digest,
                    receipt=receipt,
                    decided_at=stamp,
                )
            )

            # 11. Record audit event
            audit_action = 'PLACEMENT_COMPLETED' if new_placement_status == 'COMPLETED' else 'PLACEMENT_COMPLETION_REQUESTED'
            self.audit.append_audit_event(
                actor_id=actor.user_id,
                action=audit_action,
                entity_type='placement',
                entity_id=placement_id,
            )

            return receipt


completion_service = PlacementCompletionService()
