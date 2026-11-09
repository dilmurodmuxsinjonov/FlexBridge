import hashlib
import io
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now,enqueue,outbox_table
from app.services.auth import auth_service,AuthError,hash_password,verify_password,generate_totp_code
from app.services.billing import BillingQuotaService,BillingInvariantError
from app.core.circuit_breaker import shared_circuit_breaker,FinanceCircuitOpenError
from app.api.dependencies import ActorContext

billing=BillingQuotaService()

def count(name):
    with transaction() as conn: return conn.execute(select(func.count()).select_from(table(name))).scalar_one()

def billing_actor(user):
    return ActorContext(user['user_id'],user['session_id'],())


def checkout(owner,org,plan='ORG_PLAN_30D'):
    order,invoice=billing.create_order_and_invoice(organization_id=org,plan_code=plan,actor=billing_actor(owner),idempotency_key='order-key-1234')
    attempt=billing.process_payment_attempt(invoice_id=invoice.id,provider_code='HMAC',idempotency_key='payment-key-1234',amount_uzs=invoice.amount_uzs,actor=billing_actor(owner))
    return order,invoice,attempt

def capture(attempt,event='provider-event-123'):
    args=dict(provider='HMAC',provider_event_id=event,attempt_id=attempt.id,amount_uzs=attempt.amount_uzs,timestamp=int(time.time()))
    return billing.confirm_payment_webhook_api_x04(**args,signature=billing.sign_webhook_payload(**args))

def placement_fixture(candidate,owner,org,status='ACTIVE'):
    from app.services.opportunities import opportunity_service
    from app.services.placements import placement_service
    revision=opportunity_service.create_opportunity_revision(organization_id=org,title='Test internship',opportunity_kind='INTERNSHIP',contract_type='INTERNSHIP_AGREEMENT',
        compensation_type='HOURLY',hourly_pay=20000,published=False,actor_user_id=owner['user_id'])
    with transaction() as conn:
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(status='PUBLISHED'))
    application=placement_service.create_application(opportunity_id=revision['opportunity_id'],candidate_id=candidate['candidate_id'],actor_user_id=candidate['user_id'])
    placement_service.create_application_attempt(application_id=application['id'],opportunity_id=revision['opportunity_id'],actor_user_id=candidate['user_id'])
    offer=placement_service.create_offer(application_id=application['id'],opportunity_id=revision['opportunity_id'],candidate_id=candidate['candidate_id'],offered_by=owner['user_id'])
    placement_service.respond_to_offer_api_043(offer_id=offer['id'],candidate_id=candidate['candidate_id'],decision='ACCEPT')
    p=placement_service.create_placement(application_id=application['id'],offer_id=offer['id'],opportunity_id=revision['opportunity_id'],candidate_id=candidate['candidate_id'],organization_id=org,actor=billing_actor(owner),start_date=date.today())
    if status=='ACTIVE':
        from app.services.placement_admission import admission_service
        from app.services.placements import insert_row,get_row
        # Roles/publication are trusted setup, while all admission/consent uses actual sessions.
        # An OWNER may independently hold MENTOR; the candidate is always another person.
        with transaction() as conn:
            roles,members,grants=(table(n) for n in ('role_catalog','org_memberships','org_role_grants'))
            rid=conn.execute(select(roles.c.id).where(roles.c.code=='MENTOR',roles.c.scope_kind=='ORG')).scalar_one_or_none()
            if not rid:rid=insert_row(conn,'role_catalog',code='MENTOR',scope_kind='ORG',description='Trusted mentor role')['id']
            mid=conn.execute(select(members.c.id).where(members.c.user_id==owner['user_id'],members.c.organization_id==org)).scalar_one()
            if not conn.execute(select(grants.c.id).where(grants.c.membership_id==mid,grants.c.role_id==rid)).first():
                insert_row(conn,'org_role_grants',membership_id=mid,role_id=rid,granted_by_id=owner['user_id'])
        args=dict(placement_id=p['id'],terms_id=p['current_terms_id'],version=1)
        admission_service.accept_candidate(actor=billing_actor(candidate),**args,idempotency_key=str(uuid4()))
        assignment=admission_service.nominate_mentor(actor=billing_actor(owner),placement_id=p['id'],organization_id=org,mentor_id=owner['user_id'])
        admission_service.accept_mentor(actor=billing_actor(owner),assignment_id=assignment['id'],**args,idempotency_key=str(uuid4()))
        admission_service.host_decision(actor=billing_actor(owner),action='ACTIVATE',**args,idempotency_key=str(uuid4()))
        with transaction() as conn:p=get_row(conn,'placements',p['id'])
    return p

