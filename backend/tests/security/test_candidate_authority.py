"""Next package tests: actual HTTP/session/SQL ordering, trusted skill/CV fixtures."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select, text
from app.api.dependencies import ActorContext
from app.db.storage import table, transaction, get_engine
from app.services import candidates, availability
from app.services.auth import AuthError
from app.services.governance import GovernanceError
from app.services.schedule import local_today
from test_candidate import cv_fixture, skill_fixture
from test_files_authority_expanded import change_security
from test_org_authority_transactions import wait_for_blocker

KINDS = ('profile', 'skills', 'cv', 'cv_unlink', 'rules', 'exceptions', 'profile_read', 'schedule_read', 'legacy_rule', 'legacy_exception')
WRITES = tuple(kind for kind in KINDS if not kind.endswith('_read'))


def operation(kind, client, identities, owner=None):
    owner = owner or identities()
    today = local_today().isoformat()
    document = None
    if kind == 'profile':
        request = lambda: client.patch('/api/v1/me/candidate', headers=owner['headers'], json={'headline': 'Current authorized headline'})
    elif kind == 'skills':
        skill = skill_fixture()
        request = lambda: client.patch('/api/v1/me/candidate/skills', headers=owner['headers'], json={'skills': [{'skill_id': skill['id'], 'level': 'BASIC'}]})
    elif kind in ('cv','cv_unlink'):
        document = cv_fixture(owner)
        if kind=='cv_unlink':
            initial=client.post('/api/v1/me/candidate/cv',headers=owner['headers'],json={'file_id':document['id']})
            assert initial.status_code==200
        request = lambda: client.post('/api/v1/me/candidate/cv', headers=owner['headers'], json={'file_id': document['id'] if kind=='cv' else None})
    elif kind == 'rules':
        request = lambda: client.put('/api/v1/me/availability', headers=owner['headers'], json={'rules': [{
            'weekday': 1, 'start_minute': 540, 'end_minute': 600, 'valid_from': today}]})
    elif kind == 'exceptions':
        request = lambda: client.put('/api/v1/me/availability/exceptions', headers=owner['headers'], json={
            'from_date': today, 'to_date': today, 'exceptions': [{'local_date': today, 'kind': 'AVAILABLE', 'start_minute': 540, 'end_minute': 600}]})
    elif kind == 'profile_read':
        request = lambda: client.get('/api/v1/me/candidate', headers=owner['headers'])
    elif kind == 'schedule_read':
        request = lambda: client.get('/api/v1/me/availability', headers=owner['headers'])
    elif kind == 'legacy_rule':
        request = lambda: client.post('/api/v1/candidates/' + owner['candidate_id'] + '/availability-rules', headers=owner['headers'],
            json={'weekday': 1, 'start_minute': 540, 'end_minute': 600})
    else:
        request = lambda: client.post('/api/v1/candidates/' + owner['candidate_id'] + '/availability-exceptions', headers=owner['headers'],
            json={'exception_date': today, 'kind': 'AVAILABLE_EXTRA', 'start_minute': 540, 'end_minute': 600})
    module = candidates if kind in ('profile', 'skills', 'cv', 'cv_unlink', 'profile_read') else availability
    return module, owner, request, document


def snapshot():
    with transaction() as conn:
        result = {name: [tuple(row) for row in conn.execute(select(table(name)).order_by(table(name).c.id))]
            for name in ('candidate_profiles', 'candidate_skills', 'availability_rules', 'availability_exceptions')}
        audits = table('audit_events')
        result['candidate_audit'] = [tuple(row) for row in conn.execute(select(audits).where(
            audits.c.action.like('CANDIDATE_%')).order_by(audits.c.id))]
        return result


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('change', ('logout', 'expiry', 'auth_version', 'suspended', 'sensitive_role'))
def test_completed_security_change_while_profile_is_held_denies_request(client, identities, kind, change):
    _, owner, request, _ = operation(kind, client, identities)
    before = snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            profiles = table('candidate_profiles')
            blocker.execute(select(profiles).where(profiles.c.id == owner['candidate_id']).with_for_update())
            pid = blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending = pool.submit(request)
            wait_for_blocker(pid)
            change_security(change, client, owner)
        response = pending.result(timeout=30)
    assert response.status_code in (401, 403), (kind, change, response.status_code)
    assert snapshot() == before


@pytest.mark.parametrize('change', ('logout', 'expiry', 'auth_version', 'suspended', 'sensitive_role'))
def test_cv_authority_follows_material_file_wait(client, identities, change):
    _, owner, request, document = operation('cv', client, identities)
    before = snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            files = table('files')
            blocker.execute(select(files).where(files.c.id == document['id']).with_for_update())
            pid = blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending = pool.submit(request)
            wait_for_blocker(pid)
            change_security(change, client, owner)
        response = pending.result(timeout=30)
    assert response.status_code in (401, 403)
    assert snapshot() == before


@pytest.mark.parametrize('kind', KINDS)
def test_authorized_commit_precedes_actual_waiting_logout(client, identities, monkeypatch, kind):
    module, owner, request, _ = operation(kind, client, identities)
    original = module.account_authority
    held, release = Event(), Event()
    pids = []
    def guard(conn, actor, **kwargs):
        original(conn, actor, **kwargs)
        if actor.user_id == owner['user_id']:
            pids.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set()
            assert release.wait(30)
    monkeypatch.setattr(module, 'account_authority', guard)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(request)
        try:
            assert held.wait(30)
            logout = pool.submit(lambda: client.delete('/api/v1/me/sessions/' + owner['session_id'], headers=owner['headers']))
            wait_for_blocker(pids[0])
            assert not logout.done()
        finally:
            release.set()
        result, revoked = pending.result(timeout=30), logout.result(timeout=30)
    assert result.status_code == (201 if kind.startswith('legacy_') else 200)
    assert revoked.status_code == 200
    assert client.get('/api/v1/auth/me', headers=owner['headers']).status_code == 401


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('privileged', (False, True))
def test_current_password_or_sensitive_mfa_actor_retains_scope(client, identities, kind, privileged):
    owner = identities('MODERATOR') if privileged else identities()
    _, owner, request, _ = operation(kind, client, identities, owner=owner)
    response = request()
    assert response.status_code == (201 if kind.startswith('legacy_') else 200), response.text
    if kind == 'legacy_exception':
        assert response.json()['kind'] == 'AVAILABLE'


def direct(kind, actor, owner, document):
    if kind == 'profile':
        return candidates.candidate_service.update_profile(actor, {'headline': 'Attempted direct update'})
    if kind == 'profile_read':
        return candidates.candidate_service.get_profile(actor)
    if kind == 'skills':
        return candidates.candidate_service.update_skills(actor, [], [])
    if kind in ('cv','cv_unlink'):
        return candidates.candidate_service.link_cv(actor, document['id'] if kind=='cv' else None)
    if kind == 'rules':
        return availability.availability_service.replace_rules(actor, [])
    if kind == 'exceptions':
        return availability.availability_service.replace_exceptions(actor, local_today(), local_today(), [])
    if kind == 'schedule_read':
        return availability.availability_service.get_my_schedule(actor)
    if kind == 'legacy_rule':
        return availability.availability_service.add_availability_rule(actor=actor, candidate_id=owner['candidate_id'],
            weekday=1, start_minute=540, end_minute=600)
    return availability.availability_service.add_availability_exception(actor=actor, candidate_id=owner['candidate_id'],
        exception_date=local_today().isoformat(), start_minute=540, end_minute=600)


@pytest.mark.parametrize('kind', KINDS)
def test_other_sessions_cannot_be_attached_to_claimed_user(client, identities, kind):
    _, owner, _, document = operation(kind, client, identities)
    other = identities()
    forged = ActorContext(owner['user_id'], other['session_id'], ())
    before = snapshot()
    with pytest.raises((AuthError, GovernanceError)) as denied:
        direct(kind, forged, owner, document)
    assert denied.value.status_code in (401, 403)
    assert snapshot() == before


@pytest.mark.parametrize('kind', ('legacy_rule', 'legacy_exception'))
def test_legacy_service_checks_the_actual_actors_candidate_id(client, identities, kind):
    _, owner, _, document = operation(kind, client, identities)
    other = identities()
    actual = ActorContext(other['user_id'], other['session_id'], ())
    before = snapshot()
    with pytest.raises((AuthError, GovernanceError, availability.AvailabilityConstraintError)) as denied:
        direct(kind, actual, owner, document)
    assert denied.value.status_code == 403
    assert snapshot() == before


@pytest.mark.parametrize('kind', WRITES)
def test_audit_failure_rolls_back_candidate_material_and_legacy_writes(client, identities, monkeypatch, kind):
    _, _, request, _ = operation(kind, client, identities)
    before = snapshot()
    def fail(**kwargs):
        raise RuntimeError('Intentional audit failure')
    monkeypatch.setattr(candidates.audit, 'append_audit_event', fail)
    response = request()
    assert response.status_code == 503
    assert snapshot() == before


@pytest.mark.parametrize('writer_kind', ('legacy_rule', 'legacy_exception'))
def test_private_schedule_read_serializes_legacy_material_writers(client, identities, monkeypatch, writer_kind):
    _, owner, writer, _ = operation(writer_kind, client, identities)
    original = availability.load_snapshot
    held, release = Event(), Event()
    pids = []
    def pause(candidate_id, *args, **kwargs):
        value = original(candidate_id, *args, **kwargs)
        if candidate_id == owner['candidate_id'] and not held.is_set():
            with transaction() as conn:
                pids.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set()
            assert release.wait(30)
        return value
    monkeypatch.setattr(availability, 'load_snapshot', pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reading = pool.submit(lambda: client.get('/api/v1/me/availability?days=1', headers=owner['headers']))
        try:
            assert held.wait(30)
            writing = pool.submit(writer)
            wait_for_blocker(pids[0])
            assert not writing.done()
        finally:
            release.set()
        observed, updated = reading.result(timeout=30), writing.result(timeout=30)
    assert observed.status_code == 200 and updated.status_code == 201
    assert observed.json()['rules'] == [] and observed.json()['exceptions'] == []
    latest = client.get('/api/v1/me/availability?days=1', headers=owner['headers'])
    assert latest.status_code == 200
    assert len(latest.json()['rules' if writer_kind == 'legacy_rule' else 'exceptions']) == 1


@pytest.mark.parametrize('kind', ('profile_read', 'schedule_read'))
def test_human_private_read_refuses_a_frozen_outer_snapshot(client, identities, kind):
    from app.db.storage import read_snapshot
    _, owner, _, document = operation(kind, client, identities)
    actor = ActorContext(owner['user_id'], owner['session_id'], ())
    before = snapshot()
    with read_snapshot() as frozen:
        frozen.execute(text('SELECT 1'))
        assert frozen.get_isolation_level() == 'REPEATABLE READ'
        with pytest.raises(RuntimeError, match='READ COMMITTED'):
            direct(kind, actor, owner, document)
    assert snapshot() == before



def test_reviewed_teacher_password_session_retains_candidate_self_service(client, identities):
    from test_institution_onboarding import active_coordinator, staff_claim, accept, claim, decide
    institution = active_coordinator(client, identities)
    teacher = identities()
    request, contact, _ = staff_claim(client, institution, teacher)
    assert accept(client, institution, request['id'], user=teacher, contact_id=contact['id']).status_code == 200
    assert claim(client, institution['moderator'], request['case_id']).status_code == 200
    assert decide(client, institution['moderator'], request['case_id']).status_code == 200
    me = client.get('/api/v1/auth/me', headers=teacher['headers'])
    assert me.status_code == 200 and 'TEACHER' in me.json()['roles'] and 'COORDINATOR' not in me.json()['roles']
    with transaction() as conn:
        assert conn.execute(select(table('sessions').c.assurance).where(table('sessions').c.id == teacher['session_id'])).scalar_one() == 'PASSWORD'
    for kind in KINDS:
        # Both legacy inserts must use a valid nonconflicting schedule fixture.
        if kind == 'legacy_rule':
            assert client.put('/api/v1/me/availability',headers=teacher['headers'],json={'rules':[]}).status_code == 200
        elif kind == 'legacy_exception':
            today=local_today().isoformat()
            assert client.put('/api/v1/me/availability/exceptions',headers=teacher['headers'],json={
                'from_date':today,'to_date':today,'exceptions':[]}).status_code == 200
        _, _, request, _ = operation(kind,client,identities,owner=teacher)
        response=request()
        assert response.status_code == (201 if kind.startswith('legacy_') else 200),(kind,response.status_code,response.text)
