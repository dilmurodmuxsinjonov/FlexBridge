"""Changed-input reproductions for the independent f844d53 peer review."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction,now,save_domain_record
from app.services.placements import insert_row


def test_generic_staff_creation_cannot_request_owner(client,identities,organization):
    owner=identities('OWNER',organization);target=identities()
    response=client.post('/api/v1/organizations/'+organization+'/members',headers=owner['headers'],
        json={'user_id':target['user_id'],'role_code':'OWNER'})
    assert response.status_code==422,response.text
    with transaction() as conn:
        assert not conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==target['user_id'])).first()


def test_legacy_pending_owner_request_cannot_be_approved(client,identities,organization):
    requester=identities('OWNER',organization);approver=identities('OWNER',organization);target=identities()
    with transaction() as conn:
        member=insert_row(conn,'org_memberships',organization_id=organization,user_id=target['user_id'],status='PENDING_APPROVAL')
        role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='OWNER')).scalar_one()
        save_domain_record('membership_requests',member['id'],{'created_by':requester['user_id'],'role_id':role})
    response=client.post('/api/v1/organizations/'+organization+'/members/'+member['id']+'/approve',
        headers=approver['headers'],json={})
    assert response.status_code==422,response.text
    with transaction() as conn:
        assert conn.execute(select(table('org_memberships').c.status).where(table('org_memberships').c.id==member['id'])).scalar_one()=='PENDING_APPROVAL'
        assert conn.execute(select(func.count()).select_from(table('org_role_grants')).where(
            table('org_role_grants').c.membership_id==member['id'])).scalar_one()==0


@pytest.mark.parametrize('role',['FINANCE','OWNER','BILLING'])
def test_financial_http_paths_reject_password_only_sensitive_sessions(client,identities,organization,role):
    # Grant a role after a normal PASSWORD session exists, without enrolling that user in MFA.
    user=identities();grantor=identities('FINANCE' if role=='FINANCE' else 'OWNER',None if role=='FINANCE' else organization)
    with transaction() as conn:
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code==role)).scalar_one()
        if role=='FINANCE':
            from datetime import timedelta
            insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=rid,
                granted_by_id=grantor['user_id'],expires_at=now()+timedelta(hours=1))
        else:
            member=insert_row(conn,'org_memberships',organization_id=organization,user_id=user['user_id'],status='ACTIVE')
            insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=rid,granted_by_id=grantor['user_id'])
    for _ in range(2):
        path='/api/v1/operator/refunds/'+str(uuid4())+'/approve' if role=='FINANCE' else '/api/v1/orders/'+str(uuid4())+'/refund-requests'
        body={} if role=='FINANCE' else {'amount_uzs':100,'reason':'Valid synthetic refund request'}
        response=client.post(path,headers=user['headers'],json=body)
        assert response.status_code==403,response.text
        assert response.json()['detail']['code']=='MFA_ENROLLMENT_REQUIRED'
