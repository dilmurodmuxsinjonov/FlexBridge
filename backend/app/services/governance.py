"""Durable membership approval and independent moderation decisions."""
from datetime import timedelta
from sqlalchemy import select
from app.db.storage import table,transaction,now,save_domain_record,load_domain_record
from app.core.audit import AppendOnlyAuditStore
from app.api.dependencies import ActorContext,require_org,require_platform
from app.services.placements import get_row,insert_row

class GovernanceError(Exception):
    def __init__(self,code,message='',status_code=409):
        super().__init__(message or code);self.code,self.status_code=code,status_code

class GovernanceScopeService:
    audit_store=AppendOnlyAuditStore()

    def create_org_member_request(self,*,actor,organization_id,user_id,role_code):
        from app.services.authority import mfa_authority,org_authority
        if role_code not in ('HR','HOST_COORDINATOR','MENTOR','BILLING'):
            raise GovernanceError('OWNERSHIP_REQUIRES_INDEPENDENT_VERIFICATION',status_code=422)
        with transaction() as conn:
            get_row(conn,'organizations',organization_id,True)
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,organization_id,'OWNER')
            role=conn.execute(select(table('role_catalog')).where(table('role_catalog').c.code==role_code,
                table('role_catalog').c.scope_kind=='ORG')).mappings().first()
            if not role: raise GovernanceError('INVALID_ORG_ROLE',status_code=422)
            row=insert_row(conn,'org_memberships',organization_id=organization_id,user_id=user_id,status='PENDING_APPROVAL')
            save_domain_record('membership_requests',row['id'],{'created_by':actor.user_id,'role_id':role['id']})
            return row

    def approve_org_member(self,*,actor,organization_id,member_id,approver_org_id):
        from app.services.authority import mfa_authority,org_authority
        with transaction() as conn:
            org=get_row(conn,'organizations',organization_id,True)
            row=get_row(conn,'org_memberships',member_id,True)
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,organization_id,'OWNER')
            if org['status']!='VERIFIED': raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            request=load_domain_record('membership_requests',member_id)
            if row['organization_id']!=organization_id or approver_org_id!=organization_id: raise GovernanceError('SCOPE_VIOLATION',status_code=403)
            if not request or row['status']!='PENDING_APPROVAL': raise GovernanceError('MEMBERSHIP_NOT_PENDING')
            if actor.user_id in (request['created_by'],row['user_id']): raise GovernanceError('SELF_APPROVAL_FORBIDDEN')
            if request.get('origin')=='SELF_JOIN':
                from app.services.organizations import evidence_files
                evidence_files(conn,row['user_id'],request['evidence_file_ids'])
            role=get_row(conn,'role_catalog',request['role_id'])
            if role['scope_kind']!='ORG' or role['code'] not in ('HR','HOST_COORDINATOR','MENTOR','BILLING'):
                raise GovernanceError('OWNERSHIP_REQUIRES_INDEPENDENT_VERIFICATION',status_code=422)
            conn.execute(table('org_memberships').update().where(table('org_memberships').c.id==member_id).values(status='ACTIVE',accepted_at=now(),updated_at=now()))
            insert_row(conn,'org_role_grants',membership_id=member_id,role_id=request['role_id'],granted_by_id=actor.user_id)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ORG_MEMBER_APPROVED_DUAL_CONTROL',entity_type='membership',entity_id=member_id)
            return {**row,'status':'ACTIVE'}

    def record_moderation_action(self,*,actor_id,target_entity_type,target_entity_id,action_type,policy_code,reason_code,justification):
        with transaction() as conn:
            require_platform(ActorContext(actor_id,'',()),'MODERATOR')
            if target_entity_type not in ('opportunity','opportunities') or action_type not in ('APPROVE','REJECT'):
                raise GovernanceError('UNSUPPORTED_MODERATION_ACTION',status_code=422)
            if not policy_code.strip() or not reason_code.strip() or len(justification.strip())<15:
                raise GovernanceError('MODERATION_JUSTIFICATION_REQUIRED',status_code=422)
            opp=get_row(conn,'opportunities',target_entity_id,True)
            revision=get_row(conn,'opportunity_revisions',opp['current_revision_id'])
            if revision['author_id']==actor_id: raise GovernanceError('SELF_MODERATION_FORBIDDEN',status_code=403)
            if opp['status']!='DRAFT': raise GovernanceError('MODERATION_STATE_CONFLICT')
            case=insert_row(conn,'moderation_cases',reporter_id=actor_id,opportunity_id=opp['id'],category=policy_code,status='RESOLVED',
                severity='LOW',assigned_to_id=actor_id,due_at=now()+timedelta(hours=48))
            result=insert_row(conn,'moderation_actions',case_id=case['id'],actor_id=actor_id,action=action_type,
                reason=reason_code+': '+justification,occurred_at=now())
            conn.execute(table('opportunities').update().where(table('opportunities').c.id==opp['id']).values(status='APPROVED' if action_type=='APPROVE' else 'REJECTED',updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor_id,action='MODERATION_'+action_type,entity_type='opportunity',entity_id=opp['id'],metadata={'case_id':case['id']})
            return result

governance_service=GovernanceScopeService()
