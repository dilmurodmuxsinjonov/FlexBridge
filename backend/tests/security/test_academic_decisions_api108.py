"""Placement-wide nonofficial teacher academic conclusions (API-108 / CAP-024 / DB-054).

Trusted setup: formal school/staff/document/publication metadata and disposable upgrade
databases are explicitly labelled test fixtures, not public workflows or legal/provider
certification. Admission, diary submission, revision feedback, and session authentication
use real application flows.
"""
from __future__ import annotations

import json
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
from app.db.institution_scope import TASHKENT
from app.db.storage import get_engine, now, table, transaction
from app.services.academic_decisions import (
    academic_decision_service,
    basis_current,
    basis_for,
    digest_for,
    intent_lock_key,
)
from app.services.governance import GovernanceError
from app.services.placements import PlacementScopeError, get_row, insert_row
from test_academic_admission import pending_http, plan
from test_academic_migration import legacy_academic
from test_academic_reviews import body as review_body, ready, send as send_review
from test_academic_views import active_revision
from test_admission_lifecycle import terms_request
from test_candidate import cv_fixture
from test_institution_migration import populated_database
from test_internship_admission import post
from test_org_authority_transactions import wait_for_blocker
from test_organizations import actor
from test_regressions import count

REASON = 'Placement-wide advisory teacher academic conclusion over current diary.'


def teacher_actor(user: dict) -> ActorContext:
    return ActorContext(user['user_id'], user['session_id'], tuple(user.get('roles', ('TEACHER',))))


def get_context(client, f, assignment, *, user=None):
    target = user or f['teacher']
    return academic_decision_service.context(
        teacher_actor(target),
        f['placement']['id'],
        assignment['id'],
    )


def conclude_call(
    f,
    assignment,
    ctx,
    *,
    user=None,
    decision='ACADEMIC_REVIEW_COMPLETE',
    reason=REASON,
    idempotency_key=None,
    expected_basis_digest=None,
    terms_id=None,
    version=None,
):
    target = user or f['teacher']
    return academic_decision_service.conclude(
        actor=teacher_actor(target),
        placement_id=f['placement']['id'],
        assignment_id=assignment['id'],
        terms_id=terms_id or ctx['terms_id'],
        version=version if version is not None else ctx['version'],
        expected_basis_digest=expected_basis_digest or ctx['basis_digest'],
        decision=decision,
        reason=reason,
        idempotency_key=idempotency_key or str(uuid4()),
    )


