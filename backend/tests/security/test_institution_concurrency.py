"""Registry identity, nonblocking contacts/foreign users, and cached claims."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import select,text
from app.api.dependencies import ActorContext
from app.core.iam_security import digest
from app.db.storage import table,transaction,get_engine
from app.services.governance import GovernanceError
from app.services.institution_onboarding import institution_onboarding_service as service
from app.api.v1.institution_onboarding import AppointmentInput
from test_institution_onboarding import first_claim,submit,accept,claim,decide,active_coordinator,staff_claim
from test_institution_transactions import business_snapshot
from test_regressions import count


def test_concurrent_matching_intake_is_one_request_and_one_institution(client,identities):
    f=first_claim(identities)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:submit(client,f),range(2)))
    assert all(response.status_code==202 for response in responses),[response.text for response in responses]
    assert responses[0].json()['id']==responses[1].json()['id']
    assert count('institutions')==count('institution_onboarding_requests')==count('institution_onboarding_submissions')==1
    assert count('institution_role_grants')==0


def test_concurrent_different_claimants_cannot_duplicate_normalized_registry(client,identities):
    first,other=first_claim(identities),first_claim(identities)
    other['body']['registry_code']=' '+first['body']['registry_code'].lower()+' '
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda f:submit(client,f),(first,other)))
    assert sorted(response.status_code for response in responses)[0]==202
    assert sum(response.status_code==202 for response in responses)==1,[response.text for response in responses]
    assert all(response.status_code in (202,403,409,422) for response in responses)
    assert count('institutions')==count('institution_onboarding_requests')==1 and count('institution_role_grants')==0


def test_busy_identity_contact_is_nonblocking_and_rolls_back_the_entire_intake(client,identities):
    f=first_claim(identities);before=business_snapshot()
    key=digest('contact-lock',f['contact']['channel']+':'+f['contact']['normalized_value'])
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':key})
            pending=pool.submit(lambda:submit(client,f));response=pending.result(timeout=10)
            assert response.status_code==409,response.text
            assert response.json()['detail']['code']=='INSTITUTION_BUSY_RETRY'
    assert business_snapshot()==before
    assert submit(client,f).status_code==202


def test_busy_foreign_target_during_review_returns_retry_without_partial_decision(client,identities):
    f=active_coordinator(client,identities);teacher=identities();request,verified,body=staff_claim(client,f,teacher)
    assert accept(client,f,request['id'],user=teacher,contact_id=verified['id']).status_code==200
    assert claim(client,f['moderator'],request['case_id']).status_code==200
    before=business_snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(select(table('users')).where(table('users').c.id==teacher['user_id']).with_for_update())
            response=pool.submit(lambda:decide(client,f['moderator'],request['case_id'])).result(timeout=10)
            assert response.status_code==409,response.text
            assert response.json()['detail']['code']=='INSTITUTION_BUSY_RETRY'
    assert business_snapshot()==before
    result=decide(client,f['moderator'],request['case_id']);assert result.status_code==200,result.text
    assert result.json()['status']=='ACTIVE'


def test_direct_intake_service_cannot_use_foreign_session_or_cached_privilege_claims(identities):
    f=first_claim(identities);stranger=identities();before=business_snapshot()
    actor=ActorContext(f['user']['user_id'],stranger['session_id'],('COORDINATOR','MODERATOR','OWNER'))
    with pytest.raises(GovernanceError) as exc:
        service.submit(actor,**AppointmentInput(**f['body']).model_dump(),idempotency_key='direct-foreign-session')
    assert exc.value.status_code in (401,403) and business_snapshot()==before