def test_actual_migration_and_constraints():
    with transaction() as conn:
        assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0014_placement_admission'
        assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one()==118
        assert conn.execute(text("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON c.connamespace=n.oid WHERE n.nspname='flexbridge' AND contype='f'")).scalar_one()>=214
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('payment_attempts').insert().values(id=str(uuid4()),order_id=str(uuid4()),provider='HMAC',amount=-1,currency='UZS',status='PENDING',requested_at=now()))

@pytest.mark.parametrize('role',['EMPLOYER','OWNER','FINANCE','SUPER_ADMIN'])
def test_public_privilege_registration_rejected(client,role):
    r=client.post('/api/v1/auth/register',json={'display_name':'Attacker','password':'long-enough-password','adult_confirmed':True,'roles':[role]})
    assert r.status_code==403
    assert count('users')==0

def test_real_argon_phc():
    digest=hash_password('correct password')
    assert type(digest) is str and digest.startswith('$argon2id$')
    assert verify_password('correct password',digest) and not verify_password('incorrect',digest)

def test_session_digest_is_not_bearer(client,identities):
    user=identities()
    digest=hashlib.sha256(user['access_token'].encode()).hexdigest()
    for bearer in (digest,'sha256:'+digest,user['session_id']):
        assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+bearer}).status_code==401
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==200

def test_expired_session_blocks_all_writes(client,identities,organization):
    user=identities('OWNER',organization)
    with transaction() as conn:
        conn.execute(table('sessions').update().where(table('sessions').c.id==user['session_id']).values(expires_at=now()-timedelta(seconds=1)))
    for path,body in [('/api/v1/billing/orders',{'organization_id':organization,'plan_code':'ORG_PLAN_30D','idempotency_key':'order-key-1234'}),
        ('/api/v1/opportunities/revisions',{}),('/api/v1/placements/'+str(uuid4())+'/confirm-start',{'party':'ORGANIZATION'})]:
        assert client.post(path,json=body,headers=user['headers']).status_code==401
    assert count('orders')==0

def test_revoke_owner_only_and_immediate(client,identities):
    user,other=identities(),identities()
    assert client.delete('/api/v1/me/sessions/'+user['session_id'],headers=other['headers']).status_code==403
    assert client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers']).status_code==200
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==401

def test_mfa_proof_and_encrypted_secret(client,identities):
    user=identities()
    r=client.patch('/api/v1/me/security',json={'enable_totp':True,'current_password':'correct-passphrase-2026'},headers=user['headers'])
    assert r.status_code==200,r.text
    secret=r.json()['secret'];assert not r.json()['totp_enabled']
    with transaction() as conn:
        stored=conn.execute(select(table('mfa_credentials').c.secret_encrypted)).scalar_one()
    assert secret not in stored
    r=client.post('/api/v1/me/security/totp/confirm',json={'code':generate_totp_code(secret)},headers=user['headers'])
    assert r.status_code==200,r.text
    r=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':'correct-passphrase-2026'})
    assert r.status_code==202 and r.json()['mfa_required'] and 'access_token' not in r.json()

def test_open_breaker_no_invoice_and_no_fixture_reset(client,identities,organization):
    owner=identities('OWNER',organization)
    shared_circuit_breaker.trip(actor_id=owner['user_id'],incident_id='incident-123',reason_code='P1',details='test')
    for org in (organization,'child-org'):
        r=client.post('/api/v1/billing/orders',headers=owner['headers'],json={'organization_id':org,'plan_code':'ORG_PLAN_30D','idempotency_key':'order-key-1234'})
        assert r.status_code in (503,422)
    assert count('orders')==count('invoices')==0
    assert shared_circuit_breaker.state=='OPEN'

def test_cross_org_billing_rejected(client,identities,organization):
    outsider=identities()
    r=client.post('/api/v1/billing/orders',headers=outsider['headers'],json={'organization_id':organization,'plan_code':'ORG_PLAN_30D','idempotency_key':'order-key-1234'})
    assert r.status_code==403 and count('orders')==0

