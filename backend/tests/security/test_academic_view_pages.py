"""Scoped cursor anchors and >100 actual supervision intents; staff/agreement metadata is trusted setup."""
from uuid import uuid4
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.storage import table,transaction,now
from app.db.institution_scope import TASHKENT
from app.services.placements import insert_row
from test_academic_admission import pending_http,nominate,plan
from test_academic_views import get,active_revision
from test_internship_admission import post
from test_organizations import mfa_user


def test_another_current_coordinator_does_not_receive_first_coordinators_private_scope(client,identities,organization):
    f=pending_http(client,identities,organization);other=mfa_user(identities)
    with transaction() as conn:
        member=insert_row(conn,'institution_memberships',institution_id=f['inst']['id'],user_id=other['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=other['user_id'],document_file_id=f['appointment']['document_file_id'],
            status='ACTIVE',valid_from=now().astimezone(TASHKENT).date()-timedelta(days=1),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=f['grant']['role_id'],appointment_id=appointment['id'])
    prefix='institutions/'+f['inst']['id']
    assert get(client,prefix+'/supervisions',other)['items']==[]
    # CAP020 allows own-school students' unbound pending requests, without diary data.
    assert len(get(client,prefix+'/assignment-queue',other)['items'])==1
    nominate(client,f)
    assert get(client,prefix+'/assignment-queue',other)['items']==[]
    assert get(client,'student-supervisions/'+f['supervision']['id']+'/academic-assignments',other)['items']==[]


@pytest.mark.parametrize('kind',['supervisions','assignment-queue','review-queue'])
def test_cursor_from_another_institution_cannot_anchor_own_scope(client,identities,organization,kind):
    f=pending_http(client,identities,organization);foreign=pending_http(client,identities,organization)
    if kind=='supervisions':cursor=foreign['supervision']['id'];user=f['coord']
    elif kind=='assignment-queue':
        cursor=get(client,'institutions/'+foreign['inst']['id']+'/assignment-queue',foreign['coord'])['items'][0]['id'];user=f['coord']
    else:
        _,draft=active_revision(client,f);_,other=active_revision(client,foreign)
        for obj,log in ((f,draft),(foreign,other)):
            post(client,'/api/v1/logs/'+log['id']+'/submit',obj['candidate'],{},200)
        cursor=other['current_revision_id'];user=f['teacher']
    path='me/academic-review-queue' if kind=='review-queue' else 'institutions/'+f['inst']['id']+'/'+kind
    response=client.get('/api/v1/'+path,headers=user['headers'],params={'after':cursor})
    assert response.status_code==404 and response.json()['detail']['code']=='PAGE_CURSOR_NOT_FOUND',response.text


def test_actual_opaque_purpose_supervisions_page_beyond_100_with_tied_ordering(client,identities,organization):
    f=pending_http(client,identities,organization);purposes=['ACADEMIC_VIEW']+['ACADEMIC_PURPOSE_'+str(i) for i in range(104)]
    with transaction() as conn:
        a=table('institution_agreements');conn.execute(a.update().where(a.c.id==f['agreement']['id']).values(purposes=purposes))
    identifiers={f['supervision']['id']}
    for purpose in purposes[1:]:
        row=post(client,'/api/v1/student-supervisions',f['coord'],dict(institution_id=f['inst']['id'],enrollment_id=f['enrollment']['id'],
            agreement_id=f['agreement']['id'],purpose=purpose,legal_basis='Explicit administrative fixture purpose basis.',idempotency_key=str(uuid4())),201)
        identifiers.add(row['id'])
    # Trusted ordering metadata only; personal acceptance timestamps/proofs stay intact.
    with transaction() as conn:
        s=table('student_supervisions');conn.execute(s.update().where(s.c.institution_id==f['inst']['id']).values(created_at=now()))
    path='institutions/'+f['inst']['id']+'/supervisions'
    first=get(client,path,f['coord'],limit=100);second=get(client,path,f['coord'],limit=100,after=first['next_after'])
    assert len(first['items'])==100 and len(second['items'])==5 and second['next_after'] is None
    actual=[r['id'] for r in first['items']+second['items']]
    assert len(actual)==len(set(actual))==105 and set(actual)==identifiers
    assert len(get(client,path,f['coord'],purpose=purposes[43])['items'])==1
