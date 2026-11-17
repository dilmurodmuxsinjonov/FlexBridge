"""Placement-wide nonofficial teacher academic conclusions over the complete current diary basis (API-108 / CAP-024)."""
from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text

from app.core.audit import AppendOnlyAuditStore
from app.db.academic_decisions import register_tables
from app.db.storage import _TYPES, metadata, table, transaction
from app.services import authority
from app.services.academic_admission import academic_service, proof_for
from app.services.governance import GovernanceError
from app.services.placement_admission import evidence, fingerprint, request_record
from app.services.placements import PlacementScopeError, get_row

register_tables(metadata, _TYPES)

DECISIONS = ('ACADEMIC_REVIEW_COMPLETE', 'ACADEMIC_REVISION_REQUIRED')
HEX64_RE = re.compile(r'^[0-9a-f]{64}$')
AUDIT_ACTION = 'ACADEMIC_DECISION_RECORDED'
AUDIT_SOURCE = 'API-108'


def intent_lock_key(actor_id: str, key: str) -> str:
    return 'academic-decision:' + str(actor_id) + ':' + str(key)


def basis_for(conn, placement_id: str, assignment_id: str) -> dict[str, Any]:
    value = conn.execute(
        text('SELECT flexbridge.academic_decision_basis(CAST(:p AS uuid),CAST(:a AS uuid))'),
        {'p': str(placement_id), 'a': str(assignment_id)},
    ).scalar_one_or_none()
    if value is None:
        raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
    return dict(value)


def digest_for(conn, basis: dict[str, Any]) -> str:
    return conn.execute(
        text('SELECT flexbridge.academic_decision_digest(CAST(:b AS jsonb))'),
        {'b': json.dumps(basis)},
    ).scalar_one()


def basis_current(conn, decision_id: str) -> bool:
    return bool(
        conn.execute(
            text('SELECT flexbridge.academic_decision_basis_current(CAST(:d AS uuid))'),
            {'d': str(decision_id)},
        ).scalar_one()
    )


