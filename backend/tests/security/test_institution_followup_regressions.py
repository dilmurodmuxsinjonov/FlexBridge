"""Review follow-up: claim replay and conservative omitted-term semantics."""
from sqlalchemy import select
from app.db.storage import table,transaction
from test_institution_onboarding import first_claim,submit,claim,decide
from test_regressions import count


def test_matching_reviewer_claim_is_a_receipt_without_duplicate_audit_or_timestamp(client,identities):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    case=created.json()['case_id'];moderator=identities('MODERATOR')
    first=claim(client,moderator,case);assert first.status_code==200,first.text
    before=count('audit_events')
    with transaction() as conn:
        cases=table('verification_cases');updated=conn.execute(select(cases.c.updated_at).where(cases.c.id==case)).scalar_one()
    again=claim(client,moderator,case);assert again.status_code==200,again.text
    assert again.json()==first.json() and count('audit_events')==before
    with transaction() as conn:assert conn.execute(select(cases.c.updated_at).where(cases.c.id==case)).scalar_one()==updated
    reviewed=decide(client,moderator,case);assert reviewed.status_code==200,reviewed.text
    after=count('audit_events')
    receipt=claim(client,moderator,case);assert receipt.status_code==200,receipt.text
    assert receipt.json()['status']=='APPROVED' and count('audit_events')==after


def test_omitted_revision_end_dates_preserve_existing_limits(client,identities):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    appointment,case=created.json()['id'],created.json()['case_id'];moderator=identities('MODERATOR')
    assert claim(client,moderator,case).status_code==200
    assert decide(client,moderator,case,'NEEDS_INFO').status_code==200
    payload={**f['body'],'expected_revision':1};payload.pop('valid_to');payload.pop('agreement_valid_to')
    response=client.post('/api/v1/institution-appointments/'+appointment+'/revisions',headers=f['user']['headers'],json=payload)
    assert response.status_code==202,response.text
    assert response.json()['valid_to']==f['body']['valid_to']
    assert response.json()['proposal']['agreement']['valid_to']==f['body']['agreement_valid_to']


def test_explicit_null_end_dates_are_a_new_unbounded_proposal_without_a_grant(client,identities):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    appointment,case=created.json()['id'],created.json()['case_id'];moderator=identities('MODERATOR')
    assert claim(client,moderator,case).status_code==200
    assert decide(client,moderator,case,'NEEDS_INFO').status_code==200
    payload={**f['body'],'expected_revision':1,'valid_to':None,'agreement_valid_to':None}
    response=client.post('/api/v1/institution-appointments/'+appointment+'/revisions',headers=f['user']['headers'],json=payload)
    assert response.status_code==202,response.text
    assert response.json()['valid_to'] is None and response.json()['proposal']['agreement']['valid_to'] is None
    assert count('institution_role_grants')==0
    with transaction() as conn:
        submissions=table('institution_onboarding_submissions')
        original=conn.execute(select(submissions).where(submissions.c.case_id==case,submissions.c.revision==1)).mappings().one()
        assert original['valid_to'].isoformat()==f['body']['valid_to']
        assert original['payload']['agreement_snapshot']['valid_to']==f['body']['agreement_valid_to']
