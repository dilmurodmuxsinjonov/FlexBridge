"""HTTP grant replacement cannot revive intent; persisted quorum and immutable proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from test_owner_continuity import setup_continuity,submit,claim,decide,ready
from test_owner_continuity_security import platform_grant
from test_owner_additions import ready as addition_ready,has_owner
from test_owner_grant_boundaries import revoke,rejoin_staff
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import decide as addition_decide

def new_ready(client,flow):
    response=submit(client,flow,key='new-explicit-continuity-intent');assert response.status_code==202,response.text
    case=response.json()['id']
    for stage in ('moderator','compliance'):
        response=claim(client,flow,case,stage);assert response.status_code==200,response.text
        if stage=='moderator':
            response=decide(client,flow,case,stage);assert response.status_code==200,response.text
    return case

def test_staff_revoke_and_fresh_invite_requires_new_self_request(client,setup_continuity):
    flow=setup_continuity;case=ready(client,flow)
    revoke(client,flow['owner'],flow['org'],flow['member'])
    rejoin_staff(client,flow['owner'],flow['applicant'],flow['org'],flow['contact'])
    response=decide(client,flow,case,'compliance')
    assert response.status_code==200 and response.json()['status']=='EXPIRED',response.text
    assert not has_owner(flow['member'])
    fresh=new_ready(client,flow);response=decide(client,flow,fresh,'compliance')
    assert response.status_code==200 and response.json()['status']=='APPROVED',response.text
    assert has_owner(flow['member'])

def test_same_owner_memberships_with_fresh_owner_grant_do_not_match_old_roster(client,setup_continuity,identities):
    flow=setup_continuity;other_owner=identities('OWNER',flow['org'])
    verified=contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL')
    case=ready(client,flow)
    revoke(client,other_owner,flow['org'],flow['owner_member'])
    rejoin_staff(client,other_owner,flow['owner'],flow['org'],verified)
    restoring={**flow,'owner':other_owner,'target':flow['owner'],'target_member':flow['owner_member'],
        'moderator':flow['moderator'],'file':cv_fixture(other_owner),'contact':verified}
    restored=addition_ready(client,restoring);response=addition_decide(client,flow['moderator'],restored)
    assert response.status_code==200 and has_owner(flow['owner_member']),response.text
    response=decide(client,flow,case,'compliance')
    assert response.status_code==200 and response.json()['status']=='EXPIRED',response.text
    assert not has_owner(flow['member'])
    fresh=new_ready(client,flow);response=decide(client,flow,fresh,'compliance')
    assert response.status_code==200 and response.json()['status']=='APPROVED',response.text

@pytest.mark.parametrize('stage',['moderator','compliance'])
def test_replaced_platform_grant_does_not_revive_original_stage_claim(client,setup_continuity,stage):
    flow=setup_continuity;case=ready(client,flow);user=flow[stage]
    with transaction() as conn:
        grants=table('platform_role_grants')
        old=conn.execute(select(grants.c.id).where(grants.c.user_id==user['user_id'],grants.c.revoked_at.is_(None))).scalar_one()
        conn.execute(grants.update().where(grants.c.id==old).values(revoked_at=now()))
    new=platform_grant(user,stage.upper(),flow['compliance' if stage=='moderator' else 'moderator'])
    assert new['id']!=old
    response=decide(client,flow,case,stage)
    assert response.status_code==200 and response.json()['status']=='EXPIRED',response.text
    assert 'decisions' not in response.json() and not has_owner(flow['member'])
    fresh=new_ready(client,flow);response=decide(client,flow,fresh,'compliance')
    assert response.status_code==200 and response.json()['status']=='APPROVED',response.text

def test_quorum_and_tracking_receipt_survive_second_python_process(client,setup_continuity):
    flow=setup_continuity;case=ready(client,flow);response=decide(client,flow,case,'compliance')
    assert response.status_code==200 and response.json()['status']=='APPROVED',response.text
    user=flow['applicant'];env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    code="from app.api.dependencies import ActorContext;from app.services.owner_continuity import owner_continuity_service;import sys,json;r=owner_continuity_service.read(ActorContext(sys.argv[1],sys.argv[2],()),sys.argv[3]);print(json.dumps({'id':r['id'],'status':r['status'],'actions':sorted(d['action'] for d in r['decisions'])}))"
    child=subprocess.run([sys.executable,'-c',code,user['user_id'],user['session_id'],case],env=env,capture_output=True,text=True,check=True)
    assert json.loads(child.stdout)=={'id':case,'status':'APPROVED','actions':['APPROVE','RECOMMEND']}
    # This proves service/DB persistence with session UUID metadata, not bearer transport authentication.

def test_request_stage_proof_and_terminal_tracking_identity_cannot_be_rewritten(client,setup_continuity):
    flow=setup_continuity;case=ready(client,flow);response=decide(client,flow,case,'compliance')
    assert response.status_code==200,response.text
    targets=[('owner_continuity_requests','case_id',case,{'staff_grant_id':str(uuid4())}),
        ('owner_continuity_events','case_id',case,{'authority_grant_id':str(uuid4())}),
        ('verification_cases','id',case,{'current_revision':2}),
        ('recovery_requests','user_id',flow['applicant']['user_id'],{'kind':'ACCOUNT_ACCESS'}),
        ('org_ownership_events','id',response.json()['ownership_event_id'],{'effective_at':now()})]
    for name,key,value,changes in targets:
        target=table(name)
        with pytest.raises(IntegrityError) as failure,transaction() as conn:
            conn.execute(target.update().where(target.c[key]==value).values(**changes))
        assert failure.value.orig.sqlstate=='23514'
        with pytest.raises(IntegrityError),transaction() as conn:conn.execute(target.delete().where(target.c[key]==value))

def test_status_updates_without_moderator_proof_roll_back_together(client,setup_continuity):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    with pytest.raises(IntegrityError) as failure,transaction() as conn:
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case).values(status='WAITING_COMPLIANCE'))
        conn.execute(table('recovery_requests').update().where(table('recovery_requests').c.user_id==flow['applicant']['user_id']).values(status='WAITING_COMPLIANCE'))
    assert failure.value.orig.sqlstate=='23514'
    with transaction() as conn:
        assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='WAITING_MODERATOR'
        assert conn.execute(select(table('recovery_requests').c.status)).scalar_one()=='WAITING_MODERATOR'

def test_account_recovery_proof_cannot_read_continuity_tracking(client,setup_continuity):
    from app.core.iam_security import issue_continuation
    from app.services.identity import identity_service
    from app.services.auth import AuthError
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    with transaction() as conn:
        rid=conn.execute(select(table('owner_continuity_requests').c.recovery_id).where(table('owner_continuity_requests').c.case_id==case)).scalar_one()
        # Trusted misrouting fixture: no public continuity endpoint issues an account proof.
        token=issue_continuation(conn,'RECOVERY_STATUS',user_id=flow['applicant']['user_id'],payload={'request_id':rid},ttl=300)
    with pytest.raises(AuthError) as failure:identity_service.recovery_status(request_id=rid,recovery_token=token)
    assert failure.value.code=='INVALID_OR_EXPIRED_PROOF'