class AcademicDecisionService:
    audit = AppendOnlyAuditStore()

    @staticmethod
    def _require_read_committed(conn) -> None:
        if conn.execute(text("SELECT current_setting('transaction_isolation')")).scalar_one() != 'read committed':
            raise PlacementScopeError('ACADEMIC_DECISION_ISOLATION_UNSAFE', status_code=503)

    @staticmethod
    def _require_uuid(value: Any, code: str = 'INVALID_IDENTIFIER_OR_VALUE') -> str:
        if not isinstance(value, (str, UUID)):
            raise PlacementScopeError(code, status_code=422)
        try:
            return str(UUID(str(value)))
        except (TypeError, ValueError):
            raise PlacementScopeError(code, status_code=422) from None

    @classmethod
    def _require_actor(cls, actor) -> tuple[str, str]:
        try:
            uid = str(UUID(str(actor.user_id)))
            sid = str(UUID(str(actor.session_id)))
            return uid, sid
        except (AttributeError, TypeError, ValueError):
            raise GovernanceError('AUTH_REVOKED', status_code=401) from None

    @classmethod
    def _validate_conclude_inputs(
        cls,
        *,
        placement_id: Any,
        assignment_id: Any,
        terms_id: Any,
        version: Any,
        expected_basis_digest: Any,
        decision: Any,
        reason: Any,
        idempotency_key: Any,
    ) -> tuple[str, str, str, str]:
        pid = cls._require_uuid(placement_id)
        aid = cls._require_uuid(assignment_id)
        tid = cls._require_uuid(terms_id)
        if type(version) is not int or version <= 0:
            raise PlacementScopeError('INVALID_PLAN_VERSION', status_code=422)
        if not isinstance(expected_basis_digest, str) or not HEX64_RE.fullmatch(expected_basis_digest):
            raise PlacementScopeError('INVALID_BASIS_DIGEST', status_code=422)
        if decision not in DECISIONS:
            raise PlacementScopeError('INVALID_ACADEMIC_DECISION', status_code=422)
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2000:
            raise PlacementScopeError('INVALID_ACADEMIC_DECISION_REASON', status_code=422)
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise PlacementScopeError('INVALID_IDEMPOTENCY_KEY', status_code=422)
        return pid, aid, tid, reason.strip()

    @staticmethod
    def _lock_diary_scope(conn, placement_id: str, assignment_id: str) -> None:
        logs = table('daily_logs')
        revisions = table('log_revisions')
        reviews = table('academic_log_reviews')
        log_rows = list(
            conn.execute(
                select(logs.c.id, logs.c.current_revision_id)
                .where(logs.c.placement_id == placement_id)
                .order_by(logs.c.id)
                .with_for_update()
            ).mappings()
        )
        revision_ids = sorted({r['current_revision_id'] for r in log_rows if r['current_revision_id'] is not None})
        if revision_ids:
            conn.execute(
                select(revisions.c.id)
                .where(revisions.c.id.in_(revision_ids))
                .order_by(revisions.c.id)
                .with_for_update()
            ).all()
        conn.execute(
            select(reviews.c.id)
            .where(
                reviews.c.placement_id == placement_id,
                reviews.c.academic_assignment_id == assignment_id,
            )
            .order_by(reviews.c.id)
            .with_for_update()
        ).all()

    @staticmethod
    def _verify_authority_and_consent(conn, actor, p, current_terms, s, assignment, check_terms_id: str):
        academic_service.material(conn, p, s['id'], assignment['institution_id'])
        current = academic_service.teacher(conn, actor, p, assignment)
        # Recheck global sensitive-role policy after all business/grant waits.
        authority.account_authority(conn, actor)
        auth_info = evidence(conn, actor)
        binding = proof_for(conn, 'placement_academic_bindings', 'placement_id', p['id'])
        if (
            not binding
            or not p['academic_track']
            or p['enrollment_id'] != binding['enrollment_id']
            or assignment['supervision_id'] != binding['supervision_id']
            or assignment['institution_id'] != binding['institution_id']
            or (
                binding['origin'] == 'PUBLIC'
                and current_terms['terms_snapshot'].get('academic_scope') != binding['scope_snapshot']
            )
        ):
            raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
        if not conn.execute(
            text('SELECT flexbridge.placement_actor_current(CAST(:u AS uuid),CAST(:s AS uuid),:v)'),
            {'u': auth_info['actor_id'], 's': auth_info['session_id'], 'v': auth_info['auth_version']},
        ).scalar_one():
            raise GovernanceError('AUTH_REVOKED', status_code=401)
        if not conn.execute(
            text('SELECT flexbridge.academic_teacher_current(CAST(:a AS uuid),CAST(:t AS uuid))'),
            {'a': assignment['id'], 't': check_terms_id},
        ).scalar_one():
            raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
        consents = table('academic_assignment_consents')
        consent = (
            conn.execute(
                select(consents).where(
                    consents.c.assignment_id == assignment['id'],
                    consents.c.placement_id == p['id'],
                    consents.c.terms_id == check_terms_id,
                    consents.c.actor_id == actor.user_id,
                    consents.c.teacher_grant_id == current['_authority_grant_id'],
                    consents.c.teacher_appointment_id == current['_authority_appointment_id'],
                )
            )
            .mappings()
            .first()
        )
        if not consent:
            raise PlacementScopeError('TEACHER_PLAN_ACCEPTANCE_REQUIRED', status_code=403)
        return current, auth_info, dict(consent)

    def context(self, actor, placement_id, assignment_id) -> dict[str, Any]:
        pid = self._require_uuid(placement_id)
        aid = self._require_uuid(assignment_id)
        self._require_actor(actor)
        with transaction() as conn:
            self._require_read_committed(conn)
            p, current_terms, s, assignment = academic_service.locked_assignment(conn, aid)
            if p['id'] != pid:
                raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
            self._lock_diary_scope(conn, p['id'], aid)
            self._verify_authority_and_consent(conn, actor, p, current_terms, s, assignment, current_terms['id'])
            basis = basis_for(conn, p['id'], aid)
            actual_digest = digest_for(conn, basis)
            proofs = table('academic_decision_proofs')
            current_conclusion = conn.execute(
                select(proofs.c.receipt).where(
                    proofs.c.origin == 'PUBLIC',
                    proofs.c.assignment_id == aid,
                    proofs.c.terms_id == current_terms['id'],
                    proofs.c.basis_digest == actual_digest,
                )
            ).scalar_one_or_none()
            return {
                'placement_id': str(p['id']),
                'academic_assignment_id': str(aid),
                'terms_id': str(current_terms['id']),
                'version': int(current_terms['version']),
                'basis_digest': actual_digest,
                'log_count': int(basis['log_count']),
                'submitted_count': int(basis['submitted_count']),
                'reviewed_count': int(basis['reviewed_count']),
                'needs_revision_count': int(basis['needs_revision_count']),
                'pending_count': int(basis['pending_count']),
                'academic_review_complete': bool(basis['academic_review_complete']),
                'new_conclusion_allowed': bool(p['status'] == 'ACTIVE'),
                'current_conclusion': dict(current_conclusion) if current_conclusion is not None else None,
                'advisory_only': True,
            }

    def conclude(
        self,
        *,
        actor,
        placement_id,
        assignment_id,
        terms_id,
        version,
        expected_basis_digest,
        decision,
        reason,
        idempotency_key,
    ) -> dict[str, Any]:
        pid, aid, tid, clean_reason = self._validate_conclude_inputs(
            placement_id=placement_id,
            assignment_id=assignment_id,
            terms_id=terms_id,
            version=version,
            expected_basis_digest=expected_basis_digest,
            decision=decision,
            reason=reason,
            idempotency_key=idempotency_key,
        )
        uid, _ = self._require_actor(actor)
        digest = fingerprint(
            'ACADEMIC_DECISION',
            placement_id=pid,
            assignment_id=aid,
            terms_id=tid,
            version=version,
            expected_basis_digest=expected_basis_digest,
            decision=decision,
            reason=clean_reason,
        )
        with transaction() as conn:
            self._require_read_committed(conn)
            # 1. Actor/key advisory lock FIRST, before any business, actor FK, or authority locks.
            conn.execute(
                text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                {'key': intent_lock_key(uid, idempotency_key)},
            )
            # 2. Parent/business lock chain and sorted diary/revision/review locks.
            p, current_terms, s, assignment = academic_service.locked_assignment(conn, aid)
            if p['id'] != pid:
                raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
            requested_terms = (
                current_terms if tid == current_terms['id'] else get_row(conn, 'placement_terms', tid, True)
            )
            if requested_terms['placement_id'] != p['id']:
                raise PlacementScopeError('DECISION_SCOPE_FORBIDDEN', status_code=403)
            self._lock_diary_scope(conn, p['id'], aid)
            # 3. Current material, original teacher, session/MFA, and exact requested terms consent after all waits.
            current, auth_info, consent = self._verify_authority_and_consent(
                conn, actor, p, current_terms, s, assignment, tid
            )
            # 4. Replay lookup precedes current-plan / ACTIVE / current-basis checks.
            old = request_record(conn, 'academic_decision_proofs', actor, idempotency_key, digest)
            if old:
                return dict(old['receipt'])
            # 5. New write eligibility checks.
            if p['status'] != 'ACTIVE':
                raise PlacementScopeError('ACTIVE_ACADEMIC_PLACEMENT_REQUIRED', status_code=403)
            if p['current_terms_id'] != tid or current_terms['version'] != version:
                raise PlacementScopeError('STALE_PLAN_VERSION', status_code=409)
            basis = basis_for(conn, p['id'], aid)
            actual_digest = digest_for(conn, basis)
            if actual_digest != expected_basis_digest:
                raise PlacementScopeError('ACADEMIC_BASIS_CHANGED', status_code=412)
            proofs = table('academic_decision_proofs')
            if conn.execute(
                select(proofs.c.decision_id).where(
                    proofs.c.origin == 'PUBLIC',
                    proofs.c.assignment_id == aid,
                    proofs.c.terms_id == tid,
                    proofs.c.basis_digest == actual_digest,
                )
            ).first():
                raise PlacementScopeError('ACADEMIC_CONCLUSION_ALREADY_RECORDED', status_code=409)
            if decision == 'ACADEMIC_REVIEW_COMPLETE' and not basis['academic_review_complete']:
                raise PlacementScopeError('ACADEMIC_REVIEWS_PENDING', status_code=409)
            # 6. Fresh SQL clock after all waits; insert canonical DB-054 -> audit -> proof.
            stamp = conn.execute(text('SELECT clock_timestamp()')).scalar_one()
            decision_id = str(uuid4())
            conn.execute(
                table('placement_decisions').insert().values(
                    id=decision_id,
                    created_at=stamp,
                    updated_at=stamp,
                    placement_id=p['id'],
                    actor_id=uid,
                    side='TEACHER',
                    decision=decision,
                    terms_id=tid,
                    reason=clean_reason,
                    decided_at=stamp,
                )
            )
            receipt = conn.execute(
                text(
                    'SELECT flexbridge.placement_decision_snapshot(d) '
                    'FROM flexbridge.placement_decisions d WHERE d.id=CAST(:id AS uuid)'
                ),
                {'id': decision_id},
            ).scalar_one()
            audit_entry = self.audit.append_audit_event(
                actor_id=uid,
                action=AUDIT_ACTION,
                entity_type='placement_decision',
                entity_id=decision_id,
                metadata={
                    'source': AUDIT_SOURCE,
                    'placement_id': p['id'],
                    'assignment_id': aid,
                    'academic_assignment_id': aid,
                    'terms_id': tid,
                    'version': version,
                    'decision': decision,
                    'basis_digest': actual_digest,
                },
            )
            assignment_proof_snapshot = conn.execute(
                text(
                    'SELECT flexbridge.academic_jsonb_snapshot(q) '
                    'FROM flexbridge.academic_assignment_proofs q WHERE q.assignment_id=CAST(:id AS uuid)'
                ),
                {'id': aid},
            ).scalar_one()
            consent_snapshot = conn.execute(
                text(
                    'SELECT flexbridge.academic_jsonb_snapshot(c) '
                    'FROM flexbridge.academic_assignment_consents c WHERE c.id=CAST(:id AS uuid)'
                ),
                {'id': consent['id']},
            ).scalar_one()
            conn.execute(
                proofs.insert().values(
                    decision_id=decision_id,
                    created_at=stamp,
                    origin='PUBLIC',
                    initial_snapshot=receipt,
                    placement_id=p['id'],
                    assignment_id=aid,
                    terms_id=tid,
                    terms_version=version,
                    **auth_info,
                    teacher_grant_id=current['_authority_grant_id'],
                    teacher_appointment_id=current['_authority_appointment_id'],
                    teacher_consent_id=consent['id'],
                    consent_snapshot=consent_snapshot,
                    assignment_proof_snapshot=assignment_proof_snapshot,
                    basis_snapshot=basis,
                    basis_digest=actual_digest,
                    audit_event_id=audit_entry['id'],
                    idempotency_key=idempotency_key,
                    request_fingerprint=digest,
                    receipt=receipt,
                )
            )
            return dict(receipt)


academic_decision_service = AcademicDecisionService()
