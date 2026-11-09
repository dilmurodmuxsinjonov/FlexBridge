"""Independently reproduced review findings; DB fixtures are trusted administration."""
from datetime import timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from app.services.institution_onboarding import proof_insert
from test_candidate import cv_fixture
from test_institution_onboarding import first_claim,submit,active_coordinator,staff_claim,accept


@pytest.mark.parametrize('kind',['cache_headers','body_limit'])
def test_onboarding_families_use_private_headers_and_bound_request_bodies(client,identities,kind):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    paths=['/api/v1/institution-onboarding/options','/api/v1/me/institution-appointments',
        '/api/v1/institution-appointments/'+created.json()['id']]
    for path in paths:
        if kind=='cache_headers':
            response=client.get(path,headers=f['user']['headers']);assert response.status_code==200,response.text
            assert response.headers.get('cache-control')=='no-store',(path,dict(response.headers))
            assert response.headers.get('pragma')=='no-cache'
            assert response.headers.get('referrer-policy')=='no-referrer'
        else:
            response=client.request('GET',path,headers={**f['user']['headers'],'Content-Type':'application/json'},content=b'x'*131073)
            assert response.status_code==413,(path,response.status_code)


@pytest.mark.parametrize('scope_kind',['PLATFORM','ORG','INSTITUTION'])
def test_db_consent_guard_matches_global_sensitive_role_mfa_policy(client,identities,organization,scope_kind):
    f=active_coordinator(client,identities);teacher=identities();request,verified,body=staff_claim(client,f,teacher)
    with transaction() as conn:
        roles=table('role_catalog')
        # Trusted administrative role changes, not public self-registration/grant.
        if scope_kind=='PLATFORM':
            rid=conn.execute(select(roles.c.id).where(roles.c.code=='MODERATOR',roles.c.scope_kind=='PLATFORM')).scalar_one()
            insert_row(conn,'platform_role_grants',user_id=teacher['user_id'],role_id=rid,granted_by_id=f['moderator']['user_id'],expires_at=now()+timedelta(hours=1))
        elif scope_kind=='ORG':
            rid=conn.execute(select(roles.c.id).where(roles.c.code=='BILLING',roles.c.scope_kind=='ORG')).scalar_one()
            member=insert_row(conn,'org_memberships',organization_id=organization,user_id=teacher['user_id'],status='ACTIVE',accepted_at=now())
            insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=rid,granted_by_id=f['user']['user_id'])
        else:
            from datetime import date
            rid=conn.execute(select(roles.c.id).where(roles.c.code=='COORDINATOR',roles.c.scope_kind=='INSTITUTION')).scalar_one()
            member=insert_row(conn,'institution_memberships',institution_id=f['institution_id'],user_id=teacher['user_id'],status='ACTIVE',accepted_at=now())
            document=cv_fixture(teacher)
            appointment=insert_row(conn,'institution_appointments',institution_id=f['institution_id'],user_id=teacher['user_id'],document_file_id=document['id'],status='ACTIVE',valid_from=date.today(),accepted_at=now())
            insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=rid,appointment_id=appointment['id'])
        submissions=table('institution_onboarding_submissions')
        revision=conn.execute(select(submissions).where(submissions.c.case_id==request['case_id'],submissions.c.revision==1)).mappings().one()
    # Public HTTP was already protected; the finding concerns the DB proof guard.
    assert accept(client,f,request['id'],user=teacher,contact_id=verified['id']).status_code==403
    with pytest.raises(IntegrityError) as exc,transaction() as conn:
        proof_insert(conn,'institution_onboarding_consents',case_id=request['case_id'],revision=1,event_no=1,
            actor_id=teacher['user_id'],session_id=teacher['session_id'],auth_version=revision['target_auth_version'],decision='ACCEPT',
            contact_id=verified['id'],contact_digest=revision['target_contact_digest'],contact_verified_at=verified['verified_at'],expires_at=now()+timedelta(hours=24))
    assert exc.value.orig.sqlstate=='23514'
