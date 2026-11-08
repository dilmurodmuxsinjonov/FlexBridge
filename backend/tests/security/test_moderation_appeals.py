"""Real PostgreSQL appeal state, identity, concurrency and evidence boundaries."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.exc import IntegrityError,OperationalError
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from test_adapters_and_quota import draft

REASON='The original decision omitted material evidence'
DECISION_REASON='Independent review of the pinned evidence is complete'


def rejection(client,identities,organization,revision=None,owner=None):
    owner=owner or identities('OWNER',organization)
    moderator=identities('MODERATOR');revision=revision or draft(owner,organization)
    response=client.post('/api/v1/moderation/actions',headers=moderator['headers'],json={
        'target_entity_type':'opportunity','target_entity_id':revision['opportunity_id'],
        'action_type':'REJECT','policy_code':'EVIDENCE_REVIEW','reason_code':'MISSING_EVIDENCE',
        'justification':'Independent initial review rejected this opportunity'})
    assert response.status_code==201,response.text
    return owner,moderator,revision,response.json()


def submit(client,owner,original,**changes):
    return client.post('/api/v1/moderation/actions/'+original['id']+'/appeals',headers=owner['headers'],
        json={'reason':REASON,**changes})


def claim(client,reviewer,case_id):
    return client.post('/api/v1/operator/moderation-cases/'+case_id+'/claim',headers=reviewer['headers'],json={})


def decide(client,reviewer,case_id,decision='REOPEN',reason=DECISION_REASON):
    return client.post('/api/v1/operator/moderation-cases/'+case_id+'/actions',headers=reviewer['headers'],
        json={'decision':decision,'reason':reason})


def status(opportunity_id):
    with transaction() as conn:
        return conn.execute(select(table('opportunities').c.status).where(table('opportunities').c.id==opportunity_id)).scalar_one()


def audit_count(action):
    with transaction() as conn:
        return conn.execute(select(func.count()).select_from(table('audit_events')).where(table('audit_events').c.action==action)).scalar_one()


@pytest.mark.parametrize('decision,expected',[('UPHOLD','REJECTED'),('REOPEN','DRAFT')])
def test_real_appellant_and_assigned_independent_decision(client,identities,organization,decision,expected):
    owner,original_moderator,revision,original=rejection(client,identities,organization)
    submitted=submit(client,owner,original);assert submitted.status_code==201,submitted.text
    case_id=submitted.json()['case_id'];reviewer=identities('MODERATOR')
    assert submitted.headers['cache-control']=='no-store'
    assert submitted.json()['appellant_id']==owner['user_id'] and submitted.json()['status']=='OPEN'
    assert decide(client,reviewer,case_id).status_code==403
    assert claim(client,reviewer,case_id).status_code==200
    review=client.get('/api/v1/moderation-appeals/'+case_id,headers=reviewer['headers']).json()
    assert review['original_decision']['action']['reason']==original['reason']
    response=decide(client,reviewer,case_id,decision);assert response.status_code==200,response.text
    assert response.json()['status']=='RESOLVED' and status(revision['opportunity_id'])==expected
    assert decide(client,reviewer,case_id,decision).json()['idempotent_replay']
    assert decide(client,reviewer,case_id,decision,reason='Different final decision explanation').status_code==409
    with transaction() as conn:
        original_row=conn.execute(select(table('moderation_actions')).where(table('moderation_actions').c.id==original['id'])).mappings().one()
        assert original_row['action']=='REJECT' and original_row['actor_id']==original_moderator['user_id']
        result=conn.execute(select(table('moderation_actions')).where(table('moderation_actions').c.appealed_action_id==original['id'])).mappings().one()
        assert result['action']=='APPEAL_'+decision and result['actor_id']==reviewer['user_id']
        assert conn.execute(select(table('moderation_cases').c.decision).where(table('moderation_cases').c.id==case_id)).scalar_one()==decision
    assert audit_count('MODERATION_APPEAL_'+decision)==1
    if decision=='REOPEN':
        # Appeal cannot grant moderation approval or bypass paid publishing.
        assert client.post('/api/v1/opportunities/'+revision['opportunity_id']+'/publish',headers=owner['headers']).status_code==409


def test_submission_identity_org_scope_and_strict_payload(client,identities,organization):
    owner,_,_,original=rejection(client,identities,organization)
    path='/api/v1/moderation/actions/'+original['id']+'/appeals'
    assert client.post(path,json={'reason':REASON}).status_code==401
    assert submit(client,identities(),original).status_code==403
    assert submit(client,owner,original,appellant_id=str(uuid4())).status_code==422
    assert submit(client,owner,original,reviewer_id=str(uuid4())).status_code==422
    assert submit(client,owner,original,reason=' '*16).status_code==422
    with transaction() as conn:
        other_org=insert_row(conn,'organizations',tax_id=str(uuid4()),legal_name='Other organization',
            public_name='Other organization',region='Tashkent',status='VERIFIED')
    assert submit(client,identities('OWNER',other_org['id']),original).status_code==403
    assert submit(client,owner,{'id':str(uuid4())}).status_code==404


def add_org_history(user,organization):
    with transaction() as conn:
        insert_row(conn,'org_memberships',organization_id=organization,user_id=user['user_id'],status='REVOKED',revoked_at=now())


def test_original_moderator_and_historical_org_participant_cannot_review(client,identities,organization):
    owner,original_moderator,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id']
    related=identities('MODERATOR');add_org_history(related,organization)
    for reviewer in (original_moderator,related):
        assert claim(client,reviewer,case_id).status_code==403
        assert client.get('/api/v1/operator/moderation-appeals',headers=reviewer['headers']).json()['items']==[]
    independent=identities('MODERATOR')
    queue=client.get('/api/v1/operator/moderation-appeals',headers=independent['headers'])
    assert queue.status_code==200 and queue.json()['items'][0]['case_id']==case_id
    assert 'reason' not in queue.json()['items'][0] and 'appellant_id' not in queue.json()['items'][0]
    assert client.get('/api/v1/moderation-appeals/'+case_id,headers=independent['headers']).status_code==403
    assert claim(client,independent,case_id).status_code==200
    add_org_history(independent,organization)
    assert decide(client,independent,case_id).status_code==403


def test_private_reads_assignment_and_revocation(client,identities,organization):
    owner,_,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR');other=identities('MODERATOR')
    assert claim(client,reviewer,case_id).status_code==200
    path='/api/v1/moderation-appeals/'+case_id
    assert client.get(path,headers=owner['headers']).status_code==200
    assert client.get(path,headers=reviewer['headers']).status_code==200
    assert client.get(path,headers=other['headers']).status_code==403
    assert decide(client,other,case_id).status_code==403
    with transaction() as conn:
        conn.execute(table('platform_role_grants').update().where(table('platform_role_grants').c.user_id==reviewer['user_id']).values(revoked_at=now()))
    assert client.get(path,headers=reviewer['headers']).status_code==403
    assert decide(client,reviewer,case_id).status_code==403
    assert audit_count('MODERATION_APPEAL_REOPEN')==0


def test_password_only_operator_cannot_claim_or_decide(client,identities,organization):
    from datetime import timedelta
    owner,grantor,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];user=identities()
    with transaction() as conn:
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='MODERATOR')).scalar_one()
        insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=rid,granted_by_id=grantor['user_id'],expires_at=now()+timedelta(hours=1))
    assert claim(client,user,case_id).status_code==403
    assert decide(client,user,case_id).status_code==403


def test_parallel_submission_is_single_and_changed_request_conflicts(client,identities,organization):
    owner,_,_,original=rejection(client,identities,organization)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(submit,client,owner,original) for _ in range(2)]]
    assert all(r.status_code==201 for r in results),[r.text for r in results]
    assert results[0].json()['case_id']==results[1].json()['case_id']
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    assert submit(client,owner,original,reason='Another materially different appeal reason').status_code==409
    assert audit_count('MODERATION_APPEAL_SUBMITTED')==1


def test_parallel_claim_and_decision_cannot_duplicate_actions(client,identities,organization):
    owner,_,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewers=[identities('MODERATOR') for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(claim,client,r,case_id) for r in reviewers]]
    assert sorted(r.status_code for r in results)==[200,409]
    winner=reviewers[[r.status_code for r in results].index(200)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(decide,client,winner,case_id) for _ in range(2)]]
    assert all(r.status_code==200 for r in results),[r.text for r in results]
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    assert audit_count('MODERATION_APPEAL_ASSIGNED')==audit_count('MODERATION_APPEAL_REOPEN')==1


def test_decision_audit_failure_rolls_back_all_effects(client,identities,organization,monkeypatch):
    from app.api.v1.moderation_appeals import service
    owner,_,revision,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR');claim(client,reviewer,case_id)
    def fail(**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(service.audit_store,'append_audit_event',fail)
    assert decide(client,reviewer,case_id).status_code==503
    assert status(revision['opportunity_id'])=='REJECTED'
    with transaction() as conn:
        assert conn.execute(select(table('moderation_appeal_requests').c.status)).scalar_one()=='ASSIGNED'
        assert conn.execute(select(func.count()).select_from(table('moderation_actions'))).scalar_one()==1


@pytest.mark.parametrize('operation,revoked',[('claim','grant'),('claim','session'),('decide','grant'),('decide','session')])
def test_revocation_while_waiting_for_business_locks_is_rechecked(client,identities,organization,monkeypatch,operation,revoked):
    from app.services import moderation_appeals as module
    owner,_,revision,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR')
    if operation=='decide':assert claim(client,reviewer,case_id).status_code==200
    entered,resume=Event(),Event();original_lock=module.locked_request
    def pause(*args):
        result=original_lock(*args);entered.set()
        if not resume.wait(15):raise RuntimeError('Test coordination timed out')
        return result
    monkeypatch.setattr(module,'locked_request',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(claim if operation=='claim' else decide,client,reviewer,case_id)
        try:
            assert entered.wait(15)
            with transaction() as conn:
                if revoked=='grant':
                    conn.execute(table('platform_role_grants').update().where(table('platform_role_grants').c.user_id==reviewer['user_id']).values(revoked_at=now()))
                else:conn.execute(table('sessions').update().where(table('sessions').c.id==reviewer['session_id']).values(revoked_at=now()))
        finally:resume.set()
        response=future.result(timeout=20)
    assert response.status_code==403,response.text
    assert status(revision['opportunity_id'])=='REJECTED'
    assert audit_count('MODERATION_APPEAL_REOPEN')==0
    with transaction() as conn:
        assert conn.execute(select(table('moderation_appeal_requests').c.status)).scalar_one()==('OPEN' if operation=='claim' else 'ASSIGNED')


@pytest.mark.parametrize('revoked',['grant','session'])
def test_authority_lock_serializes_revocation_with_commit(client,identities,organization,monkeypatch,revoked):
    from app.services import moderation_appeals as module
    owner,_,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR')
    entered,resume=Event(),Event();original_authority=module.moderator_authority
    def pause(*args):
        original_authority(*args);entered.set()
        if not resume.wait(15):raise RuntimeError('Test coordination timed out')
    monkeypatch.setattr(module,'moderator_authority',pause)
    target=table('platform_role_grants' if revoked=='grant' else 'sessions')
    condition=target.c.user_id==reviewer['user_id'] if revoked=='grant' else target.c.id==reviewer['session_id']
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(claim,client,reviewer,case_id)
        try:
            assert entered.wait(15)
            with pytest.raises(OperationalError) as exc,transaction() as conn:
                conn.execute(text("SET LOCAL lock_timeout='200ms'"))
                conn.execute(target.update().where(condition).values(revoked_at=now()))
            assert exc.value.orig.sqlstate=='55P03'
        finally:resume.set()
        assert future.result(timeout=20).status_code==200
    with transaction() as conn:conn.execute(target.update().where(condition).values(revoked_at=now()))
    assert decide(client,reviewer,case_id).status_code==403


@pytest.mark.parametrize('description,expected',[('é'*260000,201),('é'*263000,422),('é\\\n'*100000,422)],
    ids=['unicode-below-db-limit','unicode-above-db-limit','escaped-text-above-db-limit'])
def test_snapshot_size_uses_postgresql_jsonb_bytes(client,identities,organization,description,expected):
    owner,_,revision,original=rejection(client,identities,organization)
    with transaction() as conn:
        conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==revision['id']).values(description=description))
    response=submit(client,owner,original)
    assert response.status_code==expected,response.text[:300]
    if expected==422:assert response.json()['detail']['code']=='APPEAL_SNAPSHOT_TOO_LARGE'


def test_snapshot_keeps_full_decimal_salary_precision(client,identities,organization):
    from decimal import Decimal
    owner,_,revision,original=rejection(client,identities,organization)
    with transaction() as conn:
        conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==revision['id'])
            .values(salary_min=Decimal('9999999999999999.99')))
    response=submit(client,owner,original);assert response.status_code==201,response.text
    read=client.get('/api/v1/moderation-appeals/'+response.json()['case_id'],headers=owner['headers']).json()
    assert read['revision_snapshot']['revision']['salary_min']=='9999999999999999.99'


def test_sql_cannot_install_fabricated_appeal_evidence(client,identities,organization):
    owner,_,revision,original=rejection(client,identities,organization)
    with pytest.raises(IntegrityError),transaction() as conn:
        case=insert_row(conn,'moderation_cases',reporter_id=owner['user_id'],opportunity_id=revision['opportunity_id'],
            category='OPPORTUNITY_REJECTION_APPEAL',status='OPEN',severity='LOW',due_at=now())
        conn.execute(table('moderation_appeal_requests').insert().values(case_id=case['id'],created_at=now(),
            original_action_id=original['id'],opportunity_id=revision['opportunity_id'],revision_id=revision['id'],
            appellant_id=owner['user_id'],reason=REASON,revision_snapshot={'forged':True},original_decision={},status='OPEN'))
    assert submit(client,owner,original).status_code==201


@pytest.mark.parametrize('change',['status','content','later_decision'])
def test_stale_state_content_and_decision_cannot_be_reopened(client,identities,organization,change):
    owner,original_moderator,revision,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR');claim(client,reviewer,case_id)
    with transaction() as conn:
        if change=='status':conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(status='DRAFT'))
        elif change=='content':conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==revision['id']).values(title='Changed after appeal submission'))
        else:insert_row(conn,'moderation_actions',case_id=original['case_id'],actor_id=original_moderator['user_id'],action='REJECT',reason='A later independent rejection decision',occurred_at=now())
    response=decide(client,reviewer,case_id)
    assert response.status_code==409 and response.json()['detail']['code']=='APPEAL_DECISION_STALE'
    read=client.get('/api/v1/moderation-appeals/'+case_id,headers=owner['headers']).json()
    assert read['revision_snapshot']['revision']['title']==revision['title']
    assert audit_count('MODERATION_APPEAL_REOPEN')==0


def test_request_snapshot_and_original_action_are_immutable(client,identities,organization):
    owner,original_moderator,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id']
    for name,field,key,values in [('moderation_appeal_requests','case_id',case_id,{'reason':'Silently altered appeal evidence text'}),
        ('moderation_actions','id',original['id'],{'reason':'Silently altered original decision'})]:
        t=table(name)
        with pytest.raises(IntegrityError),transaction() as conn:conn.execute(t.update().where(t.c[field]==key).values(**values))
        with pytest.raises(IntegrityError),transaction() as conn:conn.execute(t.delete().where(t.c[field]==key))
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('moderation_appeal_requests').update().where(table('moderation_appeal_requests').c.case_id==case_id)
            .values(status='ASSIGNED',reviewer_id=original_moderator['user_id']))


def test_appeal_survives_separate_python_process(client,identities,organization):
    owner,_,_,original=rejection(client,identities,organization)
    case_id=submit(client,owner,original).json()['case_id']
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    code="from app.api.dependencies import ActorContext;from app.services.moderation_appeals import ModerationAppealsService;import sys,json;r=ModerationAppealsService().read(ActorContext(sys.argv[1],sys.argv[2],()),sys.argv[3]);print(json.dumps({'case_id':r['case_id'],'appellant_id':r['appellant_id'],'status':r['status']}))"
    result=subprocess.run([sys.executable,'-c',code,owner['user_id'],owner['session_id'],case_id],env=env,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)=={'case_id':case_id,'appellant_id':owner['user_id'],'status':'OPEN'}


def test_existing_accepted_relation_and_evidence_survive_reopen(client,identities,organization):
    from test_regressions import placement_fixture
    owner=identities('OWNER',organization);candidate=identities();placement=placement_fixture(candidate,owner,organization)
    with transaction() as conn:
        # Trusted legacy-data fixture: a reviewable opportunity with an accepted relation.
        application=conn.execute(select(table('applications')).where(table('applications').c.id==placement['application_id'])).mappings().one()
        opp=conn.execute(select(table('opportunities')).where(table('opportunities').c.id==application['opportunity_id'])).mappings().one()
        revision=dict(conn.execute(select(table('opportunity_revisions')).where(table('opportunity_revisions').c.id==opp['current_revision_id'])).mappings().one())
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==opp['id']).values(status='DRAFT'))
        before={name:[dict(r) for r in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()] for name in ('placements','offers','application_attempts')}
    owner,_,_,original=rejection(client,identities,organization,revision=revision,owner=owner)
    case_id=submit(client,owner,original).json()['case_id'];reviewer=identities('MODERATOR');claim(client,reviewer,case_id)
    assert decide(client,reviewer,case_id).status_code==200
    with transaction() as conn:
        for name,records in before.items():assert [dict(r) for r in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()]==records
