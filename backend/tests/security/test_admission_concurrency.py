"""HTTP revocation/acceptance interleavings and real PostgreSQL lock observations."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select, text

from app.db.storage import table, transaction
from app.services.placement_admission import admission_service
from test_admission_lifecycle import planned, terms_request, accept_sides, saved
from test_internship_admission import post
from test_admission_current_actor import admission_snapshot
from test_org_authority_transactions import wait_for_blocker


def member_for(user, org):
    m=table('org_memberships')
    with transaction() as conn:
        return conn.execute(select(m.c.id).where(m.c.user_id==user['user_id'],m.c.organization_id==org)).scalar_one()


def revoke(client, host, org, member):
    return client.post('/api/v1/organizations/'+org+'/memberships/'+member+'/revoke',headers=host['headers'],
                       json={'reason':'Current scoped authority is explicitly withdrawn.'})


@pytest.mark.parametrize('side',['MENTOR','HOST_COORDINATOR'])
def test_completed_public_membership_revocation_after_preflight_denies_new_personal_action(
    client,identities,organization,monkeypatch,side):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    base='/api/v1/placements/'+p['id']
    if side=='MENTOR':
        acting=mentor
        request=lambda:client.post(base+'/assignments/'+assignment['id']+'/accept',headers=acting['headers'],json=terms_request(p))
    else:
        accept_sides(client,candidate,mentor,p,assignment,p)
        acting=identities('HOST_COORDINATOR',organization)
        request=lambda:client.post(base+'/host-decisions',headers=acting['headers'],json={**terms_request(p),'action':'ACTIVATE'})
    member=member_for(acting,organization)
    entered,release=Event(),Event();original=admission_service._locked
    def before_business_locks(conn,pid):
        entered.set();assert release.wait(30)
        return original(conn,pid)
    monkeypatch.setattr(admission_service,'_locked',before_business_locks)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(request)
        try:
            assert entered.wait(30)
            changed=revoke(client,host,organization,member)
            assert changed.status_code==200,changed.text
            before=admission_snapshot()
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code in (403,404),response.text
    assert admission_snapshot()==before
    # This case gates preflight in Python; the next case observes an actual PostgreSQL wait.


def test_public_mentor_revocation_waits_for_personal_consent_commit_then_closes_new_access(
    client,identities,organization,monkeypatch):
    _,host,mentor,p,assignment=planned(client,identities,organization)
    member=member_for(mentor,organization)
    held,release=Event(),Event();pid=[];original=admission_service._consent
    def hold(conn,actor,placement,terms,side,*args,**kwargs):
        result=original(conn,actor,placement,terms,side,*args,**kwargs)
        if side=='MENTOR':
            pid.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set();assert release.wait(30)
        return result
    monkeypatch.setattr(admission_service,'_consent',hold)
    base='/api/v1/placements/'+p['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted=pool.submit(lambda:client.post(base+'/assignments/'+assignment['id']+'/accept',
                                             headers=mentor['headers'],json=terms_request(p)))
        try:
            assert held.wait(30)
            changed=pool.submit(lambda:revoke(client,host,organization,member))
            wait_for_blocker(pid[0]);assert not changed.done()
        finally:release.set()
        response=accepted.result(timeout=30);revoked=changed.result(timeout=30)
    assert response.status_code==200,response.text
    assert revoked.status_code==200,revoked.text
    assert client.get(base+'/plan',headers=mentor['headers']).status_code in (403,404)
    with transaction() as conn:
        assert conn.execute(select(table('placement_consents').c.id)).first() is not None
        assert conn.execute(select(table('mentor_assignments').c.accepted_at)).scalar_one() is not None
    assert saved(p)['status']=='PLANNED'


@pytest.mark.parametrize('same_key',[True,False])
def test_concurrent_candidate_duplicate_acceptance_records_one_intent(client,identities,organization,same_key):
    candidate,_,_,p,_=planned(client,identities,organization)
    first=terms_request(p);second=first if same_key else terms_request(p)
    def accept(body):return client.post('/api/v1/placements/'+p['id']+'/accept',headers=candidate['headers'],json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(accept,(first,second)))
    assert sorted(r.status_code for r in responses)==([200,200] if same_key else [200,409]),[r.text for r in responses]
    if same_key:assert responses[0].json()==responses[1].json()
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_consents')).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM flexbridge.audit_events WHERE action='PLACEMENT_CANDIDATE_ACCEPTED'")).scalar_one()==1


def test_concurrent_host_activation_replay_records_exactly_one_initial_start(client,identities,organization):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    accept_sides(client,candidate,mentor,p,assignment,p)
    body={**terms_request(p),'action':'ACTIVATE'}
    def activate(_):return client.post('/api/v1/placements/'+p['id']+'/host-decisions',headers=host['headers'],json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(activate,(0,1)))
    assert [r.status_code for r in responses]==[200,200],[r.text for r in responses]
    assert responses[0].json()==responses[1].json() and saved(p)['status']=='ACTIVE'
    with transaction() as conn:
        assert conn.execute(text("SELECT count(*) FROM flexbridge.placement_admission_events WHERE action='ACTIVATE'")).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM flexbridge.placement_consents WHERE side='HOST'")).scalar_one()==1
