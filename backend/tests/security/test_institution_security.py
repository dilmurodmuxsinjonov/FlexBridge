"""No grant from stale intent, changed document/identity or unauthorized actors."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
from threading import Event
from time import monotonic
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,get_engine,now
from app.services.placements import insert_row
from app.services.institution_onboarding import institution_onboarding_service as service
from test_candidate import cv_fixture
from test_institution_onboarding import first_claim,submit,accept,claim,decide,active_coordinator,staff_claim
from test_institution_transactions import business_snapshot
from test_regressions import count
from test_org_authority_transactions import wait_for_blocker


@pytest.mark.parametrize('change',['file_hash','file_version','agreement_purpose','institution_identity','requester_security','target_contact'])
def test_changed_pending_proof_cannot_activate_first_coordinator(client,identities,change):
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    appointment,case=r.json()['id'],r.json()['case_id'];moderator=identities('MODERATOR')
    assert accept(client,f,appointment).status_code==200
    assert claim(client,moderator,case).status_code==200
    with transaction() as conn:
        if change in ('file_hash','file_version'):
            t=table('files');values={'sha256':'b'*64} if change=='file_hash' else {'object_version':'different-object-version','storage_version_id':'different-object-version'}
            conn.execute(t.update().where(t.c.id==f['document']['id']).values(**values))
        elif change=='agreement_purpose':
            t=table('institution_agreements');conn.execute(t.update().values(purposes={'ACADEMIC_VIEW':False}))
        elif change=='institution_identity':
            t=table('institutions');conn.execute(t.update().values(name='Different institution identity'))
        elif change=='requester_security':
            t=table('users');conn.execute(t.update().where(t.c.id==f['user']['user_id']).values(auth_version=t.c.auth_version+1))
        else:
            t=table('user_contacts');conn.execute(t.update().where(t.c.id==f['contact']['id']).values(verified_at=now()))
    before=business_snapshot();response=decide(client,moderator,case)
    assert response.status_code in (403,409),response.text
    assert business_snapshot()==before and count('institution_role_grants')==0


def test_replaced_coordinator_grant_cannot_authorize_old_teacher_proposal(client,identities):
    f=active_coordinator(client,identities);teacher=identities();proposal,verified,body=staff_claim(client,f,teacher)
    assert accept(client,f,proposal['id'],user=teacher,contact_id=verified['id']).status_code==200
    assert claim(client,f['moderator'],proposal['case_id']).status_code==200
    with transaction() as conn:
        grants=table('institution_role_grants');old=dict(conn.execute(select(grants)).mappings().one())
        conn.execute(grants.update().where(grants.c.id==old['id']).values(revoked_at=now()))
        # A distinct official appointment gives a fresh trusted coordinator grant;
        # this cannot revive the old proposal's pinned requester grant.
        appts=table('institution_appointments');appointment=dict(conn.execute(select(appts).where(appts.c.id==old['appointment_id'])).mappings().one())
        replacement={key:value for key,value in appointment.items() if key not in ('id','created_at','updated_at','verification_case_id')}
        fresh=insert_row(conn,'institution_appointments',**replacement)
        insert_row(conn,'institution_role_grants',membership_id=old['membership_id'],role_id=old['role_id'],appointment_id=fresh['id'])
    before=business_snapshot();denied=decide(client,f['moderator'],proposal['case_id'])
    assert denied.status_code==409,denied.text
    assert business_snapshot()==before
    # An explicit new revision is new intent: it must get a new independent
    # decision and named consent, rather than inheriting either old prerequisite.
    assert decide(client,f['moderator'],proposal['case_id'],'NEEDS_INFO').status_code==200
    revised=client.post('/api/v1/institution-appointments/'+proposal['id']+'/revisions',headers=f['user']['headers'],json={**body,'expected_revision':1})
    assert revised.status_code==202,revised.text
    assert accept(client,f,proposal['id'],user=teacher,contact_id=verified['id'],revision=2).status_code==200
    renewed=decide(client,f['moderator'],proposal['case_id'],revision=2);assert renewed.status_code==200,renewed.text
    assert renewed.json()['status']=='ACTIVE'


def test_expired_consent_needs_fresh_named_acceptance_and_not_a_new_review(client,identities,monkeypatch):
    from app.services import institution_onboarding as module
    monkeypatch.setattr(module,'CONSENT_LIFETIME',timedelta(milliseconds=100))
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    appointment,case=r.json()['id'],r.json()['case_id'];moderator=identities('MODERATOR')
    assert accept(client,f,appointment).status_code==200
    assert claim(client,moderator,case).status_code==200
    with transaction() as conn:expires=conn.execute(select(table('institution_onboarding_consents').c.expires_at)).scalar_one()
    deadline=monotonic()+2;tick=Event()
    while now()<expires:
        assert monotonic()<deadline,'Short consent did not expire on the real clock'
        tick.wait(.02)
    reviewed=decide(client,moderator,case);assert reviewed.status_code==200,reviewed.text
    assert reviewed.json()['status']=='APPROVED_PENDING_ACCEPT' and count('institution_role_grants')==0
    # Renew with an actual current session and the normal policy lifetime; no
    # timestamps, immutable proofs or application clocks are rewritten.
    monkeypatch.setattr(module,'CONSENT_LIFETIME',timedelta(hours=24))
    renewed=accept(client,f,appointment);assert renewed.status_code==200,renewed.text
    assert renewed.json()['status']=='ACTIVE' and count('institution_onboarding_consents')==2
    assert count('institution_onboarding_decisions')==1


def test_reappointment_creates_new_membership_instead_of_reactivating_revoked_history(client,identities):
    f=active_coordinator(client,identities);teacher=identities();first,verified,body=staff_claim(client,f,teacher)
    assert accept(client,f,first['id'],user=teacher,contact_id=verified['id']).status_code==200
    assert claim(client,f['moderator'],first['case_id']).status_code==200
    assert decide(client,f['moderator'],first['case_id']).status_code==200
    with transaction() as conn:
        members=table('institution_memberships');old=dict(conn.execute(select(members).where(members.c.user_id==teacher['user_id'])).mappings().one())
    revoked=client.post('/api/v1/institution-appointments/'+first['id']+'/revoke',headers=teacher['headers'],json={'reason':'Named teacher withdraws the first formal appointment'})
    assert revoked.status_code==200,revoked.text
    with transaction() as conn:
        stamp=now();conn.execute(members.update().where(members.c.id==old['id']).values(status='REVOKED',revoked_at=stamp))
    document=cv_fixture(f['user']);fresh_body={**body,'document_file_id':document['id'],'file_ids':[document['id']]}
    second=client.post('/api/v1/institution-appointments',headers={**f['user']['headers'],'Idempotency-Key':'new-teacher-appointment'},json=fresh_body)
    assert second.status_code==202,second.text
    data=second.json();assert accept(client,f,data['id'],user=teacher,contact_id=verified['id']).status_code==200
    assert claim(client,f['moderator'],data['case_id']).status_code==200
    accepted=decide(client,f['moderator'],data['case_id']);assert accepted.status_code==200,accepted.text
    with transaction() as conn:
        rows=[dict(row) for row in conn.execute(select(members).where(members.c.user_id==teacher['user_id'])).mappings()]
        historical=next(row for row in rows if row['id']==old['id']);current=next(row for row in rows if row['id']!=old['id'])
        assert historical['status']=='REVOKED' and historical['revoked_at']==stamp
        assert historical['accepted_at']==old['accepted_at']
        assert current['status']=='ACTIVE' and current['revoked_at'] is None and current['accepted_at'] is not None


def test_audit_failure_rolls_back_consent_and_activation(client,identities,monkeypatch):
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    appointment,case=r.json()['id'],r.json()['case_id'];moderator=identities('MODERATOR')
    assert claim(client,moderator,case).status_code==200
    assert decide(client,moderator,case).status_code==200
    before=business_snapshot()
    def fail(**kwargs):raise RuntimeError('Audit unavailable')
    monkeypatch.setattr(service.audit_store,'append_audit_event',fail)
    response=accept(client,f,appointment);assert response.status_code==503,response.text
    assert business_snapshot()==before and count('institution_role_grants')==0


def test_review_proof_rows_are_append_only_and_scoped(client,identities):
    f=active_coordinator(client,identities)
    for name in ('institution_onboarding_requests','institution_onboarding_submissions','institution_onboarding_consents','institution_onboarding_decisions'):
        t=table(name)
        for mutation in ('update','delete'):
            with pytest.raises(IntegrityError) as exc,transaction() as conn:
                if mutation=='update':conn.execute(t.update().values(created_at=now()))
                else:conn.execute(t.delete())
            assert exc.value.orig.sqlstate=='23514'


def test_registered_contact_cannot_be_silently_retargeted_to_another_user(client,identities):
    f=active_coordinator(client,identities);teacher=identities();proposal,verified,body=staff_claim(client,f,teacher)
    assert claim(client,f['moderator'],proposal['case_id']).status_code==200
    assert decide(client,f['moderator'],proposal['case_id'],'NEEDS_INFO').status_code==200
    stranger=identities()
    with transaction() as conn:
        contacts=table('user_contacts');conn.execute(contacts.update().where(contacts.c.id==verified['id']).values(user_id=stranger['user_id']))
    before=business_snapshot()
    response=client.post('/api/v1/institution-appointments/'+proposal['id']+'/revisions',headers=f['user']['headers'],json={**body,'expected_revision':1})
    assert response.status_code==403,response.text
    assert business_snapshot()==before


def test_current_sensitive_role_arriving_after_preflight_blocks_teacher_password_consent(client,identities,organization):
    f=active_coordinator(client,identities);teacher=identities();proposal,verified,body=staff_claim(client,f,teacher)
    before=count('institution_onboarding_consents')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(select(table('institutions')).where(table('institutions').c.id==f['institution_id']).with_for_update())
            pid=blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(lambda:accept(client,f,proposal['id'],user=teacher,contact_id=verified['id']));wait_for_blocker(pid)
            with transaction() as conn:
                roles=table('role_catalog');rid=conn.execute(select(roles.c.id).where(roles.c.code=='BILLING',roles.c.scope_kind=='ORG')).scalar_one()
                membership=insert_row(conn,'org_memberships',organization_id=organization,user_id=teacher['user_id'],status='ACTIVE',accepted_at=now())
                insert_row(conn,'org_role_grants',membership_id=membership['id'],role_id=rid,granted_by_id=f['user']['user_id'])
        response=pending.result(timeout=30)
    assert response.status_code==403,response.text
    assert count('institution_onboarding_consents')==before and count('institution_role_grants')==1
