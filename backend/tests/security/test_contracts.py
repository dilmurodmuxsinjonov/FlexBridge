"""Contract and matching coverage retained while replacing unsafe prototype fixtures."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.storage import transaction,table
from app.services.opportunities import opportunity_service,OpportunityConstraintError,validate_compensation_contract_matrix
from app.services.availability import availability_service
from test_adapters_and_quota import draft,approve_for_test
from test_candidate import candidate_actor
from test_regressions import checkout,capture,billing,count,placement_fixture,billing_actor

@pytest.mark.parametrize('contract,compensation,hourly,stipend',[
    ('INVALID','HOURLY',100,None),('LABOR_PART_TIME','HOURLY',100,100),
    ('LABOR_PART_TIME','STIPEND',None,100),('LABOR_PART_TIME','HOURLY',0,None)])
def test_compensation_contract_rejections(contract,compensation,hourly,stipend):
    with pytest.raises(OpportunityConstraintError):
        validate_compensation_contract_matrix(opportunity_kind='PART_TIME_JOB',contract_type=contract,
            compensation_type=compensation,hourly_pay=hourly,stipend_amount=stipend)

def test_matching_complete_groups_and_db_shift_exclusion(identities,organization):
    owner=identities('OWNER',organization);candidate=identities()
    o,i,a=checkout(owner,organization);capture(a)
    rev=draft(owner,organization)
    # Onsite matching now includes the specified 30-minute travel buffer at both ends.
    for weekday in (1,3):availability_service.add_availability_rule(actor=candidate_actor(candidate),candidate_id=candidate['candidate_id'],weekday=weekday,start_minute=510,end_minute=750)
    for group,days in [('GROUP_A',(1,3,5)),('GROUP_B',(1,3))]:
        for weekday in days:opportunity_service.add_opportunity_shift(revision_id=rev['id'],group_code=group,weekday=weekday,
            start_minute=540,end_minute=720,actor_user_id=owner['user_id'])
    with pytest.raises(OpportunityConstraintError):
        opportunity_service.add_opportunity_shift(revision_id=rev['id'],group_code='GROUP_A',weekday=1,start_minute=600,end_minute=800,actor_user_id=owner['user_id'])
    approve_for_test(rev)
    billing.publish_opportunity_with_quota(organization_id=organization,opportunity_id=rev['opportunity_id'],actor_user_id=owner['user_id'])
    assert opportunity_service.match_candidate_feed_api_003(candidate_id=candidate['candidate_id'],schedule_match_mode='ALL_SHIFTS_IN_GROUP')==[]
    matched=opportunity_service.match_candidate_feed_api_003(candidate_id=candidate['candidate_id'],schedule_match_mode='ANY_SHIFT_IN_GROUP')
    assert len(matched)==1 and matched[0]['matched_group_codes']==['GROUP_B']

def test_composite_fk_and_deferred_transaction_rollback(identities,organization):
    owner=identities('OWNER',organization)
    with pytest.raises(IntegrityError),transaction() as conn:
        revision=draft(owner,organization)
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(current_revision_id=str(uuid4())))
    assert count('opportunities')==count('opportunity_revisions')==0

def test_published_revision_database_immutable(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    revision=draft(owner,organization);approve_for_test(revision)
    billing.publish_opportunity_with_quota(organization_id=organization,opportunity_id=revision['opportunity_id'],actor_user_id=owner['user_id'])
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==revision['id']).values(title='Mutated'))

def test_submitted_log_summary_database_immutable(client,identities,organization):
    owner=identities('OWNER',organization);candidate=identities();p=placement_fixture(candidate,owner,organization)
    from datetime import date
    from app.services.internship_logs import internship_log_service
    log=internship_log_service.create_daily_log_with_revision(actor=billing_actor(candidate),placement_id=p['id'],log_date=date.today().isoformat(),summary_text='Test work',total_minutes=60)
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('log_revisions').update().where(table('log_revisions').c.id==log['current_revision_id']).values(summary='Mutated'))

def test_unimplemented_contract_never_claims_success(client,identities):
    user=identities()
    # An endpoint outside this remediation remains explicitly unimplemented.
    r=client.get('/api/v1/operator/audit-events',headers=user['headers'])
    assert r.status_code==501,r.text
    assert r.json()['status']=='NOT_IMPLEMENTED'

def test_canonical_routes_have_no_duplicate_signature():
    import re
    from app.main import app
    paths=app.openapi()['paths']
    seen=set()
    for path,methods in paths.items():
        for method in methods:
            signature=(method,re.sub(r'\{[^}]+\}','{}',path))
            assert signature not in seen,signature
            seen.add(signature)

def test_live_and_ready_are_distinct(client):
    r=client.get('/api/v1/health/live')
    assert r.status_code==200 and r.json()['status']=='alive'
    assert client.get('/api/v1/health/ready').status_code==503

def test_membership_two_people_and_scoped_grant(client,identities,organization):
    requester,approver,target=identities('OWNER',organization),identities('OWNER',organization),identities()
    r=client.post('/api/v1/organizations/'+organization+'/members',json={'user_id':target['user_id'],'role_code':'BILLING'},headers=requester['headers'])
    assert r.status_code==201,r.text
    url='/api/v1/organizations/'+organization+'/members/'+r.json()['id']+'/approve'
    assert client.post(url,json={},headers=requester['headers']).status_code==409
    r=client.post(url,json={},headers=approver['headers']);assert r.status_code==200,r.text
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers=target['headers']).status_code==403
    from app.services.auth import generate_totp_code
    enrollment=client.patch('/api/v1/me/security',headers=target['headers'],json={'enable_totp':True,'current_password':'correct-passphrase-2026'})
    assert enrollment.status_code==200,enrollment.text
    code=generate_totp_code(enrollment.json()['secret'])
    assert client.post('/api/v1/me/security/totp/confirm',headers=target['headers'],json={'code':code}).status_code==200
    signed_in=client.post('/api/v1/auth/login',json={'user_id':target['user_id'],'password':'correct-passphrase-2026','totp_code':code})
    assert signed_in.status_code==200,signed_in.text
    headers={'Authorization':'Bearer '+signed_in.json()['access_token']}
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers=headers).status_code==403
    assert client.post('/api/v1/organizations/'+organization+'/orders',headers=headers,json={
        'plan_code':'ORG_PLAN_30D','idempotency_key':'delegated-billing-order'}).status_code==201

def test_independent_moderation_is_durable(client,identities,organization):
    owner=identities('OWNER',organization);moderator=identities('MODERATOR');revision=draft(owner,organization)
    r=client.post('/api/v1/moderation/actions',headers=moderator['headers'],json={'target_entity_type':'opportunity',
        'target_entity_id':revision['opportunity_id'],'action_type':'APPROVE','policy_code':'P1','reason_code':'REVIEWED','justification':'Independent moderation completed'})
    assert r.status_code==201,r.text
    with transaction() as conn:
        assert conn.execute(select(table('opportunities').c.status).where(table('opportunities').c.id==revision['opportunity_id'])).scalar_one()=='APPROVED'
    assert count('moderation_actions')==1

def test_unconfigured_gateway_never_executes_approved_refund(identities,organization,monkeypatch):
    from app.workers.outbox import relay_pending_outbox_events
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    refund=billing.request_refund(invoice_id=i.id,amount_uzs=100,reason='Valid refund request reason',actor=billing_actor(owner))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    monkeypatch.delenv('PAYMENT_GATEWAY_URL',raising=False)
    assert relay_pending_outbox_events()==0
    with transaction() as conn:
        assert conn.execute(select(table('refunds').c.status)).scalar_one()=='APPROVED'
    assert count('billing_ledger')==1

def test_gateway_refund_effect_and_acknowledgement(identities,organization,monkeypatch):
    from app.workers.outbox import relay_pending_outbox_events
    from app.workers import refunds
    import httpx
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    refund=billing.request_refund(invoice_id=i.id,amount_uzs=100,reason='Valid refund request reason',actor=billing_actor(owner))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    calls=[]
    class GatewayClient:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            assert headers['Idempotency-Key']==refund['refund_id']
            assert json['provider_transaction_id']=='provider-event-123'
            calls.append(json)
            return httpx.Response(200,request=httpx.Request('POST',url),json={'refund_id':refund['refund_id'],'status':'REFUNDED','provider_refund_id':'provider-refund-123'})
    monkeypatch.setenv('PAYMENT_GATEWAY_URL','https://gateway.test.invalid');monkeypatch.setenv('PAYMENT_GATEWAY_TOKEN','ephemeral-test-secret')
    monkeypatch.setattr(refunds.httpx,'Client',GatewayClient)
    assert relay_pending_outbox_events()==1
    assert relay_pending_outbox_events()==0 and len(calls)==1
    with transaction() as conn:
        assert conn.execute(select(table('refunds').c.status)).scalar_one()=='REFUNDED'
        assert conn.execute(select(table('service_entitlements').c.status)).scalar_one()=='REFUNDED'
    assert count('billing_ledger')==2

def test_refund_revocation_uses_same_organization_lock(identities,organization):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.workers.refunds import apply_refund
    from app.db.storage import get_engine
    from sqlalchemy import text
    import time
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    refund=billing.request_refund(invoice_id=i.id,amount_uzs=100,reason='Valid refund request reason',actor=billing_actor(owner))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    billing.approve_refund(refund['refund_id'],billing_actor(identities('FINANCE')))
    started=Event()
    def revoke():
        with transaction() as conn:
            conn.execute(text("SET LOCAL application_name = 'refund_lock_regression'"));started.set()
            apply_refund(conn,{'payload':{'refund_id':refund['refund_id']}},{'provider_refund_id':'locked-refund'})
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction() as conn:
            conn.execute(select(table('organizations').c.id).where(table('organizations').c.id==organization).with_for_update())
            future=pool.submit(revoke);assert started.wait(3)
            locked=False;deadline=time.monotonic()+3
            while time.monotonic()<deadline and not future.done():
                with get_engine().connect() as observer:
                    locked=observer.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name='refund_lock_regression' AND wait_event_type='Lock'")).scalar_one()>0
                if locked:break
                time.sleep(.01)
            assert locked,'Refund revocation bypassed the organization serialization lock'
        future.result(timeout=5)
