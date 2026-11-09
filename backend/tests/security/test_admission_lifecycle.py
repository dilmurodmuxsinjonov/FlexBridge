"""Real host/candidate/mentor HTTP flow on disposable PostgreSQL, with trusted publication metadata."""
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table, transaction, now
from test_internship_admission import accepted_offer, post


def terms_request(plan, **extra):
    return dict(terms_id=plan.get('terms_id',plan.get('current_terms_id')), version=plan.get('version',1),
                idempotency_key=str(uuid4()), **extra)


def planned(client, identities, organization):
    candidate, host, body=accepted_offer(client,identities,organization,'INTERNSHIP')
    p=post(client,'/api/v1/placements',host,body,201)
    mentor=identities('MENTOR',organization)
    assignment=post(client,'/api/v1/placements/'+p['id']+'/mentor-assignments',host,{'mentor_id':mentor['user_id']},201)
    return candidate, host, mentor, p, assignment


def publish(client, host, p):
    response=client.put('/api/v1/placements/'+p['id']+'/plan',headers=host['headers'],json={
        **terms_request(p), 'title':'Backend internship', 'objectives':'Build and explain a reviewed service.',
        'daily_limit_minutes':360,'weekly_limit_minutes':1800,'required_minutes':360,
        'tasks':[{'code':'SERVICE','title':'Service implementation','expected_result':'Reviewed implementation',
                  'required':True,'target_minutes':360}]})
    assert response.status_code==200,response.text
    return response.json()


def saved(p):
    with transaction() as conn:
        return dict(conn.execute(select(table('placements')).where(table('placements').c.id==p['id'])).mappings().one())


def accept_sides(client,candidate,mentor,p,assignment,plan):
    post(client,'/api/v1/placements/'+p['id']+'/accept',candidate,terms_request(plan),200)
    post(client,'/api/v1/placements/'+p['id']+'/assignments/'+assignment['id']+'/accept',mentor,terms_request(plan),200)


def test_reachable_versioned_host_flow_records_personal_consents_and_single_historical_start(client,identities,organization):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    assert p['status']=='PLANNED' and assignment['accepted_at'] is None
    plan=publish(client,host,p)
    response=client.get('/api/v1/placements/'+p['id']+'/plan',headers=mentor['headers'])
    assert response.status_code==200 and response.headers['cache-control']=='no-store',response.text
    assert response.json()['tasks'][0]['code']=='SERVICE' and 'salary_min' not in response.json()
    accept_sides(client,candidate,mentor,p,assignment,plan)
    body={**terms_request(plan),'action':'ACTIVATE'}
    receipt=post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,body,200)
    assert receipt['status_at_decision']=='ACTIVE' and saved(p)['status']=='ACTIVE'
    assert post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,body,200)==receipt
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(plan),'action':'CANCEL'},200)
    assert saved(p)['status']=='CANCELLED'
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('placements').update().where(table('placements').c.id==p['id']).values(status='ACTIVE'))
    # A replay acknowledges its historical intent and never resurrects the cancelled placement.
    assert post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,body,200)==receipt
    assert saved(p)['status']=='CANCELLED'
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_consents')).scalar_one()==3
        assert conn.execute(text("SELECT count(*) FROM flexbridge.placement_admission_events WHERE action='ACTIVATE'")).scalar_one()==1
    assert client.get('/api/v1/me/placements',headers=candidate['headers']).json()['items'][0]['id']==p['id']
    assert client.get('/api/v1/organizations/'+organization+'/placements',headers=host['headers']).json()['items'][0]['id']==p['id']
    assert client.get('/api/v1/me/mentor-assignments',headers=mentor['headers']).json()['items'][0]['id']==assignment['id']


def test_new_plan_invalidates_old_candidate_and_mentor_acceptance_without_erasing_history(client,identities,organization):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    plan=publish(client,host,p)
    accept_sides(client,candidate,mentor,p,assignment,plan)
    next_plan=publish(client,host,{'id':p['id'],'current_terms_id':plan['terms_id'],'version':plan['version']})
    stale=client.post('/api/v1/placements/'+p['id']+'/accept',headers=candidate['headers'],json=terms_request(plan))
    assert stale.status_code==409,stale.text
    denied=client.post('/api/v1/placements/'+p['id']+'/host-decisions',headers=host['headers'],
                       json={**terms_request(next_plan),'action':'ACTIVATE'})
    assert denied.status_code==409 and saved(p)['status']=='PLANNED',denied.text
    accept_sides(client,candidate,mentor,p,assignment,next_plan)
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(next_plan),'action':'ACTIVATE'},200)
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_terms')).scalar_one()==3
        assert conn.execute(text("SELECT count(*) FROM flexbridge.placement_consents WHERE side='MENTOR'")).scalar_one()==2