def test_pending_payment_no_entitlement_or_refund(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization)
    assert a.status=='PENDING_PROVIDER' and count('service_entitlements')==0
    with pytest.raises(BillingInvariantError,match='CAPTURED_PAYMENT_REQUIRED'):
        billing.request_refund(invoice_id=i.id,amount_uzs=1,reason='Valid refund reason',actor=billing_actor(owner))
    assert count('refunds')==0

def test_literal_signature_rejected_and_callback_exactly_once(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization)
    with pytest.raises(BillingInvariantError,match='SIGNATURE'):
        billing.confirm_payment_webhook_api_x04(provider='HMAC',provider_event_id='provider-event-123',attempt_id=a.id,amount_uzs=a.amount_uzs,
            timestamp=int(time.time()),signature='VALID_PROVIDER_WEBHOOK_SIGNATURE')
    assert capture(a)['idempotent_replay'] is False
    assert capture(a)['idempotent_replay'] is True
    assert count('service_entitlements')==count('billing_ledger')==1

def test_capture_survives_new_process(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization)
    args=dict(provider='HMAC',provider_event_id='provider-event-process',attempt_id=a.id,amount_uzs=a.amount_uzs,timestamp=int(time.time()))
    args['signature']=billing.sign_webhook_payload(**args)
    code='from app.services.billing import BillingQuotaService; BillingQuotaService().confirm_payment_webhook_api_x04(**'+repr(args)+')'
    r=subprocess.run([sys.executable,'-c',code],cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert count('service_entitlements')==1

def test_parallel_idempotent_orders(identities,organization):
    owner=identities('OWNER',organization)
    def create(_):return billing.create_order_and_invoice(organization_id=organization,plan_code='ORG_PLAN_30D',actor=billing_actor(owner),idempotency_key='same-key-1234')[0].id
    with ThreadPoolExecutor(max_workers=4) as pool: ids=list(pool.map(create,range(4)))
    assert len(set(ids))==1 and count('orders')==count('invoices')==1
    with pytest.raises(BillingInvariantError,match='IDEMPOTENCY_CONFLICT'):
        billing.create_order_and_invoice(organization_id=organization,plan_code='SINGLE_POST_30D',actor=billing_actor(owner),idempotency_key='same-key-1234')

def test_refund_requires_two_independent_authenticated_approvals(client,identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    r=billing.request_refund(invoice_id=i.id,amount_uzs=100,reason='Valid refund reason',actor=billing_actor(owner))
    rid=r['refund_id'];first,second=identities('FINANCE'),identities('FINANCE')
    assert client.post('/api/v1/operator/refunds/'+rid+'/approve',headers=owner['headers']).status_code==403
    assert client.post('/api/v1/operator/refunds/'+rid+'/approve',headers=first['headers']).json()['status']=='PENDING_SECOND_APPROVAL'
    assert client.post('/api/v1/operator/refunds/'+rid+'/approve',headers=first['headers']).status_code==409
    assert client.post('/api/v1/operator/refunds/'+rid+'/approve',headers=second['headers']).json()['status']=='APPROVED'
    assert count('outbox_events')==1

def test_parallel_refunds_cannot_overreserve(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    def request(_):
        try:billing.request_refund(invoice_id=i.id,amount_uzs=i.amount_uzs,reason='Valid refund reason',actor=billing_actor(owner));return True
        except BillingInvariantError:return False
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(request,range(2)))
    assert sorted(results)==[False,True] and count('refunds')==1

def test_foreign_org_cannot_confirm_placement_or_engagement(client,identities,organization):
    owner=identities('OWNER',organization);candidate,outsider=identities(),identities()
    p=placement_fixture(candidate,owner,organization,status='PENDING_START_CONFIRMATION')
    terms=dict(terms_id=p['current_terms_id'],version=1,idempotency_key=str(uuid4()),party='ORGANIZATION')
    r=client.post('/api/v1/placements/'+p['id']+'/confirm-start',json=terms,headers=outsider['headers'])
    assert r.status_code==403,r.text
    assert client.post('/api/v1/placements/'+p['id']+'/confirm-start',json=terms).status_code==401
    from app.services.placements import insert_row
    with transaction() as conn:
        eng=insert_row(conn,'job_engagements',application_id=p['application_id'],offer_id=p['offer_id'],status='PENDING_START_CONFIRMATION',start_date=date.today(),terms_snapshot={})
    url='/api/v1/engagements/'+eng['id']+'/confirmations'
    assert client.post(url,json={'party':'ORGANIZATION'},headers=outsider['headers']).status_code==403
    assert client.post(url,json={'party':'CANDIDATE'},headers=candidate['headers']).status_code==200
    r=client.post(url,json={'party':'ORGANIZATION'},headers=owner['headers'])
    assert r.status_code==200 and r.json()['status']=='ACTIVE',r.text

def test_foreign_draft_rejected_before_write_and_owner_submit(client,identities,organization):
    owner=identities('OWNER',organization);candidate,outsider=identities(),identities()
    p=placement_fixture(candidate,owner,organization)
    url='/api/v1/placements/'+p['id']+'/logs/'+date.today().isoformat()
    body={'day_type':'WORKED','summary_text':'Actual work','total_minutes':60}
    assert client.put(url,json=body,headers=outsider['headers']).status_code==403
    assert count('daily_logs')==0
    r=client.put(url,json=body,headers=candidate['headers']);assert r.status_code==200,r.text
    log_id=r.json()['id']
    assert client.post('/api/v1/logs/'+log_id+'/submit',headers=outsider['headers']).status_code==403
    r=client.post('/api/v1/logs/'+log_id+'/submit',headers=candidate['headers']);assert r.status_code==200,r.text
    assert r.json()['status']=='SUBMITTED'
    assert client.put(url,json=body,headers=candidate['headers']).status_code==409

def test_outbox_does_not_starve_after_50_processed():
    from app.workers.outbox import relay_pending_outbox_events
    with transaction() as conn:
        for i in range(61):
            eid=enqueue(conn,'TEST_EFFECT',str(i),{'i':i},'test:'+str(i))
            if i<60:conn.execute(outbox_table.update().where(outbox_table.c.id==eid).values(processed_at=now()))
    effects=[]
    registry={'TEST_EFFECT':(lambda e:e['payload']['i'],lambda c,e,r:effects.append(r))}
    assert relay_pending_outbox_events(registry=registry)==1 and effects==[60]

def test_outbox_failed_effect_stays_pending():
    from app.workers.outbox import relay_pending_outbox_events
    with transaction() as conn:eid=enqueue(conn,'TEST_FAIL','a',{},'failed-event')
    def fail(event): raise RuntimeError('Unavailable dependency')
    assert relay_pending_outbox_events(registry={'TEST_FAIL':(fail,lambda *a:None)})==0
    with transaction() as conn:
        r=conn.execute(select(outbox_table).where(outbox_table.c.id==eid)).mappings().one()
    assert r['processed_at'] is None and r['attempts']==1 and r['lease_until'] is None

@pytest.mark.parametrize('payload',[b'%PDF-1.7\nrandom garbage',b'%PDF-1.4\n1 0 obj\n<<>>\nendobj',b'plain data'])
def test_arbitrary_malformed_pdf_rejected(payload):
    from app.workers.pdf_check import validate_pdf
    with pytest.raises(ValueError):validate_pdf(payload)

def test_valid_pdf_and_active_content():
    from pypdf import PdfWriter
    from app.workers.pdf_check import validate_pdf
    w=PdfWriter();w.add_blank_page(width=100,height=100);raw=io.BytesIO();w.write(raw)
    assert validate_pdf(raw.getvalue())['pages']==1
    from pypdf.actions import JavaScript
    w.add_open_action(JavaScript('app.alert("hello")'));raw=io.BytesIO();w.write(raw)
    with pytest.raises(ValueError):validate_pdf(raw.getvalue())

def test_readiness_cannot_be_enabled_by_environment(client,monkeypatch):
    monkeypatch.setenv('FLEXBRIDGE_EXTERNAL_SERVICES_VERIFIED','1')
    monkeypatch.delenv('S3_ENDPOINT_URL',raising=False);monkeypatch.delenv('CLAMAV_HOST',raising=False)
    r=client.get('/api/v1/health/ready');assert r.status_code==503,r.text
    assert r.json()['detail']['checks']['database'] is True

def test_audit_is_transactional_and_immutable(identities):
    from app.core.audit import AppendOnlyAuditStore
    user=identities();store=AppendOnlyAuditStore()
    with pytest.raises(ValueError),transaction():
        store.append_audit_event(actor_id=user['user_id'],action='ROLLBACK_TEST',entity_type='test',entity_id='a')
        raise ValueError('Rollback business transaction')
    assert count('audit_events')==0
    store.append_audit_event(actor_id=user['user_id'],action='IMMUTABLE_TEST',entity_type='test',entity_id='a')
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(table('audit_events').update().values(action='CHANGED'))