def test_positive_and_negative_conclusions_full_diary_basis_and_stale_digest(client, identities, organization):
    f, assignment, draft1 = ready(client, identities, organization,
        placement_start_date=now().astimezone(TASHKENT).date()-timedelta(days=1))
    p = plan(client, f)

    # Log 1 is submitted but unreviewed -> positive conclusion denied (409 ACADEMIC_REVIEWS_PENDING).
    ctx0 = get_context(client, f, assignment)
    assert ctx0['log_count'] == 1 and ctx0['submitted_count'] == 1
    assert ctx0['reviewed_count'] == 0 and ctx0['pending_count'] == 1
    assert ctx0['academic_review_complete'] is False and ctx0['advisory_only'] is True
    assert ctx0['current_conclusion'] is None and ctx0['new_conclusion_allowed'] is True
    for forbidden_key in ('summary', 'tasks', 'files', 'legal_basis', 'session_id', 'teacher_grant_id'):
        assert forbidden_key not in json.dumps(ctx0)

    with pytest.raises(PlacementScopeError) as pending_exc:
        conclude_call(f, assignment, ctx0, decision='ACADEMIC_REVIEW_COMPLETE')
    assert pending_exc.value.status_code == 409
    assert pending_exc.value.code == 'ACADEMIC_REVIEWS_PENDING'

    # Review Log 1 as REVIEWED, then add Log 2 as DRAFT -> ALL-LOG check denies positive conclusion
    # and invalidates the earlier basis digest (412 ACADEMIC_BASIS_CHANGED).
    assert send_review(client, f, draft1, review_body(assignment)).status_code == 201
    ctx_one_reviewed = get_context(client, f, assignment)
    assert ctx_one_reviewed['academic_review_complete'] is True

    second_date = (f['placement']['start_date'] + timedelta(days=1)).isoformat()
    draft2_resp = client.put(
        '/api/v1/placements/' + f['placement']['id'] + '/logs/' + second_date,
        headers=f['candidate']['headers'],
        json={'day_type': 'WORKED', 'summary_text': 'Second day draft entry', 'total_minutes': 120},
    )
    assert draft2_resp.status_code == 200, draft2_resp.text
    draft2 = draft2_resp.json()

    # Old digest from before draft2 is now stale (412 ACADEMIC_BASIS_CHANGED).
    with pytest.raises(PlacementScopeError) as stale_exc:
        conclude_call(f, assignment, ctx_one_reviewed, decision='ACADEMIC_REVIEW_COMPLETE')
    assert stale_exc.value.status_code == 412
    assert stale_exc.value.code == 'ACADEMIC_BASIS_CHANGED'

    # Fresh context reflects 2 logs (1 reviewed, 1 pending draft) -> positive denied, negative allowed.
    ctx_with_draft = get_context(client, f, assignment)
    assert ctx_with_draft['log_count'] == 2
    assert ctx_with_draft['submitted_count'] == 1
    assert ctx_with_draft['reviewed_count'] == 1
    assert ctx_with_draft['needs_revision_count'] == 0
    assert ctx_with_draft['pending_count'] == 1
    assert ctx_with_draft['academic_review_complete'] is False

    with pytest.raises(PlacementScopeError) as pending_exc2:
        conclude_call(f, assignment, ctx_with_draft, decision='ACADEMIC_REVIEW_COMPLETE')
    assert pending_exc2.value.status_code == 409
    assert pending_exc2.value.code == 'ACADEMIC_REVIEWS_PENDING'

    neg_key = str(uuid4())
    neg_receipt = conclude_call(
        f,
        assignment,
        ctx_with_draft,
        decision='ACADEMIC_REVISION_REQUIRED',
        reason='  Second daily log is still a draft and needs submission.  ',
        idempotency_key=neg_key,
    )
    assert neg_receipt['side'] == 'TEACHER'
    assert neg_receipt['decision'] == 'ACADEMIC_REVISION_REQUIRED'
    assert neg_receipt['reason'] == 'Second daily log is still a draft and needs submission.'
    assert neg_receipt['placement_id'] == f['placement']['id']
    assert neg_receipt['terms_id'] == p['terms_id']

    # Same key + same intent replays exact canonical DB-054 receipt; changed intent or new key on same basis fails 409.
    assert conclude_call(
        f,
        assignment,
        ctx_with_draft,
        decision='ACADEMIC_REVISION_REQUIRED',
        reason='Second daily log is still a draft and needs submission.',
        idempotency_key=neg_key,
    ) == neg_receipt

    with pytest.raises(PlacementScopeError) as reused_exc:
        conclude_call(
            f,
            assignment,
            ctx_with_draft,
            decision='ACADEMIC_REVISION_REQUIRED',
            reason='Different reason with same key',
            idempotency_key=neg_key,
        )
    assert reused_exc.value.status_code == 409
    assert reused_exc.value.code == 'IDEMPOTENCY_KEY_REUSED'

    with pytest.raises(PlacementScopeError) as dup_exc:
        conclude_call(
            f,
            assignment,
            ctx_with_draft,
            decision='ACADEMIC_REVISION_REQUIRED',
            reason='Duplicate conclusion on unchanged basis',
            idempotency_key=str(uuid4()),
        )
    assert dup_exc.value.status_code == 409
    assert dup_exc.value.code == 'ACADEMIC_CONCLUSION_ALREADY_RECORDED'

    # Submit and review Log 2 as REVIEWED -> basis advances and positive conclusion succeeds.
    post(client, '/api/v1/logs/' + draft2['id'] + '/submit', f['candidate'], {}, 200)
    draft2_submitted = client.get('/api/v1/placements/' + f['placement']['id'] + '/plan', headers=f['candidate']['headers'])
    assert draft2_submitted.status_code == 200
    with transaction() as conn:
        rev2_id = get_row(conn, 'daily_logs', draft2['id'])['current_revision_id']
    assert send_review(
        client,
        f,
        {'id': draft2['id'], 'current_revision_id': rev2_id},
        review_body(assignment),
    ).status_code == 201

    ctx_complete = get_context(client, f, assignment)
    assert ctx_complete['log_count'] == 2
    assert ctx_complete['submitted_count'] == 2
    assert ctx_complete['reviewed_count'] == 2
    assert ctx_complete['needs_revision_count'] == 0
    assert ctx_complete['pending_count'] == 0
    assert ctx_complete['academic_review_complete'] is True
    assert ctx_complete['current_conclusion'] is None

    pos_key = str(uuid4())
    pos_receipt = conclude_call(
        f,
        assignment,
        ctx_complete,
        decision='ACADEMIC_REVIEW_COMPLETE',
        reason=REASON,
        idempotency_key=pos_key,
    )
    assert pos_receipt['decision'] == 'ACADEMIC_REVIEW_COMPLETE'
    assert get_context(client, f, assignment)['current_conclusion'] == pos_receipt
    with transaction() as conn:
        assert basis_current(conn, pos_receipt['id']) is True
        assert basis_current(conn, neg_receipt['id']) is False
        assert get_row(conn, 'placements', f['placement']['id'])['status'] == 'ACTIVE'


