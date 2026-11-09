"""Concrete peer-review replay reproduction and enrollment-specific self-review."""
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,text
from app.db.storage import get_engine, table, transaction
from test_enrollments import create, enrollment_body, review
from test_enrollment_transactions import snapshot
from test_org_authority_transactions import wait_for_blocker


def test_revision_retry_rejects_changed_pinned_file_material_without_new_effect(client,identities):
    owner=identities();body,file=enrollment_body(owner,files=True)
    entry=create(client,owner,{**body,'file_ids':[],'evidence_note':''})
    request={key:body[key] for key in ('program','start_date','end_date','file_ids','evidence_note')}
    request['expected_revision']=1
    url='/api/v1/me/enrollments/'+entry['id']+'/verification'
    first=client.post(url,json=request,headers=owner['headers'])
    assert first.status_code==202 and first.json()['revision']==2,first.text
    before=snapshot();unchanged=client.post(url,json=request,headers=owner['headers'])
    assert unchanged.status_code==202 and unchanged.json()==first.json(),unchanged.text
    assert snapshot()==before
    # Trusted metadata mutation models changed material; this is not a public S3 overwrite claim.
    version=str(uuid4())
    with transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id==file['id']).values(
            storage_version_id=version,object_version=version,storage_etag=str(uuid4()),
            sha256='2'*64 if file['sha256']!='2'*64 else '3'*64))
    before=snapshot();retry=client.post(url,json=request,headers=owner['headers'])
    assert snapshot()==before
    assert retry.status_code==409,(retry.status_code,retry.json())
    assert retry.json()['detail']['code']=='ENROLLMENT_EVIDENCE_CHANGED'


def test_requester_with_actual_moderator_mfa_cannot_claim_or_decide_own_case(client,identities):
    owner=identities('MODERATOR');body,_=enrollment_body(owner,files=True);entry=create(client,owner,body)
    before=snapshot();base='/api/v1/operator/verification-cases/'+entry['case_id']
    queue=client.get('/api/v1/operator/verification-cases?unassigned=true',headers=owner['headers'])
    assert queue.status_code==200 and entry['case_id'] not in [item['id'] for item in queue.json()['items']]
    claimed=client.post(base+'/claim',headers=owner['headers'])
    assert claimed.status_code==403,claimed.text
    denied=client.post(base+'/decide',headers=owner['headers'],json={
        'decision':'APPROVE','expected_revision':1,'reason':'My moderator role cannot approve my own enrollment.'})
    assert denied.status_code==403,denied.text
    assert snapshot()==before
    independent=identities('MODERATOR')
    claim=client.post(base+'/claim',headers=independent['headers']);assert claim.status_code==200,claim.text
    before=snapshot()
    denied=client.post(base+'/decide',headers=owner['headers'],json={
        'decision':'APPROVE','expected_revision':1,'reason':'Another assigned reviewer still does not authorize my self-review.'})
    assert denied.status_code==403 and snapshot()==before
    with transaction() as conn:
        assert conn.execute(select(table('enrollments').c.status).where(table('enrollments').c.id==entry['id'])).scalar_one()=='PENDING'


def test_revision_replay_rechecks_logout_after_actual_file_wait(client,identities):
    owner=identities();body,file=enrollment_body(owner,files=True)
    entry=create(client,owner,{**body,'file_ids':[],'evidence_note':''})
    request={key:body[key] for key in ('program','start_date','end_date','file_ids','evidence_note')};request['expected_revision']=1
    url='/api/v1/me/enrollments/'+entry['id']+'/verification'
    first=client.post(url,json=request,headers=owner['headers']);assert first.status_code==202,first.text
    before=snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(select(table('files')).where(table('files').c.id==file['id']).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(lambda:client.post(url,json=request,headers=owner['headers']))
            wait_for_blocker(pid)
            revoked=client.delete('/api/v1/me/sessions/'+owner['session_id'],headers=owner['headers'])
            assert revoked.status_code==200,revoked.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert snapshot()==before


def test_end_preserves_existing_ordinary_application_and_new_service_access(client,identities,organization):
    from test_candidate import published_fixture
    from app.services.placements import placement_service
    owner=identities();employer=identities('OWNER',organization);moderator=identities('MODERATOR')
    body,_=enrollment_body(owner,files=True);entry=create(client,owner,body)
    approved=review(client,moderator,entry['case_id']);assert approved.status_code==200,approved.text
    # Existing published-opportunity metadata is a trusted fixture, not publisher acceptance.
    opportunity=published_fixture(employer,organization)
    application=placement_service.create_application(opportunity_id=opportunity['opportunity_id'],
        candidate_id=owner['candidate_id'],actor_user_id=owner['user_id'])
    with transaction() as conn:
        original=dict(conn.execute(select(table('applications')).where(table('applications').c.id==application['id'])).mappings().one())
    ended=client.post('/api/v1/me/enrollments/'+entry['id']+'/end',headers=owner['headers'],
        json={'idempotency_key':str(uuid4()),'reason':'Graduation keeps ordinary work history and access.'})
    assert ended.status_code==200,ended.text
    with transaction() as conn:
        assert dict(conn.execute(select(table('applications')).where(table('applications').c.id==application['id'])).mappings().one())==original
    next_opportunity=published_fixture(employer,organization)
    next_application=placement_service.create_application(opportunity_id=next_opportunity['opportunity_id'],
        candidate_id=owner['candidate_id'],actor_user_id=owner['user_id'])
    assert next_application['candidate_id']==owner['candidate_id'] and next_application['id']!=application['id']
    assert client.get('/api/v1/me/candidate',headers=owner['headers']).status_code==200