@pytest.mark.parametrize('operation',['candidate','mentor','plan','inbox'])
def test_foreign_actor_cannot_acquire_plan_or_accept_another_party(client,identities,organization,operation):
    _,host,_,p,assignment=planned(client,identities,organization)
    outsider=identities()
    base='/api/v1/placements/'+p['id']
    if operation=='candidate':response=client.post(base+'/accept',headers=outsider['headers'],json=terms_request(p))
    elif operation=='mentor':response=client.post(base+'/assignments/'+assignment['id']+'/accept',headers=outsider['headers'],json=terms_request(p))
    elif operation=='plan':response=client.get(base+'/plan',headers=outsider['headers'])
    else:
        response=client.get('/api/v1/me/mentor-assignments',headers=outsider['headers'])
        assert response.status_code==200 and response.json()['items']==[],response.text
        return
    assert response.status_code in (403,404),response.text
    with transaction() as conn:
        assert conn.execute(select(table('placement_consents').c.id)).first() is None


def test_raw_acceptance_active_and_plan_rewrite_cannot_replace_personal_proof(client,identities,organization):
    _,host,_,p,assignment=planned(client,identities,organization)
    publish(client,host,p)
    for name,key,values in (
        ('placements',p['id'],{'status':'ACTIVE'}),
        ('placement_terms',p['current_terms_id'],{'candidate_accepted_at':now()}),
        ('placement_terms',p['current_terms_id'],{'terms_snapshot':{'forged':True}}),
        ('mentor_assignments',assignment['id'],{'accepted_at':now()})):
        with pytest.raises(IntegrityError),transaction() as conn:
            conn.execute(table(name).update().where(table(name).c.id==key).values(**values))
    assert saved(p)['status']=='PLANNED'


def test_published_and_superseded_plan_tasks_cannot_be_extended_with_new_rows(client,identities,organization):
    from app.services.placements import insert_row
    _,host,_,p,_=planned(client,identities,organization)
    current=publish(client,host,p)
    for terms_id in (p['current_terms_id'],current['terms_id']):
        with pytest.raises(IntegrityError),transaction() as conn:
            insert_row(conn,'plan_tasks',terms_id=terms_id,code='LATE',title='Unpublished addition',
                       expected_result='Cannot silently alter a captured plan version.',required=True,target_minutes=60)


def test_revoked_and_regranted_mentor_needs_new_nomination_and_personal_acceptance(client,identities,organization):
    from app.services.placements import insert_row
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    accept_sides(client,candidate,mentor,p,assignment,p)
    with transaction() as conn:
        q=table('mentor_assignment_proofs')
        original=conn.execute(select(q.c.mentor_grant_id).where(q.c.assignment_id==assignment['id'])).scalar_one()
        grants=table('org_role_grants')
        old=dict(conn.execute(select(grants).where(grants.c.id==original)).mappings().one())
        # Trusted authority change, not a certificate of the invitation workflow.
        conn.execute(grants.update().where(grants.c.id==original).values(revoked_at=now()))
        new=insert_row(conn,'org_role_grants',membership_id=old['membership_id'],role_id=old['role_id'],granted_by_id=host['user_id'])
        assert new['id']!=original
    base='/api/v1/placements/'+p['id']
    assert client.get(base+'/plan',headers=mentor['headers']).status_code in (403,404)
    assert client.get('/api/v1/me/mentor-assignments',headers=mentor['headers']).json()['items']==[]
    denied=client.post(base+'/assignments/'+assignment['id']+'/accept',headers=mentor['headers'],json=terms_request(p))
    assert denied.status_code==403,denied.text
    denied=client.post(base+'/host-decisions',headers=host['headers'],json={**terms_request(p),'action':'ACTIVATE'})
    assert denied.status_code in (403,409) and saved(p)['status']=='PLANNED',denied.text
    post(client,base+'/mentor-assignments/'+assignment['id']+'/revoke',host,terms_request(p),200)
    replacement=post(client,base+'/mentor-assignments',host,{'mentor_id':mentor['user_id']},201)
    post(client,base+'/assignments/'+replacement['id']+'/accept',mentor,terms_request(p),200)
    post(client,base+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)


def test_recorded_personal_intents_survive_later_session_logout(client,identities,organization):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    accept_sides(client,candidate,mentor,p,assignment,p)
    for who in (candidate,mentor):
        assert client.delete('/api/v1/me/sessions/'+who['session_id'],headers=who['headers']).status_code==200
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)
    assert saved(p)['status']=='ACTIVE'


def test_candidate_consent_rolls_back_with_audit_failure(client,identities,organization,monkeypatch):
    from app.services.placement_admission import admission_service
    from test_admission_current_actor import admission_snapshot
    candidate,_,_,p,_=planned(client,identities,organization)
    before=admission_snapshot()
    def broken(**kwargs):raise RuntimeError('Injected audit failure')
    monkeypatch.setattr(admission_service.audit,'append_audit_event',broken)
    response=client.post('/api/v1/placements/'+p['id']+'/accept',headers=candidate['headers'],json=terms_request(p))
    assert response.status_code==503,response.text
    assert admission_snapshot()==before