def test_replay_survives_pointer_and_cancellation_and_logout_keeps_basis_current(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization)
    assert send_review(client, f, draft, review_body(assignment)).status_code == 201
    ctx = get_context(client, f, assignment)
    key = str(uuid4())
    receipt = conclude_call(f, assignment, ctx, decision='ACADEMIC_REVIEW_COMPLETE', idempotency_key=key)

    # Logout of a separate session or checking basis_current does not depend on old session staying open.
    # First advance pointer with a new draft and cancel placement: exact prior key still replays.
    p = plan(client, f)
    with transaction() as conn:
        replacement = insert_row(
            conn,
            'log_revisions',
            daily_log_id=draft['id'],
            revision=2,
            terms_id=p['terms_id'],
            author_id=f['candidate']['user_id'],
            day_type='WORKED',
            summary='Later draft pointer change',
            total_minutes=0,
            status='DRAFT',
            idempotency_key=str(uuid4()),
        )
        conn.execute(
            table('daily_logs')
            .update()
            .where(table('daily_logs').c.id == draft['id'])
            .values(current_revision_id=replacement['id'])
        )
        assert basis_current(conn, receipt['id']) is False

    post(
        client,
        '/api/v1/placements/' + f['placement']['id'] + '/host-decisions',
        f['owner'],
        {**terms_request(p), 'action': 'CANCEL'},
        200,
    )
    assert get_context(client, f, assignment)['new_conclusion_allowed'] is False
    assert conclude_call(f, assignment, ctx, decision='ACADEMIC_REVIEW_COMPLETE', idempotency_key=key) == receipt
    with pytest.raises(PlacementScopeError) as inactive_exc:
        conclude_call(f, assignment, get_context(client, f, assignment), decision='ACADEMIC_REVISION_REQUIRED')
    assert inactive_exc.value.status_code == 403
    assert inactive_exc.value.code == 'ACTIVE_ACADEMIC_PLACEMENT_REQUIRED'


@pytest.mark.parametrize('who', ['candidate', 'coord', 'owner', 'outsider'])
def test_foreign_and_self_actors_are_denied(client, identities, organization, who):
    f, assignment, draft = ready(client, identities, organization)
    assert send_review(client, f, draft, review_body(assignment)).status_code == 201
    ctx = get_context(client, f, assignment)
    user = identities() if who == 'outsider' else f[who]
    with pytest.raises((PlacementScopeError, GovernanceError)) as exc_info:
        get_context(client, f, assignment, user=user)
    assert exc_info.value.status_code == 403
    with pytest.raises((PlacementScopeError, GovernanceError)) as post_exc:
        conclude_call(f, assignment, ctx, user=user)
    assert post_exc.value.status_code == 403


