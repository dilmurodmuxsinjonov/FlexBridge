"""Durable API-121 feature-flag state administration (CAP-037, DB-092).

This unit administers *state only*. A flag row is never domain authority: capability, tenant, session, MFA,
agreement and provider boundaries (paid checkout, ratings, official export, WhatsApp) stay separate checks.
The protected flags and R2 are disable-only in R1 and R1_PAID_ORG_PLANS is a read-only alias of paid_checkout.

Total lock order (one global order, never reversed):
  1. advisory lock  actor + Idempotency-Key   (serializes cross-code same-key intent)
  2. advisory lock  flag code                 (serializes creation of a missing row)
  3. feature_flags row FOR UPDATE             (when it exists)
  4. users FOR SHARE -> sessions FOR SHARE -> exact ADMIN grant FOR SHARE
Authority is evaluated only after every wait, re-checked against the database clock, held by FOR SHARE locks
and re-evaluated by PostgreSQL commit-time constraint triggers (migration 0017).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, null, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction
from app.services.governance import GovernanceError

log = logging.getLogger(__name__)

R1_ENABLEABLE = ('R1_PART_TIME_JOBS', 'R1_GENERAL_INTERNSHIPS', 'R1_ACADEMIC_INTERNSHIPS')
PROTECTED_FLAGS = ('ratings', 'academic_official_export', 'WhatsApp', 'paid_checkout')
R2_FLAG = 'R2_FREELANCE_MARKETPLACE'
FLAG_ALIASES = {'R1_PAID_ORG_PLANS': 'paid_checkout'}
CATALOG = frozenset(R1_ENABLEABLE + PROTECTED_FLAGS + (R2_FLAG,))
SERVER_RULE_SCHEMA = {'schema_version': 1, 'scope': 'GLOBAL'}
AUDIT_ACTION = 'FEATURE_FLAG_ADMINISTERED'
AUDIT_SOURCE = 'API-121'


def intent_lock_key(user_id: str, idempotency_key: str) -> str:
    return 'feature-flag-admin:intent:' + user_id + ':' + idempotency_key


def code_lock_key(code: str) -> str:
    return 'feature-flag-admin:code:' + code


def _lock(conn, key: str) -> None:
    # One namespaced BIGINT lock (hashtextextended), not the invalid (int,bigint) signature.
    conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'), {'key': key})


@dataclass(frozen=True)
class AdminAuthority:
    user_id: str
    session_id: str
    auth_version: int
    grant_id: str
    decided_at: datetime


_EFFECTIVE_SQL = text("""
    SELECT (f.enabled AND e.enabled AND f.code=e.code AND f.rule_schema=CAST(:schema AS jsonb)
            AND e.rule_schema=f.rule_schema AND o.code=f.code
            AND flexbridge.feature_flag_snapshot(f)=e.after_snapshot)
    FROM flexbridge.feature_flags f
    JOIN flexbridge.feature_flag_origins o ON o.flag_id=f.id
    JOIN LATERAL (SELECT x.* FROM flexbridge.feature_flag_change_events x
                  WHERE x.flag_id=f.id ORDER BY x.version DESC LIMIT 1) e ON true
    WHERE f.code=:code""")


class FeatureFlagAdministrationService:
    audit = AppendOnlyAuditStore()

    # ----------------------------------------------------------------- reads
    def verify_storage(self) -> None:
        """Run the actual proof-backed read without turning storage failure into OFF.

        Success means the read is queryable, including when no flag exists. It
        does not certify feature prerequisites or pilot readiness. The savepoint
        keeps a caller's ambient transaction usable if this diagnostic fails.
        """
        with transaction() as conn:
            with conn.begin_nested():
                self._scalar_true(conn, {'code': R1_ENABLEABLE[0],
                    'schema': json.dumps(SERVER_RULE_SCHEMA)})

    def effective_enabled(self, code: str, *, conn=None) -> bool:
        """DB-backed, uncached. Only a valid latest PUBLIC event can make an R1 stage flag ON.

        Missing, legacy-only, mismatched, protected, R2, alias-of-protected, unknown and any storage failure
        read as OFF (fail closed)."""
        if not isinstance(code, str):
            return False
        target = FLAG_ALIASES.get(code, code)
        if target not in R1_ENABLEABLE:
            return False
        params = {'code': target, 'schema': json.dumps(SERVER_RULE_SCHEMA)}
        try:
            if conn is None:
                with transaction() as own:
                    # transaction() can join an implicit outer UoW as well as
                    # open one. Isolate a failed read in either case.
                    with own.begin_nested():
                        return self._scalar_true(own, params)
            with conn.begin_nested():  # a failed read must not poison the caller's transaction
                return self._scalar_true(conn, params)
        except SQLAlchemyError:
            log.warning('feature flag state unavailable; reporting OFF', exc_info=True)
            return False

    @staticmethod
    def _scalar_true(conn, params) -> bool:
        return conn.execute(_EFFECTIVE_SQL, params).scalar_one_or_none() is True

    # ---------------------------------------------------------------- writes
    def administer(self, *, actor, code, enabled, reason, idempotency_key, expected_version) -> dict[str, Any]:
        reason = self._validate(code, enabled, reason, idempotency_key, expected_version)
        user_id, session_id = self._actor_ids(actor)
        fingerprint = hashlib.sha256(json.dumps(
            {'api': AUDIT_SOURCE, 'code': code, 'enabled': enabled, 'reason': reason,
             'expected_version': expected_version}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        try:
            with transaction() as conn:
                self._require_read_committed(conn)
                _lock(conn, intent_lock_key(user_id, idempotency_key))
                _lock(conn, code_lock_key(code))
                flags = table('feature_flags')
                row = conn.execute(select(flags).where(flags.c.code == code).with_for_update()).mappings().first()
                authority = self._admin_authority(conn, actor, user_id, session_id)
                events = table('feature_flag_change_events')
                old = conn.execute(select(events).where(events.c.actor_id == user_id,
                    events.c.idempotency_key == idempotency_key)).mappings().first()
                if old:  # replay needs *current* ADMIN authority, never the original session
                    if old['request_fingerprint'] != fingerprint:
                        raise GovernanceError('IDEMPOTENCY_KEY_REUSED', status_code=409)
                    return dict(old['receipt'])
                if enabled and code in PROTECTED_FLAGS:
                    raise GovernanceError('FEATURE_PREREQUISITES_UNMET', status_code=409)
                if enabled and code == R2_FLAG:
                    raise GovernanceError('R2_FEATURE_OUT_OF_R1_SCOPE', status_code=409)
                prior, before = self._current_proof(conn, row)
                version = prior['version'] if prior else 0
                if expected_version != version:
                    raise GovernanceError('STALE_FEATURE_FLAG_VERSION', status_code=412)
                return self._commit_change(conn, authority, row, prior, before, code, enabled, reason,
                                           idempotency_key, fingerprint)
        except IntegrityError as exc:  # commit-time proof triggers fire when the outer transaction ends
            raise self._proof_error(exc) from exc

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _validate(code, enabled, reason, idempotency_key, expected_version) -> str:
        if not isinstance(code, str) or (code not in CATALOG and code not in FLAG_ALIASES):
            raise GovernanceError('FEATURE_FLAG_NOT_FOUND', status_code=404)
        if code in FLAG_ALIASES:
            raise GovernanceError('FEATURE_FLAG_ALIAS_READ_ONLY', status_code=409)
        if not isinstance(enabled, bool):
            raise GovernanceError('INVALID_FEATURE_FLAG_ENABLED', status_code=422)
        if not isinstance(reason, str) or not 15 <= len(reason.strip()) <= 2000:
            raise GovernanceError('INVALID_FEATURE_FLAG_REASON', status_code=422)
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise GovernanceError('INVALID_IDEMPOTENCY_KEY', status_code=400)
        if type(expected_version) is not int or expected_version < 0:
            raise GovernanceError('INVALID_EXPECTED_VERSION', status_code=400)
        return reason.strip()

    @staticmethod
    def _actor_ids(actor) -> tuple[str, str]:
        try:  # actual ActorContext session only; no user-id fallback
            return str(UUID(str(actor.user_id))), str(UUID(str(actor.session_id)))
        except (AttributeError, TypeError, ValueError):
            raise GovernanceError('MFA_REQUIRED', status_code=403) from None

    @staticmethod
    def _require_read_committed(conn) -> None:
        if conn.execute(text("SELECT current_setting('transaction_isolation')")).scalar_one() != 'read committed':
            raise GovernanceError('FEATURE_FLAG_ISOLATION_UNSAFE', status_code=503)

    @staticmethod
    def _admin_authority(conn, actor, user_id: str, session_id: str) -> AdminAuthority:
        """Current MFA session + exact deterministically locked ADMIN grant, evaluated after all waits."""
        users, sessions, grants, roles = (table(n) for n in ('users', 'sessions', 'platform_role_grants', 'role_catalog'))
        mfa = GovernanceError('MFA_REQUIRED', status_code=403)
        user = conn.execute(select(users.c.auth_version).where(users.c.id == user_id, users.c.status == 'ACTIVE')
            .with_for_update(read=True)).first()
        if not user:
            raise mfa
        session = conn.execute(select(sessions.c.expires_at).where(sessions.c.id == session_id,
            sessions.c.user_id == user_id, sessions.c.auth_version == user.auth_version,
            sessions.c.revoked_at.is_(None), sessions.c.assurance == 'MFA',
            sessions.c.expires_at > func.clock_timestamp()).with_for_update(read=True)).first()
        if not session:
            raise mfa
        grant = conn.execute(select(grants.c.id, grants.c.expires_at).join(roles, roles.c.id == grants.c.role_id)
            .where(grants.c.user_id == user_id, grants.c.revoked_at.is_(None),
                   grants.c.expires_at > func.clock_timestamp(), grants.c.granted_by_id != grants.c.user_id,
                   roles.c.code == 'ADMIN', roles.c.scope_kind == 'PLATFORM')
            .order_by(grants.c.expires_at.desc(), grants.c.id).limit(1)
            .with_for_update(read=True, of=(grants, roles))).first()
        if not grant:
            raise GovernanceError('FORBIDDEN_ROLE', status_code=403)
        decided_at = conn.execute(select(func.clock_timestamp())).scalar_one()
        if session.expires_at <= decided_at:
            raise mfa
        if grant.expires_at <= decided_at:
            raise GovernanceError('FORBIDDEN_ROLE', status_code=403)
        return AdminAuthority(user_id, session_id, user.auth_version, str(grant.id), decided_at)

    @staticmethod
    def _snapshot(conn, flag_id: str) -> dict[str, Any]:
        return conn.execute(text('SELECT flexbridge.feature_flag_snapshot(f) FROM flexbridge.feature_flags f '
                                 'WHERE f.id=CAST(:id AS uuid)'), {'id': flag_id}).scalar_one()

    @staticmethod
    def _digest(conn, value: dict[str, Any] | None) -> str | None:
        if value is None:
            return None
        return conn.execute(text('SELECT flexbridge.feature_flag_digest(CAST(:value AS jsonb))'),
                            {'value': json.dumps(value)}).scalar_one()

    def _current_proof(self, conn, row):
        """Latest event (or None) and the canonical snapshot, refusing a row whose state diverged from proof."""
        if row is None:
            return None, None
        origins, events = table('feature_flag_origins'), table('feature_flag_change_events')
        origin = conn.execute(select(origins).where(origins.c.flag_id == row['id'])).mappings().first()
        prior = conn.execute(select(events).where(events.c.flag_id == row['id'])
            .order_by(events.c.version.desc()).limit(1)).mappings().first()
        before = self._snapshot(conn, row['id'])
        expected = prior['after_snapshot'] if prior else (origin['initial_snapshot'] if origin else None)
        if origin is None or before != expected:
            raise GovernanceError('FEATURE_FLAG_STATE_MISMATCH', status_code=409)
        return (dict(prior) if prior else None), before

    def _commit_change(self, conn, authority, row, prior, before, code, enabled, reason, idempotency_key, fingerprint):
        flags, origins, events = (table(n) for n in ('feature_flags', 'feature_flag_origins', 'feature_flag_change_events'))
        decided_at = authority.decided_at
        state = dict(enabled=enabled, rule_schema=dict(SERVER_RULE_SCHEMA), changed_by_id=authority.user_id,
                     reason=reason, updated_at=decided_at)
        if row is None:
            flag_id = str(uuid4())
            conn.execute(flags.insert().values(id=flag_id, created_at=decided_at, code=code, **state))
        else:
            flag_id = str(row['id'])
            conn.execute(flags.update().where(flags.c.id == flag_id).values(**state))
        after = self._snapshot(conn, flag_id)
        if row is None:  # preserve the exact initial snapshot; legacy origins are never rewritten
            conn.execute(origins.insert().values(flag_id=flag_id, code=code, origin='PUBLIC', initial_snapshot=after))
        version = (prior['version'] if prior else 0) + 1
        event_id = str(uuid4())
        audit_id = self.audit.append_audit_event(actor_id=authority.user_id, action=AUDIT_ACTION,
            entity_type='feature_flag', entity_id=flag_id,
            metadata={'source': AUDIT_SOURCE, 'capability': 'CAP-037', 'event_id': event_id, 'code': code,
                      'version': version, 'enabled': enabled, 'session_id': authority.session_id,
                      'admin_grant_id': authority.grant_id, 'auth_version': authority.auth_version})['id']
        receipt = {'flag_id': flag_id, 'event_id': event_id, 'audit_event_id': audit_id, 'code': code,
                   'enabled': enabled, 'effective_enabled': enabled and code in R1_ENABLEABLE,
                   'version': version, 'reason': reason,
                   'decided_at': decided_at.astimezone(timezone.utc).isoformat()}
        before_digest = self._digest(conn, before)
        conn.execute(events.insert().values(id=event_id, flag_id=flag_id, code=code, version=version,
            prior_event_id=prior['id'] if prior else null(), enabled=enabled, rule_schema=dict(SERVER_RULE_SCHEMA),
            reason=reason, before_snapshot=null() if before is None else before, after_snapshot=after,
            before_digest=null() if before_digest is None else before_digest,
            after_digest=self._digest(conn, after), actor_id=authority.user_id, session_id=authority.session_id,
            auth_version=authority.auth_version, admin_grant_id=authority.grant_id, decided_at=decided_at,
            idempotency_key=idempotency_key, request_fingerprint=fingerprint, audit_event_id=audit_id,
            receipt=receipt))
        return receipt

    @staticmethod
    def _proof_error(exc: IntegrityError) -> GovernanceError:
        message = str(getattr(exc, 'orig', exc))
        if 'ADMIN authority' in message:
            return GovernanceError('FEATURE_FLAG_AUTHORITY_REQUIRED', status_code=403)
        if 'idempotency_key' in message:
            return GovernanceError('IDEMPOTENCY_KEY_REUSED', status_code=409)
        if 'locked in R1' in message:
            return GovernanceError('FEATURE_PREREQUISITES_UNMET', status_code=409)
        return GovernanceError('FEATURE_FLAG_PROOF_REJECTED', status_code=409)


flag_admin_service = FeatureFlagAdministrationService()
