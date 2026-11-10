"""Independent feedback on the submitted revision explicitly named by the teacher."""
from sqlalchemy import select, text

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction, now
from app.services import authority
from app.services.academic_admission import academic_service, proof_for, snapshot
from app.services.placement_admission import evidence, fingerprint, request_record
from app.services.placements import get_row, insert_row, PlacementScopeError


class AcademicReviewService:
    audit = AppendOnlyAuditStore()

    def review(self, *, actor, revision_id, assignment_id, decision, comment, idempotency_key,
               daily_log_id=None, placement_id=None):
        if decision not in ('REVIEWED', 'NEEDS_REVISION'):
            raise PlacementScopeError('INVALID_REVIEW_DECISION', status_code=422)
        if not isinstance(comment, str) or len(comment) > 10000:
            raise PlacementScopeError('INVALID_REVIEW_COMMENT', status_code=422)
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise PlacementScopeError('INVALID_IDEMPOTENCY_KEY', status_code=422)
        digest = fingerprint('ACADEMIC_REVIEW', revision_id=revision_id, assignment_id=assignment_id,
                             decision=decision, comment=comment)
        with transaction() as conn:
            p, current_terms, s, assignment = academic_service.locked_assignment(conn, assignment_id)
            hint = get_row(conn, 'log_revisions', revision_id)
            log = get_row(conn, 'daily_logs', hint['daily_log_id'], True)
            revision = get_row(conn, 'log_revisions', revision_id, True)
            if (log['placement_id'] != p['id'] or revision['daily_log_id'] != log['id']
                or placement_id is not None and placement_id != p['id']
                or daily_log_id is not None and daily_log_id != log['id']):
                raise PlacementScopeError('REVIEW_SCOPE_FORBIDDEN', status_code=403)
            # Intent waits must precede the current actor/scope checks too: locks
            # prevent revocation races, but cannot stop a session expiring with time.
            conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                         {'key': 'academic-review:' + actor.user_id + ':' + idempotency_key})
            academic_service.material(conn, p, s['id'], assignment['institution_id'])
            current = academic_service.teacher(conn, actor, p, assignment)
            # Recheck global sensitive-role policy after the scoped grant lock wait.
            authority.account_authority(conn, actor)
            candidate = get_row(conn, 'candidate_profiles', p['candidate_id'])
            if revision['author_id'] != candidate['user_id']:
                raise PlacementScopeError('REVISION_AUTHOR_FORBIDDEN', status_code=403)
            revision_terms = get_row(conn, 'placement_terms', revision['terms_id'])
            binding = proof_for(conn, 'placement_academic_bindings', 'placement_id', p['id'])
            if (revision_terms['placement_id'] != p['id'] or not binding
                or binding['origin'] == 'PUBLIC' and current_terms['terms_snapshot'].get('academic_scope') != binding['scope_snapshot']
                or not conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),
                    {'a': assignment_id, 't': revision['terms_id']}).scalar_one()):
                raise PlacementScopeError('REVIEW_SCOPE_FORBIDDEN', status_code=403)
            consents = table('academic_assignment_consents')
            if not conn.execute(select(consents.c.id).where(consents.c.assignment_id == assignment_id,
                consents.c.terms_id == revision['terms_id'], consents.c.actor_id == actor.user_id,
                consents.c.teacher_grant_id == current['_authority_grant_id'],
                consents.c.teacher_appointment_id == current['_authority_appointment_id'])).first():
                raise PlacementScopeError('TEACHER_PLAN_ACCEPTANCE_REQUIRED', status_code=403)
            if revision['status'] != 'SUBMITTED' or not revision['submitted_at'] or revision['submitted_at'] > now():
                raise PlacementScopeError('SUBMITTED_REVISION_REQUIRED')
            old = request_record(conn, 'academic_review_proofs', actor, idempotency_key, digest)
            if old:
                return old['receipt']
            if daily_log_id is not None and log['current_revision_id'] != revision_id:
                raise PlacementScopeError('STALE_LOG_REVISION')
            if p['status'] != 'ACTIVE':
                raise PlacementScopeError('ACTIVE_ACADEMIC_PLACEMENT_REQUIRED', status_code=403)
            reviews = table('academic_log_reviews')
            if conn.execute(select(reviews.c.id).where(reviews.c.revision_id == revision_id,
                reviews.c.academic_assignment_id == assignment_id)).first():
                raise PlacementScopeError('ACADEMIC_REVISION_ALREADY_REVIEWED')
            review = insert_row(conn, 'academic_log_reviews', revision_id=revision_id, placement_id=p['id'],
                                academic_assignment_id=assignment_id, decision=decision, comment=comment, decided_at=now())
            receipt = snapshot(conn, 'academic_log_reviews', review['id'])
            conn.execute(table('academic_review_proofs').insert().values(
                review_id=review['id'], created_at=now(), origin='PUBLIC', initial_snapshot=snapshot(conn, 'academic_log_reviews', review['id']),
                terms_id=revision['terms_id'], **evidence(conn, actor), teacher_grant_id=current['_authority_grant_id'],
                teacher_appointment_id=current['_authority_appointment_id'],
                assignment_proof_snapshot=conn.execute(text('SELECT to_jsonb(q) FROM flexbridge.academic_assignment_proofs q WHERE assignment_id=:id'),
                                                       {'id': assignment_id}).scalar_one(),
                revision_snapshot=snapshot(conn, 'log_revisions', revision_id), idempotency_key=idempotency_key,
                request_fingerprint=digest, receipt=receipt))
            self.audit.append_audit_event(actor_id=actor.user_id, action='ACADEMIC_LOG_REVIEWED',
                                          entity_type='academic_log_review', entity_id=review['id'])
            return receipt


academic_review_service = AcademicReviewService()