def test_actor_key_lock_precedes_parent_locks_and_mfa_or_revocation_after_wait_is_enforced(
    client, identities, organization, record_testsuite_property
):
    first = pending_http(client, identities, organization)
    # Trusted fixture: second verified host and second institution with same teacher.
    with transaction() as conn:
        host = insert_row(
            conn,
            'organizations',
            tax_id=str(uuid4()),
            legal_name='Second host for decision intent lock',
            public_name='Second host for decision intent lock',
            region='Tashkent',
            status='VERIFIED',
        )
        case = insert_row(
            conn,
            'verification_cases',
            requester_id=first['owner']['user_id'],
            organization_id=host['id'],
            kind='INTERNSHIP_HOST',
            status='APPROVED',
            current_revision=1,
            assigned_reviewer_id=first['coord']['user_id'],
            due_at=now(),
            decided_at=now(),
        )
        insert_row(
            conn,
            'organization_capabilities',
            organization_id=host['id'],
            capability='INTERNSHIP_HOST',
            status='ACTIVE',
            approved_case_id=case['id'],
        )
    second = pending_http(client, identities, host['id'])
    document = cv_fixture(first['teacher'])
    with transaction() as conn:
        member = insert_row(
            conn,
            'institution_memberships',
            institution_id=second['inst']['id'],
            user_id=first['teacher']['user_id'],
            status='ACTIVE',
            accepted_at=now(),
        )
        appointment = insert_row(
            conn,
            'institution_appointments',
            institution_id=second['inst']['id'],
            user_id=first['teacher']['user_id'],
            document_file_id=document['id'],
            status='ACTIVE',
            valid_from=now().astimezone(TASHKENT).date(),
            accepted_at=now(),
        )
        grant = insert_row(
            conn,
            'institution_role_grants',
            membership_id=member['id'],
            role_id=second['teacher_grant']['role_id'],
            appointment_id=appointment['id'],
        )
    second.update(teacher=first['teacher'], teacher_member=member, teacher_appointment=appointment, teacher_grant=grant)

    prepared = []
    shared_key = str(uuid4())
    for f in (first, second):
        assignment, draft = active_revision(client, f)
        post(client, '/api/v1/logs/' + draft['id'] + '/submit', f['candidate'], {}, 200)
        assert send_review(client, f, draft, review_body(assignment)).status_code == 201
        ctx = get_context(client, f, assignment)
        prepared.append((f, assignment, ctx))

    labels = ['decision-intent-' + str(uuid4()) + '-' + str(i) for i in range(2)]

    def run_conclude(f, assignment, ctx):
        try:
            res = conclude_call(f, assignment, ctx, idempotency_key=shared_key)
            return 201, res
        except (PlacementScopeError, GovernanceError) as exc:
            return exc.status_code, exc.code

    with labeled_requests(get_engine()) as call, ThreadPoolExecutor(max_workers=2) as pool:
        with get_engine().begin() as holder:
            holder.execute(
                text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                {'key': intent_lock_key(first['teacher']['user_id'], shared_key)},
            )
            futures = [pool.submit(call, label, run_conclude, *item) for label, item in zip(labels, prepared)]
            observed = wait_for_requests(get_engine(), labels, intent_only=True)
            pids = [row['pid'] for row in observed]
            with get_engine().connect() as watcher:
                held = watcher.execute(
                    text(
                        """SELECT c.relname FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
                        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE l.pid=ANY(:pids) AND l.granted
                        AND n.nspname='flexbridge' AND c.relname IN ('institutions','organizations','placements','users','sessions')"""
                    ),
                    {'pids': pids},
                ).scalars().all()
            assert len(set(pids)) == 2 and held == []
            record_testsuite_property(
                'academic_decision_actor_key_wait',
                json.dumps({'observed': observed, 'held_relations': held}, sort_keys=True),
            )
        results = [future.result(timeout=30) for future in futures]
    assert sorted(r[0] for r in results) == [201, 409], results
    assert next(r[1] for r in results if r[0] == 409) == 'IDEMPOTENCY_KEY_REUSED'

    # Parent lock wait: if sensitive role COORDINATOR is granted while waiting, PASSWORD session is rejected with MFA_REQUIRED.
    f2, assignment2, ctx2 = prepared[1]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(
                select(table('institutions'))
                .where(table('institutions').c.id == f2['inst']['id'])
                .with_for_update()
            )
            pid = holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending = pool.submit(run_conclude, f2, assignment2, ctx2)
            wait_for_blocker(pid)
            # Trusted fixture mutation: grant sensitive COORDINATOR role while teacher waits on parent institution lock.
            with transaction() as conn:
                coord_role_id = conn.execute(
                    select(table('role_catalog').c.id).where(
                        table('role_catalog').c.code == 'COORDINATOR',
                        table('role_catalog').c.scope_kind == 'INSTITUTION',
                    )
                ).scalar_one()
                insert_row(
                    conn,
                    'institution_role_grants',
                    membership_id=f2['teacher_member']['id'],
                    role_id=coord_role_id,
                    appointment_id=f2['teacher_appointment']['id'],
                )
        status, code = pending.result(timeout=30)
    assert status == 403 and code == 'MFA_REQUIRED'


