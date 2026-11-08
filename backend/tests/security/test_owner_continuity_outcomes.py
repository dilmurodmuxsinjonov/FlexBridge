"""Terminal reviewer outcomes and account-reset isolation remain durable and scoped."""
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction
from test_owner_continuity import setup_continuity,submit,claim,decide,recommended
from test_owner_additions import has_owner

@pytest.mark.parametrize('stage,decision',[('moderator','REJECT'),('compliance','REJECT'),('compliance','NEEDS_INFO')])
def test_negative_stage_outcome_closes_tracking_and_audit_without_owner(client,setup_continuity,stage,decision):
    flow=setup_continuity
    if stage=='moderator':
        response=submit(client,flow);assert response.status_code==202,response.text
        case=response.json()['id']
    else:case=recommended(client,flow)
    response=claim(client,flow,case,stage);assert response.status_code==200,response.text
    response=decide(client,flow,case,stage,decision)
    expected='REJECTED' if decision=='REJECT' else 'NEEDS_INFO'
    assert response.status_code==200 and response.json()['status']==expected,response.text
    assert not has_owner(flow['member']) and has_owner(flow['owner_member'])
    with transaction() as conn:
        assert conn.execute(select(table('recovery_requests').c.status)).scalar_one()==expected
        audit=table('audit_events')
        assert conn.execute(select(func.count()).select_from(audit).where(audit.c.object_key==case,audit.c.action=='OWNER_CONTINUITY_'+decision)).scalar_one()==1
    repeat=decide(client,flow,case,stage,decision)
    assert repeat.status_code==200 and repeat.json()['idempotent_replay'],repeat.text

def test_account_reset_proof_for_continuity_cannot_change_credentials_or_security(client,setup_continuity):
    from app.core.iam_security import issue_continuation
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];uid=flow['applicant']['user_id']
    with transaction() as conn:
        request=conn.execute(select(table('owner_continuity_requests')).where(table('owner_continuity_requests').c.case_id==case)).mappings().one()
        user=conn.execute(select(table('users').c.password_hash,table('users').c.auth_version).where(table('users').c.id==uid)).mappings().one()
        before=dict(user)
        token=issue_continuation(conn,'RECOVERY_RESET',user_id=uid,payload={
            'request_id':request['recovery_id'],'contact_id':flow['contact']['id'],'auth_version':user['auth_version']},ttl=300)
        rid=request['recovery_id']
    # Trusted misrouting fixture; continuity never issues account reset tokens over its API.
    response=client.post('/api/v1/auth/recovery/'+rid+'/complete',json={
        'reset_token':token,'new_password':'different-strong-passphrase-2026'})
    assert response.status_code in (400,401,403) and response.json()['detail']['code']=='INVALID_OR_EXPIRED_PROOF',response.text
    with transaction() as conn:
        after=dict(conn.execute(select(table('users').c.password_hash,table('users').c.auth_version).where(table('users').c.id==uid)).mappings().one())
        assert after==before
        assert conn.execute(select(table('recovery_requests').c.status).where(table('recovery_requests').c.id==rid)).scalar_one()=='WAITING_MODERATOR'
    assert not has_owner(flow['member'])
