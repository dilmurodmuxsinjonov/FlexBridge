"""Human money requests use actual current authority after their blocking business rows."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
import pytest
from sqlalchemy import select,event,text
from app.api.dependencies import ActorContext
from app.db.storage import table,transaction,get_engine,now
from app.services.billing import BillingQuotaService
from app.services.governance import GovernanceError
from test_regressions import checkout,capture
from test_organizations import mfa_user
from test_org_authority_transactions import wait_for_blocker


KINDS=('order','canonical_order','order_replay','payment','payment_replay',
    'refund','canonical_refund','approve_first','approve_second')


def money_snapshot():
    with transaction() as conn:
        return {name:sorted((dict(row) for row in conn.execute(select(table(name))).mappings()),key=repr)
            for name in ('orders','invoices','payment_attempts','refunds','service_entitlements',
                'billing_ledger','idempotency_keys','outbox_events','audit_events','products','price_versions')}


def operation(kind,client,identities,org):
    owner=identities('OWNER',org);order,invoice,attempt=checkout(owner,org)
    user=owner;target_table,target_id='organizations',org
    data={'owner':owner,'order':order,'invoice':invoice,'attempt':attempt,'org':org}
    if kind in ('order','canonical_order','order_replay'):
        path='/api/v1/organizations/'+org+'/orders' if kind=='canonical_order' else '/api/v1/billing/orders'
        body={'plan_code':'ORG_PLAN_30D','idempotency_key':'order-key-1234' if kind=='order_replay' else 'authority-order-new'}
        if kind!='canonical_order':body['organization_id']=org
    elif kind in ('payment','payment_replay'):
        if kind=='payment_replay':capture(attempt)
        path='/api/v1/billing/payments/attempts';target_table,target_id='invoices',invoice.id
        body={'invoice_id':invoice.id,'amount_uzs':invoice.amount_uzs,'provider_code':'HMAC',
            'idempotency_key':'payment-key-1234' if kind=='payment_replay' else 'authority-payment-new'}
    else:
        capture(attempt)
        body={'amount_uzs':101,'reason':'Valid human money authority test request'}
        if kind in ('refund','canonical_refund'):
            path='/api/v1/orders/'+order.id+'/refund-requests' if kind=='canonical_refund' else '/api/v1/billing/refunds'
            if kind=='refund':body['invoice_id']=invoice.id
            target_table,target_id='payment_attempts',attempt.id
        else:
            response=client.post('/api/v1/billing/refunds',headers=owner['headers'],json={'invoice_id':invoice.id,**body})
            assert response.status_code==201,response.text
            rid=response.json()['refund_id'];data['refund_id']=rid
            first=identities('FINANCE');user=first
            path='/api/v1/operator/refunds/'+rid+'/approve';body=None
            if kind=='approve_second':
                response=client.post(path,headers=first['headers']);assert response.status_code==200,response.text
                user=identities('FINANCE');data['first_finance']=first
            target_table,target_id='refunds',rid
    def request():return client.post(path,headers=user['headers'],**({'json':body} if body is not None else {}))
    return user,(target_table,target_id),request,data


def change_authority(client,user,org,kind,change):
    if change=='session':
        response=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
        assert response.status_code==200,response.text
    elif change=='disable_mfa':
        response=client.patch('/api/v1/me/security',headers=user['headers'],json={
            'enable_totp':False,'current_password':'correct-passphrase-2026'})
        assert response.status_code==200,response.text
    else:
        # Explicit administrative fixtures; no public account/grant provisioning claimed.
        with transaction() as conn:
            if change=='account':
                users=table('users');conn.execute(users.update().where(users.c.id==user['user_id']).values(status='SUSPENDED',updated_at=now()))
            elif change=='auth_version':
                users=table('users');conn.execute(users.update().where(users.c.id==user['user_id']).values(auth_version=users.c.auth_version+1,updated_at=now()))
            elif change=='expiry':
                target=table('platform_role_grants') if kind.startswith('approve') else table('sessions')
                condition=target.c.user_id==user['user_id'] if kind.startswith('approve') else target.c.id==user['session_id']
                conn.execute(target.update().where(condition).values(expires_at=now()-timedelta(seconds=1),updated_at=now()))
            elif change=='role':
                if kind.startswith('approve'):
                    grants=table('platform_role_grants');condition=grants.c.user_id==user['user_id']
                else:
                    grants,members=table('org_role_grants'),table('org_memberships')
                    condition=grants.c.membership_id.in_(select(members.c.id).where(
                        members.c.user_id==user['user_id'],members.c.organization_id==org))
                conn.execute(grants.update().where(condition).values(revoked_at=now(),updated_at=now()))
            else:raise AssertionError(change)


@pytest.mark.parametrize('kind',KINDS)
@pytest.mark.parametrize('change',['session','disable_mfa'])
def test_completed_security_change_blocks_after_actual_money_lock(client,identities,organization,kind,change):
    user,(name,row_id),request,_=operation(kind,client,identities,organization)
    checked=Event();engine=get_engine()
    def observed(conn,cursor,statement,parameters,context,executemany):
        if 'FROM flexbridge.'+name in statement and 'FOR UPDATE' in statement:checked.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as conn:
            target=table(name);conn.execute(select(target.c.id).where(target.c.id==row_id).with_for_update())
            event.listen(engine,'before_cursor_execute',observed)
            try:
                pending=pool.submit(request)
                assert checked.wait(30) and not pending.done()
                change_authority(client,user,organization,kind,change);before=money_snapshot()
            finally:event.remove(engine,'before_cursor_execute',observed)
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(kind,change,response.status_code)
    assert money_snapshot()==before


@pytest.mark.parametrize('kind',['order','payment','refund','approve_second'])
@pytest.mark.parametrize('change',['account','auth_version','role','expiry'])
def test_admin_state_changes_are_rechecked_after_target_wait(client,identities,organization,kind,change):
    user,(name,row_id),request,_=operation(kind,client,identities,organization)
    checked=Event();engine=get_engine()
    def observed(conn,cursor,statement,parameters,context,executemany):
        if 'FROM flexbridge.'+name in statement and 'FOR UPDATE' in statement:checked.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as conn:
            target=table(name);conn.execute(select(target.c.id).where(target.c.id==row_id).with_for_update())
            event.listen(engine,'before_cursor_execute',observed)
            try:
                pending=pool.submit(request)
                assert checked.wait(30) and not pending.done()
                change_authority(client,user,organization,kind,change);before=money_snapshot()
            finally:event.remove(engine,'before_cursor_execute',observed)
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(kind,change,response.status_code)
    assert money_snapshot()==before


@pytest.mark.parametrize('kind',['order','payment','refund','approve_second'])
@pytest.mark.parametrize('change',['session','role'])
def test_authorized_money_commit_precedes_waiting_revoke(client,identities,organization,monkeypatch,kind,change):
    from app.services import authority
    user,_,request,_=operation(kind,client,identities,organization)
    held,release=Event(),Event();pid=[]
    name='platform_authority' if kind.startswith('approve') else 'org_authority'
    original=getattr(authority,name)
    def hold(conn,*args,**kwargs):
        result=original(conn,*args,**kwargs)
        pid.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
        held.set();assert release.wait(30)
        return result
    monkeypatch.setattr(authority,name,hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30)
            revoked=pool.submit(change_authority,client,user,organization,kind,change)
            wait_for_blocker(pid[0]);assert not revoked.done()
        finally:release.set()
        response=pending.result(timeout=30);revoked.result(timeout=30)
    assert response.status_code==(201 if kind in ('order','refund') else 200),response.text
    assert request().status_code in (401,403)


@pytest.mark.parametrize('kind',KINDS)
def test_current_mfa_controls_and_receipts_still_work(client,identities,organization,kind):
    user,_,request,data=operation(kind,client,identities,organization)
    before=money_snapshot();response=request()
    assert response.status_code==(201 if kind in ('order','canonical_order','order_replay','refund','canonical_refund') else 200),response.text
    if kind in ('order_replay','payment_replay'):assert money_snapshot()==before
    after=money_snapshot()
    if kind in ('order','canonical_order'):
        assert len(after['orders'])==len(before['orders'])+1 and len(after['invoices'])==len(before['invoices'])+1
        new=[row for row in after['orders'] if row['id'] not in {r['id'] for r in before['orders']}]
        assert new[0]['purchaser_id']==user['user_id'] and new[0]['organization_id']==organization
    elif kind=='payment':
        assert len(after['payment_attempts'])==len(before['payment_attempts'])+1
        assert len(after['service_entitlements'])==len(before['service_entitlements'])
    elif kind in ('refund','canonical_refund'):
        assert len(after['refunds'])==len(before['refunds'])+1
        assert after['refunds'][0]['status']=='REQUESTED' and after['refunds'][0]['requester_id']==user['user_id']
    elif kind.startswith('approve'):
        stored=next(row for row in after['refunds'] if row['id']==data['refund_id'])
        queued=[row for row in after['outbox_events'] if row['event_type']=='REFUND_EXECUTE']
        if kind=='approve_first':
            assert stored['status']=='PENDING_SECOND_APPROVAL' and stored['approver_id']==user['user_id']
            assert stored['second_approver_id'] is None and not queued
        else:
            assert stored['status']=='APPROVED' and stored['second_approver_id']==user['user_id']
            assert len({stored['requester_id'],stored['approver_id'],stored['second_approver_id']})==3 and len(queued)==1


@pytest.mark.parametrize('kind',['order','payment','refund','approve_second'])
def test_money_audit_finish_failure_rolls_back_every_billing_effect(client,identities,organization,monkeypatch,kind):
    from app.core.audit import AppendOnlyAuditStore
    _,_,request,_=operation(kind,client,identities,organization);before=money_snapshot()
    original_audit=AppendOnlyAuditStore.append_audit_event;original_finish=BillingQuotaService._finish
    def fail_audit(self,**kwargs):
        if kwargs['action']=={'order':'ORDER_CREATED','refund':'REFUND_REQUESTED','approve_second':'REFUND_APPROVED'}.get(kind):
            raise RuntimeError('Injected money audit failure')
        return original_audit(self,**kwargs)
    def fail_finish(self,conn,user,op,key,ref):
        original_finish(self,conn,user,op,key,ref)
        if kind=='payment' and op=='PAYMENT_ATTEMPT':raise RuntimeError('Injected payment result failure')
    monkeypatch.setattr(AppendOnlyAuditStore,'append_audit_event',fail_audit)
    monkeypatch.setattr(BillingQuotaService,'_finish',fail_finish)
    response=request();assert response.status_code==503,response.text
    assert money_snapshot()==before


def test_signed_capture_still_works_after_human_payer_logout(client,identities,organization):
    owner=identities('OWNER',organization);_,_,attempt=checkout(owner,organization)
    response=client.delete('/api/v1/me/sessions/'+owner['session_id'],headers=owner['headers']);assert response.status_code==200,response.text
    capture(attempt)
    with transaction() as conn:
        assert conn.execute(select(table('payment_attempts').c.status).where(table('payment_attempts').c.id==attempt.id)).scalar_one()=='CAPTURED'
        assert len(list(conn.execute(select(table('billing_ledger').c.id))))==1


def direct_call(kind,context,data):
    service=BillingQuotaService()
    if kind=='order':return service.create_order_and_invoice(actor=context,organization_id=data['org'],
        plan_code='ORG_PLAN_30D',idempotency_key='direct-current-authority')
    if kind=='payment':return service.process_payment_attempt(actor=context,invoice_id=data['invoice'].id,
        provider_code='HMAC',idempotency_key='direct-current-payment',amount_uzs=data['invoice'].amount_uzs)
    if kind=='refund':return service.request_refund(actor=context,invoice_id=data['invoice'].id,amount_uzs=101,
        reason='Valid direct refund request authority check')
    return service.approve_refund(data['refund_id'],actor=context)


@pytest.mark.parametrize('kind',['order','payment','refund','approve_second'])
@pytest.mark.parametrize('session_kind',['missing','foreign','unknown'])
def test_service_requires_actual_current_user_session_pair(client,identities,organization,kind,session_kind):
    user,_,_,data=operation(kind,client,identities,organization);other=identities()
    session={'missing':None,'foreign':other['session_id'],'unknown':str(uuid4())}[session_kind]
    context=ActorContext(user['user_id'],session,('OWNER','BILLING','FINANCE'))
    before=money_snapshot()
    with pytest.raises(GovernanceError,match='MFA_REQUIRED'):direct_call(kind,context,data)
    assert money_snapshot()==before


@pytest.mark.parametrize('kind',['order','payment','refund','approve_second'])
def test_cached_role_claims_cannot_replace_current_scoped_grants(client,identities,organization,kind):
    _,_,_,data=operation(kind,client,identities,organization);unprivileged=mfa_user(identities)
    context=ActorContext(unprivileged['user_id'],unprivileged['session_id'],('OWNER','BILLING','FINANCE'))
    before=money_snapshot()
    with pytest.raises(GovernanceError,match='FORBIDDEN_ROLE' if kind.startswith('approve') else 'ORG_SCOPE_FORBIDDEN'):
        direct_call(kind,context,data)
    assert money_snapshot()==before


def test_concurrent_refund_reservations_cannot_exceed_captured_amount(client,identities,organization):
    _,_,_,data=operation('refund',client,identities,organization)
    def request():return client.post('/api/v1/billing/refunds',headers=data['owner']['headers'],json={
        'invoice_id':data['invoice'].id,'amount_uzs':data['invoice'].amount_uzs,
        'reason':'Reserve the captured invoice amount for refund'})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:request(),range(2)))
    assert sorted(r.status_code for r in responses)==[201,409]
    after=money_snapshot()
    assert len(after['refunds'])==1 and after['refunds'][0]['amount']==data['invoice'].amount_uzs
    assert not [row for row in after['outbox_events'] if row['event_type']=='REFUND_EXECUTE']


def test_parallel_distinct_finance_approvals_and_retries_queue_one_execution(client,identities,organization):
    first,_,_,data=operation('approve_first',client,identities,organization)
    second,third=identities('FINANCE'),identities('FINANCE')
    path='/api/v1/operator/refunds/'+data['refund_id']+'/approve'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda user:client.post(path,headers=user['headers']),(first,second)))
    assert [r.status_code for r in responses]==[200,200]
    assert {r.json()['status'] for r in responses}=={'PENDING_SECOND_APPROVAL','APPROVED'}
    before=money_snapshot();stored=before['refunds'][0]
    assert stored['status']=='APPROVED' and {stored['approver_id'],stored['second_approver_id']}=={first['user_id'],second['user_id']}
    assert stored['requester_id']==data['owner']['user_id'] and len({stored['requester_id'],stored['approver_id'],stored['second_approver_id']})==3
    assert len([row for row in before['outbox_events'] if row['event_type']=='REFUND_EXECUTE'])==1
    for user in (first,second,third):assert client.post(path,headers=user['headers']).status_code==409
    assert money_snapshot()==before


def test_finance_role_does_not_allow_requester_to_approve_own_refund(client,identities,organization):
    from app.services.placements import insert_row
    finance,_,_,data=operation('approve_first',client,identities,organization)
    with transaction() as conn:
        roles=table('role_catalog')
        rid=conn.execute(select(roles.c.id).where(roles.c.code=='FINANCE',roles.c.scope_kind=='PLATFORM')).scalar_one()
        insert_row(conn,'platform_role_grants',user_id=data['owner']['user_id'],role_id=rid,
            granted_by_id=finance['user_id'],expires_at=now()+timedelta(hours=1))
    before=money_snapshot()
    response=client.post('/api/v1/operator/refunds/'+data['refund_id']+'/approve',headers=data['owner']['headers'])
    assert response.status_code==409 and response.json()['detail']['code']=='SELF_APPROVAL_FORBIDDEN',response.text
    assert money_snapshot()==before