def test_audit_stamp_savepoint_rollback_timezone_and_isolation_controls(client, identities, organization, monkeypatch):
    f, assignment, draft = ready(client, identities, organization)
    assert send_review(client, f, draft, review_body(assignment)).status_code == 201
    ctx = get_context(client, f, assignment)

    # 1. Non-READ COMMITTED isolation fails closed with 503 ACADEMIC_DECISION_ISOLATION_UNSAFE.
    with pytest.raises(PlacementScopeError) as iso_exc:
        with transaction() as conn:
            conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'))
            get_context(client, f, assignment)
    assert iso_exc.value.status_code == 503
    assert iso_exc.value.code == 'ACADEMIC_DECISION_ISOLATION_UNSAFE'

    # 2. Failure after audit insert rolls back decision, proof, and audit event.
    before_decisions = count('placement_decisions')
    before_proofs = count('academic_decision_proofs')
    before_audits = count('audit_events')
    original_append = academic_decision_service.audit.append_audit_event

    def fail_after_audit(**kwargs):
        original_append(**kwargs)
        raise RuntimeError('Injected failure after academic decision audit')

    with monkeypatch.context() as patch:
        patch.setattr(academic_decision_service.audit, 'append_audit_event', fail_after_audit)
        with pytest.raises(RuntimeError, match='Injected failure after academic decision audit'):
            conclude_call(f, assignment, ctx)
    assert count('placement_decisions') == before_decisions
    assert count('academic_decision_proofs') == before_proofs
    assert count('audit_events') == before_audits

    # 3. DB overwrites caller-supplied _academic_decision_top_xid while leaving unrelated actions untouched.
    with transaction() as conn:
        with conn.begin_nested():
            forged = AppendOnlyAuditStore().append_audit_event(
                actor_id=f['teacher']['user_id'],
                action='ACADEMIC_DECISION_RECORDED',
                entity_type='placement_decision',
                entity_id=str(uuid4()),
                metadata={'_academic_decision_top_xid': 'caller-forged-xid', 'keep': 'yes'},
            )
            unrelated = AppendOnlyAuditStore().append_audit_event(
                actor_id=f['teacher']['user_id'],
                action='UNRELATED_ACTION',
                entity_type='test',
                entity_id=str(uuid4()),
                metadata={'_academic_decision_top_xid': 'caller-untouched'},
            )
        top_xid = conn.execute(text('SELECT CAST(pg_current_xact_id() AS text)')).scalar_one()
        stamps = {
            r['id']: r['scope_snapshot']
            for r in conn.execute(
                select(table('audit_events')).where(table('audit_events').c.id.in_([forged['id'], unrelated['id']]))
            ).mappings()
        }
        assert stamps[forged['id']] == {'_academic_decision_top_xid': top_xid, 'keep': 'yes'}
        assert stamps[unrelated['id']] == {'_academic_decision_top_xid': 'caller-untouched'}

    # 4. Savepoint execution and session TimeZone independence.
    with transaction() as conn:
        conn.execute(text("SET LOCAL TimeZone TO 'Pacific/Kiritimati'"))
        with conn.begin_nested():
            receipt = conclude_call(f, assignment, ctx, decision='ACADEMIC_REVIEW_COMPLETE')
    seen_basis = set()
    seen_snap = set()
    for zone in ('Pacific/Kiritimati', 'America/Los_Angeles', 'UTC'):
        with get_engine().begin() as conn:
            conn.execute(text("SET LOCAL TimeZone TO '" + zone + "'"))
            b = basis_for(conn, f['placement']['id'], assignment['id'])
            seen_basis.add(digest_for(conn, b))
            snap = conn.execute(
                text('SELECT flexbridge.placement_decision_snapshot(d) FROM flexbridge.placement_decisions d WHERE d.id=CAST(:id AS uuid)'),
                {'id': receipt['id']},
            ).scalar_one()
            seen_snap.add(json.dumps(snap, sort_keys=True))
            assert basis_current(conn, receipt['id']) is True
    assert len(seen_basis) == 1 and len(seen_snap) == 1


