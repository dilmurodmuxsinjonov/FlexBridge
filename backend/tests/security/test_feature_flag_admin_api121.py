"""API-121 durable feature-flag administration: actual sessions, SQL proofs, upgrade and lock-wait controls.

Trusted fixtures that are NOT public workflows: platform ADMIN/MODERATOR grants (via the existing `identities`
fixture), legacy DB-092 rows seeded at 0016, and role/grant mutations. All sessions come from real server
authentication (`auth_service.login` with password and TOTP verification).
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from academic_review_observer import labeled_requests, wait_for_requests
from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import get_engine, now, table, transaction
from app.services.auth import AuthError, auth_service, generate_totp_code
from app.services.feature_flag_admin import PROTECTED_FLAGS, code_lock_key, flag_admin_service, intent_lock_key
from app.services.governance import GovernanceError
from app.services.placements import insert_row
from test_institution_migration import populated_database

REASON = 'Operator approved change after review'
SERVER_SCHEMA = {'schema_version': 1, 'scope': 'GLOBAL'}
PROOF_TABLES = ('feature_flags', 'feature_flag_origins', 'feature_flag_change_events', 'audit_events')
LEGACY_CODES = ('paid_checkout', 'R1_PAID_ORG_PLANS', 'ratings', 'R2_FREELANCE_MARKETPLACE',
                'R1_GENERAL_INTERNSHIPS', 'legacy_unlisted_flag')


def actor_for(user):
    return ActorContext(user['user_id'], user['session_id'], ('ADMIN',))


def administer(user, code, enabled, key, version, actor=None, reason=REASON):
    return flag_admin_service.administer(actor=actor or actor_for(user), code=code, enabled=enabled,
        reason=reason, idempotency_key=key, expected_version=version)


def patch(client, user, code, enabled, key, version, **extra):
    return client.patch('/api/v1/operator/feature-flags/' + code,
        headers={**user['headers'], 'Idempotency-Key': key, 'If-Match': '"%d"' % version},
        json={'enabled': enabled, 'reason': REASON, **extra})


def count(name):
    with transaction() as conn:
        return conn.execute(text('SELECT count(*) FROM flexbridge.' + name)).scalar_one()


def proof_state():
    with transaction() as conn:
        return {name: sorted((dict(r) for r in conn.execute(select(table(name))).mappings()), key=repr)
                for name in PROOF_TABLES}


def fresh_mfa_actor(user):
    """Authenticate a genuine new MFA session via auth_service.login using the fixture password and TOTP secret."""
    deadline = monotonic() + 35
    while True:
        try:
            session = auth_service.login(user_id=user['user_id'], password='correct-passphrase-2026',
                                         totp_code=generate_totp_code(user['totp_secret']))
            break
        except AuthError:
            if monotonic() >= deadline:
                raise
            sleep(0.5)
    assert session['session_id'] != user['session_id']
    return ActorContext(user['user_id'], session['session_id'], ('ADMIN',))


def hold(conn, key):
    conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'), {'key': key})


def error_of(call):
    with pytest.raises(GovernanceError) as raised:
        call()
    return raised.value.status_code, raised.value.code


def audit_rows_for(event_id):
    with transaction() as conn:
        return [dict(r) for r in conn.execute(select(table('audit_events')).where(
            table('audit_events').c.action == 'FEATURE_FLAG_ADMINISTERED')).mappings()
            if r['scope_snapshot'].get('event_id') == event_id]


# ---------------------------------------------------------------- receipts, sessions
def test_exact_receipt_survives_author_logout_and_replays_only_for_a_current_admin(client, identities):
    admin = identities('ADMIN'); key = str(uuid4())
    first = patch(client, admin, 'R1_PART_TIME_JOBS', True, key, 0)
    assert first.status_code == 200, first.text
    receipt = first.json()
    assert set(receipt) == {'flag_id', 'event_id', 'audit_event_id', 'code', 'enabled', 'effective_enabled',
                            'version', 'reason', 'decided_at'}
    assert receipt['version'] == 1 and receipt['effective_enabled'] is True
    assert (count('feature_flags'), count('feature_flag_origins'), count('feature_flag_change_events')) == (1, 1, 1)
    audits = audit_rows_for(receipt['event_id'])
    assert len(audits) == 1 and audits[0]['id'] == receipt['audit_event_id'] and audits[0]['actor_id'] == admin['user_id']
    with transaction() as conn:
        stored = conn.execute(text('SELECT receipt, session_id, admin_grant_id FROM flexbridge.feature_flag_change_events')).mappings().one()
    assert stored['receipt'] == receipt and str(stored['session_id']) == admin['session_id']
    before_logout = proof_state()
    # The valid configuration outlives the original author's session; logout adds SESSION_REVOKED audit.
    assert client.delete('/api/v1/me/sessions/' + admin['session_id'], headers=admin['headers']).status_code == 200
    after_logout = proof_state()
    for name in ('feature_flags', 'feature_flag_origins', 'feature_flag_change_events'):
        assert after_logout[name] == before_logout[name]
    prior_audit_ids = {row['id'] for row in before_logout['audit_events']}
    new_audits = [row for row in after_logout['audit_events'] if row['id'] not in prior_audit_ids]
    assert len(new_audits) == 1 and new_audits[0]['action'] == 'SESSION_REVOKED'
    assert new_audits[0]['object_type'] == 'session' and new_audits[0]['object_key'] == admin['session_id']
    assert flag_admin_service.effective_enabled('R1_PART_TIME_JOBS') is True
    assert patch(client, admin, 'R1_PART_TIME_JOBS', True, key, 0).status_code == 401
    current = fresh_mfa_actor(admin)
    post_logout_baseline = proof_state()
    assert post_logout_baseline == after_logout
    replay = administer(admin, 'R1_PART_TIME_JOBS', True, key, 0, actor=current)
    assert replay == receipt and proof_state() == post_logout_baseline  # identical stored receipt, no new proof/audit rows
    with transaction() as conn:
        revoked = conn.execute(select(table('sessions').c.revoked_at).where(
            table('sessions').c.id == admin['session_id'])).scalar_one()
    assert revoked is not None
    second = administer(admin, 'R1_PART_TIME_JOBS', False, str(uuid4()), 1, actor=current)
    assert second['version'] == 2 and flag_admin_service.effective_enabled('R1_PART_TIME_JOBS') is False
    assert administer(admin, 'R1_PART_TIME_JOBS', True, key, 0, actor=current) == receipt   # old key after a later version
    assert error_of(lambda: administer(admin, 'R1_PART_TIME_JOBS', False, key, 0, actor=current)) == (409, 'IDEMPOTENCY_KEY_REUSED')
    assert error_of(lambda: administer(admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0, actor=current)) == (412, 'STALE_FEATURE_FLAG_VERSION')


MUTATIONS = {'revoked_grant': 'FORBIDDEN_ROLE', 'expired_grant': 'FORBIDDEN_ROLE',
             'password_session': 'MFA_REQUIRED', 'revoked_session': 'MFA_REQUIRED',
             'stale_auth_version': 'MFA_REQUIRED', 'suspended': 'MFA_REQUIRED'}


@pytest.mark.parametrize('change', sorted(MUTATIONS))
def test_only_current_mfa_session_with_a_current_independent_admin_grant_may_administer(identities, change):
    admin = identities('ADMIN'); users, sessions, grants = (table(n) for n in ('users', 'sessions', 'platform_role_grants'))
    with transaction() as conn:
        mine = grants.c.user_id == admin['user_id']
        if change == 'revoked_grant': conn.execute(grants.update().where(mine).values(revoked_at=now(), updated_at=now()))
        elif change == 'expired_grant': conn.execute(grants.update().where(mine).values(expires_at=now() - timedelta(seconds=1), updated_at=now()))
        elif change == 'password_session': conn.execute(sessions.update().where(sessions.c.id == admin['session_id']).values(assurance='PASSWORD'))
        elif change == 'revoked_session': conn.execute(sessions.update().where(sessions.c.id == admin['session_id']).values(revoked_at=now()))
        elif change == 'stale_auth_version': conn.execute(users.update().where(users.c.id == admin['user_id']).values(auth_version=users.c.auth_version + 1, updated_at=now()))
        else: conn.execute(users.update().where(users.c.id == admin['user_id']).values(status='SUSPENDED', updated_at=now()))
    before = proof_state()
    assert error_of(lambda: administer(admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0)) == (403, MUTATIONS[change])
    assert proof_state() == before


def test_self_granted_admin_authority_is_rejected_by_the_existing_database_constraint(identities):
    admin=identities('ADMIN');before=proof_state();grants=table('platform_role_grants')
    # The trusted fixture cannot manufacture this invalid authority: the older
    # IAM constraint rejects it before the flag service could ever observe it.
    with pytest.raises(IntegrityError,match='chk_platform_grant_not_self'),transaction() as conn:
        conn.execute(grants.update().where(grants.c.user_id==admin['user_id']).values(
            granted_by_id=admin['user_id'],updated_at=now()))
    assert proof_state()==before
    with transaction() as conn:
        grant=conn.execute(select(grants).where(grants.c.user_id==admin['user_id'])).mappings().one()
        assert grant['granted_by_id']!=grant['user_id']


@pytest.mark.parametrize('kind', ['wrong_role', 'missing_session', 'foreign_session', 'unknown_session'])
def test_service_never_rebuilds_admin_authority_from_a_user_id(identities, kind):
    admin = identities('ADMIN'); other = identities('MODERATOR')
    actors = {'wrong_role': ActorContext(other['user_id'], other['session_id'], ('ADMIN',)),
              'missing_session': ActorContext(admin['user_id'], None, ('ADMIN',)),
              'foreign_session': ActorContext(admin['user_id'], other['session_id'], ('ADMIN',)),
              'unknown_session': ActorContext(admin['user_id'], str(uuid4()), ('ADMIN',))}
    before = proof_state()
    status, code = error_of(lambda: administer(admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0, actor=actors[kind]))
    assert status == 403 and code == ('FORBIDDEN_ROLE' if kind == 'wrong_role' else 'MFA_REQUIRED')
    assert proof_state() == before


# ------------------------------------------------------------ catalog, lockout, schema
@pytest.mark.parametrize('code', PROTECTED_FLAGS)
def test_protected_flags_cannot_be_enabled_but_disable_is_recorded(identities, code):
    admin = identities('ADMIN'); before = proof_state()
    assert error_of(lambda: administer(admin, code, True, str(uuid4()), 0)) == (409, 'FEATURE_PREREQUISITES_UNMET')
    assert proof_state() == before
    receipt = administer(admin, code, False, str(uuid4()), 0)
    assert receipt['enabled'] is False and receipt['effective_enabled'] is False and receipt['version'] == 1
    assert flag_admin_service.effective_enabled(code) is False


def test_r2_alias_unknown_code_and_client_schema_cannot_enable_anything(client, identities):
    admin = identities('ADMIN'); before = proof_state()
    assert error_of(lambda: administer(admin, 'R2_FREELANCE_MARKETPLACE', True, str(uuid4()), 0)) == (409, 'R2_FEATURE_OUT_OF_R1_SCOPE')
    for enabled in (True, False):
        assert error_of(lambda: administer(admin, 'R1_PAID_ORG_PLANS', enabled, str(uuid4()), 0)) == (409, 'FEATURE_FLAG_ALIAS_READ_ONLY')
    assert error_of(lambda: administer(admin, 'ratings_v2', False, str(uuid4()), 0)) == (404, 'FEATURE_FLAG_NOT_FOUND')
    assert error_of(lambda: administer(admin, 'whatsapp', False, str(uuid4()), 0)) == (404, 'FEATURE_FLAG_NOT_FOUND')
    for extra in ({'rule_schema': SERVER_SCHEMA}, {'org_overrides': {str(uuid4()): True}}):
        assert patch(client, admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0, **extra).status_code == 422
    assert proof_state() == before
    assert flag_admin_service.effective_enabled('R1_PAID_ORG_PLANS') is False
    assert flag_admin_service.effective_enabled('R2_FREELANCE_MARKETPLACE') is False


# ---------------------------------------------------------------- direct SQL
def test_raw_sql_cannot_forge_change_or_delete_effective_state(identities):
    admin = identities('ADMIN')
    administer(admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0)
    administer(admin, 'ratings', False, str(uuid4()), 0)
    before = proof_state(); flags = table('feature_flags')
    attempts = [
        (None, lambda c: c.execute(flags.update().where(flags.c.code == 'R1_PART_TIME_JOBS').values(enabled=False))),
        (None, lambda c: c.execute(flags.update().where(flags.c.code == 'R1_PART_TIME_JOBS').values(reason='Edited outside proof ledger'))),
        ('identity', lambda c: c.execute(flags.update().where(flags.c.code == 'ratings').values(code='WhatsApp'))),
        ('deleted', lambda c: c.execute(flags.delete())),
        ('locked in R1', lambda c: c.execute(flags.update().where(flags.c.code == 'ratings').values(enabled=True))),
        (None, lambda c: c.execute(flags.insert().values(id=str(uuid4()), created_at=now(), updated_at=now(),
            code='R1_ACADEMIC_INTERNSHIPS', enabled=True, rule_schema=SERVER_SCHEMA,
            changed_by_id=admin['user_id'], reason=REASON))),
        (None, lambda c: c.execute(text('UPDATE flexbridge.feature_flag_origins SET created_at=now()'))),
        (None, lambda c: c.execute(text('DELETE FROM flexbridge.feature_flag_origins'))),
        (None, lambda c: c.execute(text('UPDATE flexbridge.feature_flag_change_events SET enabled=NOT enabled'))),
        (None, lambda c: c.execute(text('DELETE FROM flexbridge.feature_flag_change_events')))]
    for message, attempt in attempts:
        with pytest.raises(IntegrityError, match=message), get_engine().begin() as conn:
            attempt(conn)
    assert proof_state() == before
    assert flag_admin_service.effective_enabled('R1_PART_TIME_JOBS') is True
    assert flag_admin_service.effective_enabled('R1_ACADEMIC_INTERNSHIPS') is False


# ---------------------------------------------------------------- audit, timezone, processes
def test_failure_after_audit_insert_rolls_back_flag_origin_audit_and_event(identities, monkeypatch):
    admin = identities('ADMIN'); before = proof_state(); original = AppendOnlyAuditStore.append_audit_event
    def audit_then_fail(self, **kwargs):
        original(self, **kwargs)
        raise RuntimeError('Injected feature flag failure after audit insert')
    with monkeypatch.context() as patched:
        patched.setattr(AppendOnlyAuditStore, 'append_audit_event', audit_then_fail)
        with pytest.raises(RuntimeError, match='Injected feature flag failure'):
            administer(admin, 'R1_GENERAL_INTERNSHIPS', True, str(uuid4()), 0)
    assert proof_state() == before
    assert administer(admin, 'R1_GENERAL_INTERNSHIPS', True, str(uuid4()), 0)['version'] == 1


def test_canonical_state_equality_is_independent_of_session_timezone(identities):
    admin = identities('ADMIN'); flags = table('feature_flags')
    with transaction() as conn:
        conn.execute(text("SET LOCAL TimeZone TO 'Pacific/Kiritimati'"))
        receipt = administer(admin, 'R1_ACADEMIC_INTERNSHIPS', True, str(uuid4()), 0)
    seen = {}
    for zone in ('Pacific/Kiritimati', 'America/Los_Angeles', 'UTC'):
        with get_engine().begin() as conn:
            conn.execute(text("SET LOCAL TimeZone TO '" + zone + "'"))
            seen[zone] = (conn.execute(text('SELECT flexbridge.feature_flag_snapshot(f) FROM flexbridge.feature_flags f')).scalar_one(),
                          conn.execute(text('SELECT to_jsonb(f) FROM flexbridge.feature_flags f')).scalar_one(),
                          flag_admin_service.effective_enabled('R1_ACADEMIC_INTERNSHIPS', conn=conn))
    assert len({json.dumps(v[0], sort_keys=True) for v in seen.values()}) == 1       # stable helper
    assert len({json.dumps(v[1], sort_keys=True) for v in seen.values()}) > 1        # raw to_jsonb is zone dependent
    assert all(v[2] is True for v in seen.values()) and receipt['effective_enabled'] is True


def test_valid_configuration_is_read_by_a_separate_process(identities):
    admin = identities('ADMIN'); administer(admin, 'R1_PART_TIME_JOBS', True, str(uuid4()), 0)
    backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = ('from app.services.feature_flag_admin import flag_admin_service as s;'
              "print(s.effective_enabled('R1_PART_TIME_JOBS'),s.effective_enabled('ratings'))")
    done = subprocess.run([sys.executable, '-c', script], cwd=backend, env=os.environ, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ['True', 'False']


# ---------------------------------------------------------------- real lock waits
@pytest.mark.parametrize('round_number', range(3))
def test_missing_row_creation_waits_on_the_code_lock_and_has_one_winner(client, identities, round_number, request):
    admin = identities('ADMIN'); code = 'R1_GENERAL_INTERNSHIPS'
    labels = ['flag-missing-' + str(uuid4()) + '-' + str(i) for i in range(2)]
    with labeled_requests(get_engine()) as call, ThreadPoolExecutor(max_workers=2) as pool:
        with get_engine().begin() as holder:
            hold(holder, code_lock_key(code))
            futures = [pool.submit(call, label, patch, client, admin, code, True, str(uuid4()), 0) for label in labels]
            observed = wait_for_requests(get_engine(), labels)
            assert len({row['pid'] for row in observed}) == 2
            request.node.user_properties.append(('actual_postgres_waits',json.dumps(observed,sort_keys=True)))
        responses = [future.result(timeout=30) for future in futures]
    assert sorted(r.status_code for r in responses) == [200, 412], [r.text for r in responses]
    assert (count('feature_flags'), count('feature_flag_origins'), count('feature_flag_change_events')) == (1, 1, 1)
    assert flag_admin_service.effective_enabled(code) is True


def test_same_actor_key_on_two_codes_serializes_before_any_authority_lock(client, identities, request):
    admin = identities('ADMIN'); key = str(uuid4()); codes = ('R1_PART_TIME_JOBS', 'R1_GENERAL_INTERNSHIPS')
    labels = ['flag-key-' + str(uuid4()) + '-' + str(i) for i in range(2)]
    with labeled_requests(get_engine()) as call, ThreadPoolExecutor(max_workers=2) as pool:
        with get_engine().begin() as holder:
            hold(holder, intent_lock_key(admin['user_id'], key))
            futures = [pool.submit(call, label, patch, client, admin, code, True, key, 0) for label, code in zip(labels, codes)]
            observed = wait_for_requests(get_engine(), labels, intent_only=True)
            pids = [row['pid'] for row in observed]
            with get_engine().connect() as watcher:   # blocked requests must not yet hold identity/grant locks
                held = watcher.execute(text("""SELECT c.relname FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
                    JOIN pg_namespace n ON n.oid=c.relnamespace WHERE l.pid=ANY(:pids) AND l.granted
                    AND n.nspname='flexbridge' AND c.relname IN ('users','sessions','platform_role_grants','role_catalog')"""),
                    {'pids': pids}).scalars().all()
            assert len(set(pids)) == 2 and held == []
            request.node.user_properties.append(('actual_postgres_waits',json.dumps(
                {'blocked_requests':observed,'identity_relations_held':held},sort_keys=True)))
        responses = [future.result(timeout=30) for future in futures]
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    assert next(r for r in responses if r.status_code == 409).json()['detail']['code'] == 'IDEMPOTENCY_KEY_REUSED'
    assert count('feature_flag_change_events') == 1 and count('audit_events') >= 1


@pytest.mark.parametrize('target', ['grant', 'session'])
def test_authority_that_expires_during_a_real_lock_wait_is_rechecked_at_decision(client, identities, target, request):
    admin = identities('ADMIN'); code = 'R1_ACADEMIC_INTERNSHIPS'; label = 'flag-expiry-' + str(uuid4())
    grants, sessions = table('platform_role_grants'), table('sessions')
    before = proof_state()
    with labeled_requests(get_engine()) as call, ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            hold(holder, code_lock_key(code))
            future = pool.submit(call, label, patch, client, admin, code, True, str(uuid4()), 0)
            observed=wait_for_requests(get_engine(), [label])
            request.node.user_properties.append(('actual_postgres_waits',json.dumps(observed,sort_keys=True)))
            with get_engine().begin() as trusted:  # real, time-based expiry while the request is already waiting
                if target == 'grant':
                    trusted.execute(text('UPDATE flexbridge.platform_role_grants SET expires_at=clock_timestamp()+interval \'2 seconds\' WHERE user_id=CAST(:u AS uuid)'), {'u': admin['user_id']})
                else:
                    trusted.execute(text('UPDATE flexbridge.sessions SET expires_at=clock_timestamp()+interval \'2 seconds\' WHERE id=CAST(:s AS uuid)'), {'s': admin['session_id']})
            deadline = monotonic() + 15
            table_name, key_column, key_value = (('platform_role_grants', 'user_id', admin['user_id']) if target == 'grant'
                                                 else ('sessions', 'id', admin['session_id']))
            while monotonic() < deadline:
                with get_engine().connect() as clock:
                    if clock.execute(text('SELECT clock_timestamp()>expires_at FROM flexbridge.' + table_name
                                          + ' WHERE ' + key_column + '=CAST(:v AS uuid)'), {'v': key_value}).scalar_one():
                        break
                sleep(.05)
            else:
                raise AssertionError('authority did not expire')
        response = future.result(timeout=30)
    assert response.status_code == 403, response.text
    assert response.json()['detail']['code'] == ('FORBIDDEN_ROLE' if target == 'grant' else 'MFA_REQUIRED')
    assert proof_state() == before


# ---------------------------------------------------------------- populated upgrades
def seed_legacy_flags(conn):
    author = insert_row(conn, 'users', display_name='Legacy flag author', status='ACTIVE', locale='uz',
                        timezone='Asia/Tashkent', auth_version=1)
    for code in LEGACY_CODES:
        conn.execute(table('feature_flags').insert().values(id=str(uuid4()), created_at=now(), updated_at=now(),
            code=code, enabled=True, rule_schema={'legacy': True, 'org_overrides': {'organization': True}},
            changed_by_id=author['id'], reason='Legacy unproved enablement'))
    return author


def flag_rows(conn):
    return [dict(r) for r in conn.execute(text('SELECT * FROM flexbridge.feature_flags ORDER BY code')).mappings()]


def test_populated_0016_upgrade_preserves_legacy_true_rows_without_certifying_them():
    with populated_database() as (engine, migrate):
        migrate('0016_academic_reviews')
        with engine.begin() as conn:
            seed_legacy_flags(conn); before = flag_rows(conn)
            tables_before = conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one()
        migrate('0017_feature_flag_administration')
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0017_feature_flag_administration'
            assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one() == tables_before + 2
            assert flag_rows(conn) == before and all(row['enabled'] for row in before)
            origins = {r['code']: dict(r) for r in conn.execute(text('SELECT * FROM flexbridge.feature_flag_origins')).mappings()}
            assert set(origins) == set(LEGACY_CODES) and all(o['origin'] == 'LEGACY_IMPORT' for o in origins.values())
            for row in before:
                snapshot = conn.execute(text('SELECT flexbridge.feature_flag_snapshot(f) FROM flexbridge.feature_flags f WHERE f.id=:id'), {'id': row['id']}).scalar_one()
                assert origins[row['code']]['initial_snapshot'] == snapshot and snapshot['changed_by_id'] == str(row['changed_by_id'])
            assert conn.execute(text('SELECT count(*) FROM flexbridge.feature_flag_change_events')).scalar_one() == 0
            assert all(flag_admin_service.effective_enabled(code, conn=conn) is False for code in LEGACY_CODES)
        with pytest.raises(IntegrityError, match='legacy set is closed'), engine.begin() as conn:
            conn.execute(text("INSERT INTO flexbridge.feature_flag_origins(flag_id,code,origin,initial_snapshot) "
                              "SELECT id,code,'LEGACY_IMPORT',flexbridge.feature_flag_snapshot(f) FROM flexbridge.feature_flags f LIMIT 1"))
        with pytest.raises(IntegrityError, match='unproved'), engine.begin() as conn:
            # Supply a structurally valid new state so the deferred missing-proof
            # guard is exercised instead of the earlier invalid-legacy-schema guard.
            conn.execute(text("UPDATE flexbridge.feature_flags SET enabled=false,rule_schema=CAST(:schema AS jsonb) "
                              "WHERE code='R1_GENERAL_INTERNSHIPS'"),{'schema':json.dumps(SERVER_SCHEMA)})
        with engine.begin() as conn:
            assert flag_rows(conn)==before
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text("UPDATE flexbridge.feature_flag_origins SET origin='PUBLIC'"))


def test_failed_0017_upgrade_rolls_back_capture_and_retains_0016_rows():
    with populated_database() as (engine, migrate):
        migrate('0016_academic_reviews')
        with engine.begin() as conn:
            seed_legacy_flags(conn); before = flag_rows(conn)
            conn.execute(text("""CREATE FUNCTION flexbridge.guard_feature_flag_change_event() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"""))
            definition = conn.execute(text("SELECT pg_get_functiondef('flexbridge.guard_feature_flag_change_event()'::regprocedure)")).scalar_one()
        failed = migrate('0017_feature_flag_administration', False)
        assert failed.returncode != 0 and 'guard_feature_flag_change_event' in failed.stderr
        with engine.begin() as conn:
            assert flag_rows(conn) == before
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0016_academic_reviews'
            assert conn.execute(text("SELECT to_regclass('flexbridge.feature_flag_origins')")).scalar_one() is None
            assert conn.execute(text("SELECT to_regclass('flexbridge.feature_flag_change_events')")).scalar_one() is None
            assert conn.execute(text("SELECT pg_get_functiondef('flexbridge.guard_feature_flag_change_event()'::regprocedure)")).scalar_one() == definition


def test_legacy_row_needs_a_real_admin_event_and_its_origin_stays_legacy(identities, monkeypatch):
    from app.db import storage
    with populated_database() as (engine, migrate):
        migrate('0016_academic_reviews')
        with engine.begin() as conn:
            seed_legacy_flags(conn)
        migrate('0017_feature_flag_administration')
        with monkeypatch.context() as patched:
            patched.setattr(storage, '_ENGINE', engine)
            admin = identities('ADMIN')
            with engine.begin() as conn:
                origin_before = [dict(r) for r in conn.execute(text('SELECT * FROM flexbridge.feature_flag_origins ORDER BY code')).mappings()]
            assert flag_admin_service.effective_enabled('R1_GENERAL_INTERNSHIPS') is False
            assert error_of(lambda: administer(admin, 'R1_GENERAL_INTERNSHIPS', True, str(uuid4()), 1)) == (412, 'STALE_FEATURE_FLAG_VERSION')
            assert error_of(lambda: administer(admin, 'R1_PAID_ORG_PLANS', False, str(uuid4()), 0)) == (409, 'FEATURE_FLAG_ALIAS_READ_ONLY')
            assert error_of(lambda: administer(admin, 'paid_checkout', True, str(uuid4()), 0)) == (409, 'FEATURE_PREREQUISITES_UNMET')
            receipt = administer(admin, 'R1_GENERAL_INTERNSHIPS', True, str(uuid4()), 0)
            assert receipt['version'] == 1 and flag_admin_service.effective_enabled('R1_GENERAL_INTERNSHIPS') is True
            off = administer(admin, 'paid_checkout', False, str(uuid4()), 0)
            assert off['effective_enabled'] is False and flag_admin_service.effective_enabled('R1_PAID_ORG_PLANS') is False
            with engine.begin() as conn:
                assert [dict(r) for r in conn.execute(text('SELECT * FROM flexbridge.feature_flag_origins ORDER BY code')).mappings()] == origin_before
                event = conn.execute(text("SELECT e.before_snapshot, o.initial_snapshot, e.actor_id FROM flexbridge.feature_flag_change_events e "
                    "JOIN flexbridge.feature_flag_origins o ON o.flag_id=e.flag_id WHERE e.code='R1_GENERAL_INTERNSHIPS'")).mappings().one()
                assert event['before_snapshot'] == event['initial_snapshot'] and str(event['actor_id']) == admin['user_id']
                assert flag_admin_service.effective_enabled('R1_GENERAL_INTERNSHIPS', conn=conn) is True
