"""API-121 / DB-092 feature-flag proof-control regressions (Issue 72 / AGY006).

Focused proof-control regression suite testing:
1. Exact receipt and digest DB controls: rejected by guard trigger BEFORE unique constraint checks.
   - Corrupted receipt fields (wrong enabled, extra key, missing decided_at)
   - Corrupted after_digest
   - Verifying exact guard rejection and zero persistence after rollback.
2. Real clock expiry after valid event insertion but before outer commit:
   - Sets trusted fixture platform ADMIN grant expiry to the near future
   - Inserts valid change while grant is still valid
   - Waits bounded via DB clock polling until actual expiry
   - Verifies deferred trigger rollback on outer commit with explicit current ADMIN authority error.
3. Actual REPEATABLE READ outer transaction isolation rejection:
   - Uses storage.transaction ContextVar joining
   - Issues SET TRANSACTION ISOLATION LEVEL REPEATABLE READ before any queries
   - Verifies 503 FEATURE_FLAG_ISOLATION_UNSAFE with no side effects.

Trusted role/grant fixture mutations are explicitly labelled test controls, not public workflows.
All sessions use genuine server authentication from the identities fixture (no synthetic sessions).
"""
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import func, null, select, text
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction
from app.services.feature_flag_admin import flag_admin_service
from app.services.governance import GovernanceError

TEST_REASON = "Operational review decision for proof control regressions"


def actor_for(user: dict) -> ActorContext:
    """Resolve an authenticated ActorContext from the real identities fixture session."""
    return ActorContext(user['user_id'], user['session_id'], ('ADMIN',))


# -----------------------------------------------------------------------------
# 1. Exact receipt and digest DB controls (guard trigger rejects BEFORE unique)
# -----------------------------------------------------------------------------