def test_failed_plan_publication_rolls_back_terms_tasks_pointer_and_event(client,identities,organization,monkeypatch):
    from app.services.placement_admission import admission_service
    from test_admission_current_actor import admission_snapshot
    _,host,_,p,_=planned(client,identities,organization)
    before=admission_snapshot();original=admission_service.audit.append_audit_event
    def broken(**kwargs):
        if kwargs['action']=='PLACEMENT_PLAN_PUBLISHED':raise RuntimeError('Injected publication audit failure')
        return original(**kwargs)
    monkeypatch.setattr(admission_service.audit,'append_audit_event',broken)
    response=client.put('/api/v1/placements/'+p['id']+'/plan',headers=host['headers'],json={
        **terms_request(p),'title':'Atomic plan','objectives':'A failed publication must preserve the prior plan.',
        'daily_limit_minutes':360,'weekly_limit_minutes':1800,'required_minutes':360,
        'tasks':[{'code':'TASK','title':'Atomic task','expected_result':'No partial publication','required':True}]})
    assert response.status_code==503,response.text
    assert admission_snapshot()==before


def test_ordinary_password_mentor_can_personally_accept_current_named_assignment(client,identities,organization):
    from app.services.placements import insert_row
    candidate,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    mentor=identities()  # Actual PASSWORD session issued before trusted ordinary MENTOR appointment.
    with transaction() as conn:
        roles=table('role_catalog')
        rid=conn.execute(select(roles.c.id).where(roles.c.code=='MENTOR',roles.c.scope_kind=='ORG')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code='MENTOR',scope_kind='ORG',description='Ordinary mentor')['id']
        member=insert_row(conn,'org_memberships',organization_id=organization,user_id=mentor['user_id'],status='ACTIVE')
        insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=rid,granted_by_id=host['user_id'])
        assert conn.execute(select(table('sessions').c.assurance).where(table('sessions').c.id==mentor['session_id'])).scalar_one()=='PASSWORD'
    p=post(client,'/api/v1/placements',host,body,201)
    assignment=post(client,'/api/v1/placements/'+p['id']+'/mentor-assignments',host,{'mentor_id':mentor['user_id']},201)
    accept_sides(client,candidate,mentor,p,assignment,p)
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)
    assert saved(p)['status']=='ACTIVE'


def test_ordinary_password_host_coordinator_can_create_and_activate_own_host_placement(client,identities,organization):
    from app.services.placements import insert_row
    candidate,_,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    host=identities();mentor=identities('MENTOR',organization)
    with transaction() as conn:
        roles=table('role_catalog')
        rid=conn.execute(select(roles.c.id).where(roles.c.code=='HOST_COORDINATOR',roles.c.scope_kind=='ORG')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code='HOST_COORDINATOR',scope_kind='ORG',description='Ordinary host coordinator')['id']
        member=insert_row(conn,'org_memberships',organization_id=organization,user_id=host['user_id'],status='ACTIVE')
        insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=rid,granted_by_id=host['user_id'])
        assert conn.execute(select(table('sessions').c.assurance).where(table('sessions').c.id==host['session_id'])).scalar_one()=='PASSWORD'
    p=post(client,'/api/v1/placements',host,body,201)
    assignment=post(client,'/api/v1/placements/'+p['id']+'/mentor-assignments',host,{'mentor_id':mentor['user_id']},201)
    accept_sides(client,candidate,mentor,p,assignment,p)
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)
    assert saved(p)['status']=='ACTIVE'


@pytest.mark.parametrize('withdraw_grant',[False,True])
def test_workplace_review_requires_original_current_personally_accepted_mentor(client,identities,organization,withdraw_grant):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    accept_sides(client,candidate,mentor,p,assignment,p)
    base='/api/v1/placements/'+p['id']
    post(client,base+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)
    response=client.put(base+'/logs/'+p['start_date'],headers=candidate['headers'],json={
        'day_type':'WORKED','summary_text':'Actual implementation result','total_minutes':60})
    assert response.status_code==200,response.text
    log=response.json();post(client,'/api/v1/logs/'+log['id']+'/submit',candidate,{},200)
    if withdraw_grant:
        from app.services.placements import insert_row
        with transaction() as conn:
            proof=table('mentor_assignment_proofs');grants=table('org_role_grants')
            gid=conn.execute(select(proof.c.mentor_grant_id).where(proof.c.assignment_id==assignment['id'])).scalar_one()
            old=dict(conn.execute(select(grants).where(grants.c.id==gid)).mappings().one())
            conn.execute(grants.update().where(grants.c.id==gid).values(revoked_at=now()))
            insert_row(conn,'org_role_grants',membership_id=old['membership_id'],role_id=old['role_id'],granted_by_id=host['user_id'])
    response=client.post('/api/v1/internship-logs/daily-logs/'+log['id']+'/workplace-reviews',headers=mentor['headers'],json={
        'placement_id':p['id'],'mentor_assignment_id':assignment['id'],'decision':'APPROVED','comment':'Actual named mentor result review.'})
    assert response.status_code==(403 if withdraw_grant else 201),response.text
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.workplace_log_reviews')).scalar_one()==(0 if withdraw_grant else 1)
