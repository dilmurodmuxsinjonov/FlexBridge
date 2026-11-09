"""Actual HTTP/PG enrollment lifecycle; CLEAN storage metadata is a trusted fixture."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from app.db.storage import table, transaction
from test_candidate import cv_fixture
from test_enrollment_migration import new_institution


def enrollment_body(owner, *, files=False):
    with transaction() as conn:inst=new_institution(conn)
    file=cv_fixture(owner) if files else None
    body=dict(institution_id=inst['id'],program='Engineering',start_date=(date.today()-timedelta(days=30)).isoformat(),
              end_date=(date.today()+timedelta(days=300)).isoformat(),idempotency_key=str(uuid4()),
              student_ref='test-student-reference-private',file_ids=[file['id']] if file else [],
              evidence_note='Current enrollment documentation for independent review.' if file else '')
    return body,file


def create(client,owner,body):
    response=client.post('/api/v1/me/enrollments',json=body,headers=owner['headers'])
    assert response.status_code==201,response.text
    return response.json()


def review(client,moderator,case_id,*,revision=1,decision='APPROVE'):
    claim=client.post('/api/v1/operator/verification-cases/'+case_id+'/claim',headers=moderator['headers'])
    assert claim.status_code==200,claim.text
    return client.post('/api/v1/operator/verification-cases/'+case_id+'/decide',headers=moderator['headers'],
                       json={'decision':decision,'expected_revision':revision,'reason':'Independent review of the exact submitted evidence.'})


def test_own_declared_history_is_private_and_never_current_student(client,identities):
    owner=identities();body,_=enrollment_body(owner);entry=create(client,owner,body)
    assert entry['contract_id']=='API-027' and entry['status']=='DECLARED' and entry['current_student'] is False
    response=client.get('/api/v1/me/enrollments',headers=owner['headers'])
    assert response.status_code==200 and response.json()['contract_id']=='API-034'
    assert [e['id'] for e in response.json()['items']]==[entry['id']]
    assert response.headers['cache-control']=='no-store'
    assert body['student_ref'] not in response.text and 'student_ref_digest' not in response.text
    assert 'storage_key' not in response.text and 'storage_version_id' not in response.text
    with transaction() as conn:
        reference=conn.execute(select(table('enrollments').c.student_ref_digest)).scalar_one()
        assert len(reference)==64 and reference!=body['student_ref']
    moderator=identities('MODERATOR')
    queue=client.get('/api/v1/operator/verification-cases?unassigned=true',headers=moderator['headers'])
    assert queue.status_code==200 and entry['case_id'] not in [r['id'] for r in queue.json()['items']]


def test_submitted_review_download_approval_end_preserve_profile(client,identities,monkeypatch):
    owner=identities();moderator=identities('MODERATOR');body,file=enrollment_body(owner,files=True)
    entry=create(client,owner,body);assert entry['status']=='PENDING' and not entry['current_student']
    claim=client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/claim',headers=moderator['headers'])
    assert claim.status_code==200,claim.text
    detail=client.get('/api/v1/operator/verification-cases/'+entry['case_id'],headers=moderator['headers'])
    assert detail.status_code==200,detail.text
    assert detail.json()['submissions'][0]['files'][0]['sha256']==file['sha256']
    signed=[]
    def presign(key,*,reference):
        signed.append((key,reference.version_id))
        return 'https://storage.invalid/exact-version'
    monkeypatch.setattr('app.adapters.storage.presign_get',presign)
    download=client.get('/api/v1/operator/verification-cases/'+entry['case_id']+'/files/'+file['id']+'/download',headers=moderator['headers'])
    assert download.status_code==200 and signed==[(file['storage_key'],file['storage_version_id'])]
    approved=review(client,moderator,entry['case_id']);assert approved.status_code==200,approved.text
    current=client.get('/api/v1/me/enrollments/'+entry['id'],headers=owner['headers'])
    assert current.status_code==200 and current.json()['current_student'] and current.json()['reviewed']
    # An accepted decision receipt is history, not a fresh approval or file download.
    with transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id==file['id'])
                     .values(sha256='0'*64 if file['sha256']!='0'*64 else '1'*64))
    retry=client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/decide',headers=moderator['headers'],
                     json={'decision':'APPROVE','expected_revision':1,'reason':'Independent review of the exact submitted evidence.'})
    assert retry.status_code==200 and retry.json()==approved.json(),retry.text
    end_body={'idempotency_key':str(uuid4()),'reason':'Graduated and ended this current education.'}
    ended=client.post('/api/v1/me/enrollments/'+entry['id']+'/end',json=end_body,headers=owner['headers'])
    assert ended.status_code==200 and ended.json()['status']=='ENDED',ended.text
    replay=client.post('/api/v1/me/enrollments/'+entry['id']+'/end',json=end_body,headers=owner['headers'])
    assert replay.status_code==200 and replay.json()==ended.json()
    final=client.get('/api/v1/me/enrollments/'+entry['id'],headers=owner['headers'])
    assert final.json()['current_student'] is False and final.json()['reviewed'] is True
    assert client.get('/api/v1/me/candidate',headers=owner['headers']).status_code==200
    with transaction() as conn:
        assert conn.execute(select(table('candidate_profiles').c.id).where(table('candidate_profiles').c.id==owner['candidate_id'])).scalar_one()==owner['candidate_id']
        assert conn.execute(select(table('enrollment_events').c.action).where(table('enrollment_events').c.enrollment_id==entry['id'])).scalars().all().count('END')==1


def test_needs_info_resubmits_same_case_preserving_decision_history(client,identities):
    owner=identities();moderator=identities('MODERATOR');body,_=enrollment_body(owner,files=True)
    entry=create(client,owner,body)
    decision=review(client,moderator,entry['case_id'],decision='NEEDS_INFO');assert decision.status_code==200,decision.text
    revision={key:body[key] for key in ('program','start_date','file_ids','evidence_note')}
    revision.update(expected_revision=1,evidence_note='Additional independent enrollment evidence explanation.')
    response=client.post('/api/v1/me/enrollments/'+entry['id']+'/verification',json=revision,headers=owner['headers'])
    assert response.status_code==202,response.text
    assert response.json()['case_id']==entry['case_id'] and response.json()['revision']==2
    assert response.json()['end_date']==body['end_date']
    approved=review(client,moderator,entry['case_id'],revision=2);assert approved.status_code==200,approved.text
    with transaction() as conn:
        history=conn.execute(select(table('enrollment_events').c.action).where(table('enrollment_events').c.case_id==entry['case_id'],
            table('enrollment_events').c.action.in_(('NEEDS_INFO','APPROVE'))).order_by(table('enrollment_events').c.revision)).scalars().all()
        assert history==['NEEDS_INFO','APPROVE']


@pytest.mark.parametrize('field,value',[('candidate_id',str(uuid4())),('status','VERIFIED'),('verified',True),('reviewer_id',str(uuid4()))])
def test_client_authority_fields_are_rejected(client,identities,field,value):
    owner=identities();body,_=enrollment_body(owner);body[field]=value
    response=client.post('/api/v1/me/enrollments',json=body,headers=owner['headers'])
    assert response.status_code==422,response.text
    with transaction() as conn:assert conn.execute(select(table('enrollments').c.id)).first() is None


def test_foreign_scope_anonymous_and_create_key_replay(client,identities):
    owner=identities();other=identities();body,_=enrollment_body(owner);entry=create(client,owner,body)
    assert create(client,owner,body)['id']==entry['id']
    changed={**body,'program':'Different request'}
    assert client.post('/api/v1/me/enrollments',json=changed,headers=owner['headers']).status_code==409
    assert client.get('/api/v1/me/enrollments').status_code==401
    assert client.get('/api/v1/me/enrollments/'+entry['id'],headers=other['headers']).status_code==404
    denied=client.post('/api/v1/me/enrollments/'+entry['id']+'/end',headers=other['headers'],
                       json={'idempotency_key':str(uuid4()),'reason':'Foreign enrollment cannot be ended by me.'})
    assert denied.status_code==404,denied.text
    with transaction() as conn:assert conn.execute(select(table('enrollments').c.id)).scalars().all()==[entry['id']]
