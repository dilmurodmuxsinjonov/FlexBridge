"""Independent whole-placement conclusion contract, actual HTTP/session fixtures.

Staff/document metadata is trusted setup. Admission, diary submission, revision
review and all conclusion/context actions are real HTTP, not mock route returns.
"""
from datetime import date,timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select,text

from app.db.storage import table,transaction,now
from app.db.institution_scope import TASHKENT
from test_academic_reviews import ready,body as review_body,send as review_send
from test_academic_admission import plan
from app.services.auth import auth_service


def reviewed(client,identities,organization):
    # The actual placement service creates a period spanning yesterday/today.
    # This exercises two valid diary dates without spoofing time or relaxing
    # the production rule that future diary writes are rejected.
    start=now().astimezone(TASHKENT).date()-timedelta(days=1)
    f,assignment,draft=ready(client,identities,organization,placement_start_date=start)
    response=review_send(client,f,draft,review_body(assignment))
    assert response.status_code==201,response.text
    return f,assignment,draft


def context(client,f,assignment):
    response=client.get('/api/v1/placements/'+f['placement']['id']+'/academic-decision-context',
        headers=f['teacher']['headers'],params={'academic_assignment_id':assignment['id']})
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    return response.json()


def request_body(assignment,ctx,**extra):
    return {'academic_assignment_id':assignment['id'],'terms_id':ctx['terms_id'],'version':ctx['version'],
        'expected_basis_digest':ctx['basis_digest'],'decision':'ACADEMIC_REVIEW_COMPLETE',
        'reason':'I have reviewed the complete current academic diary basis.',
        'idempotency_key':str(uuid4()),**extra}


def conclude(client,f,payload):
    return client.post('/api/v1/placements/'+f['placement']['id']+'/academic-decisions',
        headers=f['teacher']['headers'],json=payload)


def test_current_teacher_gets_minimum_whole_placement_context(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization)
    ctx=context(client,f,assignment)
    assert ctx['log_count']==ctx['submitted_count']==ctx['reviewed_count']==1
    assert ctx['pending_count']==ctx['needs_revision_count']==0
    assert ctx['academic_review_complete'] is True and ctx['advisory_only'] is True
    assert ctx['new_conclusion_allowed'] is True and ctx['current_conclusion'] is None
    assert len(ctx['basis_digest'])==64
    assert 'Private academic work summary' not in str(ctx)
    assert not {'basis_snapshot','summary','session_id','teacher_grant_id','legal_basis','files'} & set(ctx)


def test_official_grade_input_is_rejected_before_any_conclusion_effect(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization);p=plan(client,f)
    response=conclude(client,f,request_body(assignment,{'terms_id':p['terms_id'],'version':p['version'],
        'basis_digest':'0'*64},official_grade=5))
    assert response.status_code==422,response.text
    with transaction() as conn:
        decisions=table('placement_decisions')
        assert conn.execute(select(decisions.c.id).where(decisions.c.side=='TEACHER')).first() is None


def test_a_reviewed_revision_cannot_hide_another_pending_log_or_stale_basis(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization)
    old=context(client,f,assignment);p=plan(client,f)
    # A second in-period current-day draft is not submitted/reviewed work.
    other_date=(date.fromisoformat(p['start_date'])+timedelta(days=1)).isoformat()
    draft=client.put('/api/v1/placements/'+f['placement']['id']+'/logs/'+other_date,
        headers=f['candidate']['headers'],json={'day_type':'WORKED','summary_text':'Another unreviewed current diary draft.',
                                               'total_minutes':0})
    assert draft.status_code==200,draft.text
    current=context(client,f,assignment)
    assert current['log_count']==2 and current['reviewed_count']==1 and current['pending_count']==1
    assert current['academic_review_complete'] is False
    assert current['basis_digest']!=old['basis_digest']
    stale=conclude(client,f,request_body(assignment,old))
    assert stale.status_code==412 and stale.json()['detail']['code']=='ACADEMIC_BASIS_CHANGED',stale.text
    pending=conclude(client,f,request_body(assignment,current))
    assert pending.status_code==409 and pending.json()['detail']['code']=='ACADEMIC_REVIEWS_PENDING',pending.text
    negative=conclude(client,f,request_body(assignment,current,decision='ACADEMIC_REVISION_REQUIRED'))
    assert negative.status_code==201,negative.text
    assert negative.json()['side']=='TEACHER' and negative.json()['decision']=='ACADEMIC_REVISION_REQUIRED'
    with transaction() as conn:
        placements=table('placements')
        assert conn.execute(select(placements.c.status).where(placements.c.id==f['placement']['id'])).scalar_one()=='ACTIVE'