@pytest.mark.parametrize('corruption', ['wrong_enabled', 'extra_key', 'missing_decided_at'])
def test_event_insert_guard_rejects_corrupted_receipt_before_version_unique_check(identities, corruption):
    """Attempting to insert an event with a corrupted receipt fails at the BEFORE INSERT trigger.

    The BEFORE INSERT guard trigger validates exact minimal receipt equality before table-level
    UNIQUE(flag_id, version) constraints are checked. We verify the specific receipt guard error
    and ensure no event or audit event persists after rollback.
    """
    admin = identities('ADMIN')
    admin_actor = actor_for(admin)
    code = 'R1_PART_TIME_JOBS'

    # 1. Create one valid real ADMIN event first.
    receipt = flag_admin_service.administer(
        actor=admin_actor,
        code=code,
        enabled=True,
        reason=TEST_REASON,
        idempotency_key=str(uuid4()),
        expected_version=0,
    )

    events = table('feature_flag_change_events')
    audits = table('audit_events')

    # Load baseline event and record baseline counts in a new transaction.
    with transaction() as conn:
        base_event = dict(conn.execute(select(events).where(events.c.id == receipt['event_id'])).mappings().one())
        initial_events_count = conn.execute(select(func.count()).select_from(events)).scalar_one()
        initial_audits_count = conn.execute(
            select(func.count()).select_from(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).scalar_one()

    # 2. In a new transaction, prepare a new event UUID and genuine same-transaction audit event,
    # then attempt insertion with corrupted receipt.
    with pytest.raises(IntegrityError, match='feature flag event requires the exact minimal receipt'):
        with transaction() as conn:
            new_event_id = str(uuid4())
            audit_entry = AppendOnlyAuditStore().append_audit_event(
                actor_id=str(base_event['actor_id']),
                action='FEATURE_FLAG_ADMINISTERED',
                entity_type='feature_flag',
                entity_id=str(base_event['flag_id']),
                metadata={
                    'source': 'API-121',
                    'capability': 'CAP-037',
                    'event_id': new_event_id,
                    'code': base_event['code'],
                    'version': base_event['version'],
                    'enabled': base_event['enabled'],
                    'session_id': str(base_event['session_id']),
                    'admin_grant_id': str(base_event['admin_grant_id']),
                    'auth_version': base_event['auth_version'],
                },
            )
            new_audit_id = audit_entry['id']

            copy_event = dict(base_event)
            copy_event['id'] = new_event_id
            copy_event['idempotency_key'] = str(uuid4())
            copy_event['audit_event_id'] = new_audit_id

            # Preserve SQL NULL for absent optional columns.
            if copy_event.get('before_snapshot') is None:
                copy_event['before_snapshot'] = null()
            if copy_event.get('before_digest') is None:
                copy_event['before_digest'] = null()
            if copy_event.get('prior_event_id') is None:
                copy_event['prior_event_id'] = null()

            new_receipt = dict(base_event['receipt'])
            new_receipt['event_id'] = new_event_id
            new_receipt['audit_event_id'] = new_audit_id

            if corruption == 'wrong_enabled':
                new_receipt['enabled'] = not base_event['enabled']
            elif corruption == 'extra_key':
                new_receipt['extra_internal_receipt_key'] = 'unauthorized_payload'
            elif corruption == 'missing_decided_at':
                new_receipt.pop('decided_at', None)

            copy_event['receipt'] = new_receipt

            conn.execute(events.insert().values(**copy_event))

    # Assert no extra flag event or audit event persisted after rollback.
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(events)).scalar_one() == initial_events_count
        assert conn.execute(
            select(func.count()).select_from(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).scalar_one() == initial_audits_count


def test_event_insert_guard_rejects_wrong_after_digest_before_version_unique_check(identities):
    """Attempting to insert an event with a corrupted after_digest fails at the BEFORE INSERT trigger.

    The BEFORE INSERT guard trigger validates canonical flag state and snapshot digest equality
    before the table-level UNIQUE(flag_id, version) constraint check. We verify the specific
    canonical flag state guard error and verify that no event or audit event persists.
    """
    admin = identities('ADMIN')
    admin_actor = actor_for(admin)
    code = 'R1_PART_TIME_JOBS'

    # 1. Create one valid real ADMIN event first.
    receipt = flag_admin_service.administer(
        actor=admin_actor,
        code=code,
        enabled=True,
        reason=TEST_REASON,
        idempotency_key=str(uuid4()),
        expected_version=0,
    )

    events = table('feature_flag_change_events')
    audits = table('audit_events')

    with transaction() as conn:
        base_event = dict(conn.execute(select(events).where(events.c.id == receipt['event_id'])).mappings().one())
        initial_events_count = conn.execute(select(func.count()).select_from(events)).scalar_one()
        initial_audits_count = conn.execute(
            select(func.count()).select_from(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).scalar_one()

    # 2. In a new transaction, prepare new UUID, new same-transaction audit, and matching receipt,
    # but corrupt after_digest to a valid 64-hex string that differs from sha256(after_snapshot).
    with pytest.raises(IntegrityError, match='feature flag event must equal the canonical flag state'):
        with transaction() as conn:
            new_event_id = str(uuid4())
            audit_entry = AppendOnlyAuditStore().append_audit_event(
                actor_id=str(base_event['actor_id']),
                action='FEATURE_FLAG_ADMINISTERED',
                entity_type='feature_flag',
                entity_id=str(base_event['flag_id']),
                metadata={
                    'source': 'API-121',
                    'capability': 'CAP-037',
                    'event_id': new_event_id,
                    'code': base_event['code'],
                    'version': base_event['version'],
                    'enabled': base_event['enabled'],
                    'session_id': str(base_event['session_id']),
                    'admin_grant_id': str(base_event['admin_grant_id']),
                    'auth_version': base_event['auth_version'],
                },
            )
            new_audit_id = audit_entry['id']

            copy_event = dict(base_event)
            copy_event['id'] = new_event_id
            copy_event['idempotency_key'] = str(uuid4())
            copy_event['audit_event_id'] = new_audit_id

            if copy_event.get('before_snapshot') is None:
                copy_event['before_snapshot'] = null()
            if copy_event.get('before_digest') is None:
                copy_event['before_digest'] = null()
            if copy_event.get('prior_event_id') is None:
                copy_event['prior_event_id'] = null()

            new_receipt = dict(base_event['receipt'])
            new_receipt['event_id'] = new_event_id
            new_receipt['audit_event_id'] = new_audit_id
            copy_event['receipt'] = new_receipt

            # Deliberately mismatched after_digest (passes column regex CHECK, fails guard state check)
            copy_event['after_digest'] = 'f' * 64

            conn.execute(events.insert().values(**copy_event))

    # Assert no extra flag event or audit event persisted after rollback.
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(events)).scalar_one() == initial_events_count
        assert conn.execute(
            select(func.count()).select_from(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).scalar_one() == initial_audits_count


# -----------------------------------------------------------------------------
# 2. Real clock expiry after valid event insertion but before outer commit
# -----------------------------------------------------------------------------

def test_real_clock_expiry_after_valid_event_insertion_fails_outer_commit(identities):
    """Real clock expiry between valid event insertion and outer commit triggers deferred rollback.

    Trusted fixture mutation label: Setting platform_role_grants.expires_at to the near future
    is an explicit trusted test fixture control used to verify the deferred constraint trigger
    `feature_flag_event_current_at_commit` without synthetic credentials.

    Workflow:
    - In an outer transaction, set exact ADMIN grant expiry to near future (~1.5s).
    - Call service to insert valid change (succeeds, version 1 event created).
    - Wait bounded via real DB clock polling until actual expiry.
    - Outer commit attempts to finalize; deferred trigger checks current authority at commit and fails.
    - Entire transaction rolls back: no flag, origin, event, or audit event survives.
    """
    admin = identities('ADMIN')
    admin_actor = actor_for(admin)
    code = 'R1_PART_TIME_JOBS'

    flags = table('feature_flags')
    origins = table('feature_flag_origins')
    events = table('feature_flag_change_events')
    audits = table('audit_events')
    grants = table('platform_role_grants')

    with pytest.raises(IntegrityError, match='feature flag change requires current ADMIN authority at commit'):
        with transaction() as conn:
            # 1. Trusted fixture mutation: set ADMIN grant expiry to near future (1.5 seconds)
            conn.execute(
                grants.update()
                .where(grants.c.user_id == admin['user_id'])
                .values(expires_at=func.clock_timestamp() + text("interval '1.5 seconds'"))
            )

            # 2. Call service to insert valid change while grant is still valid
            receipt = flag_admin_service.administer(
                actor=admin_actor,
                code=code,
                enabled=True,
                reason=TEST_REASON,
                idempotency_key=str(uuid4()),
                expected_version=0,
            )
            assert receipt['version'] == 1
            assert receipt['code'] == code

            # 3. Wait bounded via DB clock polling until actual expiry (bounded to 8 seconds)
            deadline = monotonic() + 8.0
            while True:
                expired = conn.execute(
                    text(
                        "SELECT clock_timestamp() >= expires_at "
                        "FROM flexbridge.platform_role_grants "
                        "WHERE user_id = CAST(:uid AS uuid)"
                    ),
                    {'uid': admin['user_id']},
                ).scalar_one()
                if expired:
                    break
                if monotonic() >= deadline:
                    raise TimeoutError("Trusted fixture ADMIN grant did not expire within bounded DB clock wait")
                sleep(0.05)

            # 4. Outer commit triggers deferred constraint trigger feature_flag_event_current_at_commit

    # Assert that no flag row, origin, change event, or administered audit survives rollback.
    with transaction() as conn:
        assert conn.execute(select(flags).where(flags.c.code == code)).first() is None
        assert conn.execute(select(origins).where(origins.c.code == code)).first() is None
        assert conn.execute(select(events).where(events.c.code == code)).first() is None
        assert conn.execute(
            select(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).first() is None


# -----------------------------------------------------------------------------
# 3. REPEATABLE READ outer transaction isolation rejection
# -----------------------------------------------------------------------------

def test_repeatable_read_outer_transaction_fails_isolation_unsafe_with_no_effects(identities):
    """An outer transaction in REPEATABLE READ isolation is rejected with 503 and has no effects.

    Uses storage.transaction ContextVar joining with SET TRANSACTION ISOLATION LEVEL REPEATABLE READ
    executed before any queries. The service must raise 503 FEATURE_FLAG_ISOLATION_UNSAFE and leave
    no persistent flag, origin, event, or audit changes.
    """
    admin = identities('ADMIN')
    admin_actor = actor_for(admin)
    code = 'R1_PART_TIME_JOBS'
    key = str(uuid4())

    flags = table('feature_flags')
    origins = table('feature_flag_origins')
    events = table('feature_flag_change_events')
    audits = table('audit_events')

    with pytest.raises(GovernanceError) as raised:
        with transaction() as conn:
            conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            flag_admin_service.administer(
                actor=admin_actor,
                code=code,
                enabled=True,
                reason=TEST_REASON,
                idempotency_key=key,
                expected_version=0,
            )

    assert raised.value.status_code == 503
    assert raised.value.code == 'FEATURE_FLAG_ISOLATION_UNSAFE'

    # Assert no side effects survived
    with transaction() as conn:
        assert conn.execute(select(flags).where(flags.c.code == code)).first() is None
        assert conn.execute(select(origins).where(origins.c.code == code)).first() is None
        assert conn.execute(select(events).where(events.c.code == code)).first() is None
        assert conn.execute(
            select(audits).where(audits.c.action == 'FEATURE_FLAG_ADMINISTERED')
        ).first() is None