def test_populated_0017_to_0018_upgrade_rollback_and_host_decision_compatibility():
    with populated_database() as (engine, migrate):
        # Seed imported files/relationships at their genuine legacy schema;
        # later provenance guards must remain enabled for new0017 writes.
        with engine.begin() as conn:
            f = legacy_academic(conn)
        migrate('0017_feature_flag_administration')
        with engine.begin() as conn:
            legacy_host = insert_row(
                conn,
                'placement_decisions',
                placement_id=f['placement_id'],
                actor_id=f['teacher_id'],
                side='HOST',
                decision='ACTIVATE',
                terms_id=f['terms_id'],
                reason=None,
                decided_at=now(),
            )
            legacy_teacher = insert_row(
                conn,
                'placement_decisions',
                placement_id=f['placement_id'],
                actor_id=f['teacher_id'],
                side='TEACHER',
                decision='LEGACY_HISTORICAL_CONCLUSION',
                terms_id=f['terms_id'],
                reason='Imported historical teacher note',
                decided_at=now(),
            )
            before_rows = [
                dict(r)
                for r in conn.execute(
                    select(table('placement_decisions')).order_by(table('placement_decisions').c.id)
                ).mappings()
            ]
            # Inject collision to verify transactional rollback of failed 0018 upgrade.
            conn.execute(
                text(
                    """CREATE FUNCTION flexbridge.guard_academic_decision_proof() RETURNS trigger
                    LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"""
                )
            )
        failed = migrate('head', False)
        assert failed.returncode != 0 and 'guard_academic_decision_proof' in failed.stderr
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0017_feature_flag_administration'
            assert conn.execute(text("SELECT to_regclass('flexbridge.academic_decision_proofs')")).scalar_one() is None
            conn.execute(text('DROP FUNCTION flexbridge.guard_academic_decision_proof()'))

        migrate('head')
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0019_placement_completions'
            after_rows = [
                dict(r)
                for r in conn.execute(
                    select(table('placement_decisions')).order_by(table('placement_decisions').c.id)
                ).mappings()
            ]
            assert after_rows == before_rows
            proofs = {
                str(r['decision_id']): dict(r)
                for r in conn.execute(text('SELECT * FROM flexbridge.academic_decision_proofs')).mappings()
            }
            assert set(proofs) == {legacy_host['id'], legacy_teacher['id']}
            for row_id, proof in proofs.items():
                assert proof['origin'] == 'LEGACY_IMPORT'
                assert all(
                    proof[k] is None
                    for k in proof
                    if k not in ('decision_id', 'created_at', 'origin', 'initial_snapshot')
                )
                assert basis_current(conn, row_id) is False

            # Unrelated HOST placement_decisions remain insertable without academic_decision_proofs.
            new_host = insert_row(
                conn,
                'placement_decisions',
                placement_id=f['placement_id'],
                actor_id=f['teacher_id'],
                side='HOST',
                decision='CANCEL',
                terms_id=f['terms_id'],
                reason=None,
                decided_at=now(),
            )
            assert new_host['side'] == 'HOST'

        # Non-TEACHER cannot use new teacher vocabulary; unproved TEACHER row cannot commit; LEGACY_IMPORT is closed.
        with pytest.raises(IntegrityError, match='requires TEACHER side'), engine.begin() as conn:
            insert_row(
                conn,
                'placement_decisions',
                placement_id=f['placement_id'],
                actor_id=f['teacher_id'],
                side='HOST',
                decision='ACADEMIC_REVIEW_COMPLETE',
                terms_id=f['terms_id'],
                reason='Invalid side',
                decided_at=now(),
            )
        with pytest.raises(IntegrityError, match='requires immutable public proof'), engine.begin() as conn:
            insert_row(
                conn,
                'placement_decisions',
                placement_id=f['placement_id'],
                actor_id=f['teacher_id'],
                side='TEACHER',
                decision='ACADEMIC_REVISION_REQUIRED',
                terms_id=f['terms_id'],
                reason='Unproved direct SQL row',
                decided_at=now(),
            )
        with pytest.raises(IntegrityError, match='legacy set is closed'), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO flexbridge.academic_decision_proofs(decision_id,origin,initial_snapshot) "
                    "SELECT id,'LEGACY_IMPORT',flexbridge.placement_decision_snapshot(d) "
                    "FROM flexbridge.placement_decisions d WHERE d.id=CAST(:id AS uuid)"
                ),
                {'id': new_host['id']},
            )