def test_positive_conclusion_does_not_certify_workplace_hours_or_complete_placement(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization);ctx=context(client,f,assignment)
    payload=request_body(assignment,ctx);first=conclude(client,f,payload)
    assert first.status_code==201,first.text
    assert first.json()['side']=='TEACHER' and first.json()['decision']=='ACADEMIC_REVIEW_COMPLETE'
    assert conclude(client,f,payload).json()==first.json()
    with transaction() as conn:
        placements=table('placements');reviews=table('workplace_log_reviews')
        assert conn.execute(select(placements.c.status).where(placements.c.id==f['placement']['id'])).scalar_one()=='ACTIVE'
        assert conn.execute(select(reviews.c.id)).first() is None
    assert context(client,f,assignment)['current_conclusion']==first.json()


def test_old_receipt_does_not_approve_a_new_diary_basis(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization);ctx=context(client,f,assignment)
    payload=request_body(assignment,ctx);first=conclude(client,f,payload)
    assert first.status_code==201,first.text
    p=plan(client,f);another=(date.fromisoformat(p['start_date'])+timedelta(days=1)).isoformat()
    assert another!=p['start_date']
    draft=client.put('/api/v1/placements/'+f['placement']['id']+'/logs/'+another,
        headers=f['candidate']['headers'],json={'day_type':'WORKED','summary_text':'New basis after the old conclusion.',
                                               'total_minutes':0})
    assert draft.status_code==200,draft.text
    # Historical replay is a read of the old immutable receipt, with no new
    # decision, and cannot make the new basis current or complete.
    replay=conclude(client,f,payload)
    assert replay.status_code==201 and replay.json()==first.json(),replay.text
    current=context(client,f,assignment)
    assert current['current_conclusion'] is None and current['academic_review_complete'] is False
    with transaction() as conn:
        assert conn.execute(text('SELECT flexbridge.academic_decision_basis_current(CAST(:id AS uuid))'),
            {'id':first.json()['id']}).scalar_one() is False
        decisions=table('placement_decisions')
        assert len(conn.execute(select(decisions.c.id).where(decisions.c.side=='TEACHER')).all())==1


def test_committed_conclusion_survives_logout_without_resurrecting_old_session(client,identities,organization):
    f,assignment,_=reviewed(client,identities,organization);ctx=context(client,f,assignment)
    first=conclude(client,f,request_body(assignment,ctx));assert first.status_code==201,first.text
    logged_out=client.delete('/api/v1/me/sessions/'+f['teacher']['session_id'],headers=f['teacher']['headers'])
    assert logged_out.status_code==200,logged_out.text
    denied=client.get('/api/v1/placements/'+f['placement']['id']+'/academic-decision-context',
        headers=f['teacher']['headers'],params={'academic_assignment_id':assignment['id']})
    assert denied.status_code==401,denied.text
    with transaction() as conn:
        assert conn.execute(text('SELECT flexbridge.academic_decision_basis_current(CAST(:id AS uuid))'),
            {'id':first.json()['id']}).scalar_one() is True
        audits=table('audit_events')
        assert conn.execute(select(audits.c.id).where(audits.c.action=='SESSION_REVOKED',
            audits.c.object_key==f['teacher']['session_id'])).first() is not None
    session=auth_service.login(user_id=f['teacher']['user_id'],password='correct-passphrase-2026')
    assert session['session_id']!=f['teacher']['session_id']
    f['teacher']={**f['teacher'],**session,'headers':{'Authorization':'Bearer '+session['access_token']}}
    assert context(client,f,assignment)['current_conclusion']==first.json()


@pytest.mark.parametrize('writer_zone',['Asia/Tashkent','America/New_York'])
def test_review_proofs_written_in_a_non_utc_session_still_count(client,identities,organization,monkeypatch,writer_zone):
    """Regression: API-107 proofs snapshot rows in the writer's session TimeZone.

    A non-UTC server/session (FlexBridge's real Asia/Tashkent locale) previously
    rendered +05:00 offsets that never matched the UTC-pinned basis function, so
    every genuine review counted as pending and positive conclusions were impossible.
    """
    from sqlalchemy import create_engine
    from app.db import storage
    zoned=create_engine(storage.get_database_url(),pool_pre_ping=True,hide_parameters=True,
        connect_args={'prepare_threshold':None,'options':'-c TimeZone='+writer_zone})
    monkeypatch.setattr(storage,'_ENGINE',zoned)
    try:
        with transaction() as conn:
            assert conn.execute(text('SHOW TimeZone')).scalar_one()==writer_zone
        f,assignment,_=reviewed(client,identities,organization)
        ctx=context(client,f,assignment)
        assert ctx['log_count']==ctx['submitted_count']==ctx['reviewed_count']==1
        assert ctx['pending_count']==0 and ctx['academic_review_complete'] is True
        first=conclude(client,f,request_body(assignment,ctx))
        assert first.status_code==201,first.text
        with transaction() as conn:
            assert conn.execute(text('SELECT flexbridge.academic_decision_basis_current(CAST(:id AS uuid))'),
                {'id':first.json()['id']}).scalar_one() is True
    finally:
        zoned.dispose()
