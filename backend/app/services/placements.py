"""Persistent applications and independent, organization-scoped confirmations."""
from datetime import date, timedelta
from uuid import uuid4
from sqlalchemy import select
from app.db.storage import table, transaction, now
from app.api.dependencies import ActorContext, require_org, owns_candidate

class PlacementScopeError(Exception):
    def __init__(self, code, message='', status_code=409, sqlstate='23503'):
        super().__init__(message or code)
        self.code,self.status_code,self.sqlstate=code,status_code,sqlstate

def actor(user): return ActorContext(user,'',())

def get_row(conn,name,key,lock=False):
    t=table(name); q=select(t).where(t.c.id==key)
    row=conn.execute(q.with_for_update() if lock else q).mappings().first()
    if not row: raise PlacementScopeError(name.upper()+'_NOT_FOUND',status_code=404)
    return dict(row)

def insert_row(conn,name,**values):
    record={'id':str(uuid4()),'created_at':now(),'updated_at':now(),**values}
    conn.execute(table(name).insert().values(**record)); return record


def require_internship_placement(conn,placement):
    """A job engagement never acquires diary rights through a placement row."""
    offer=get_row(conn,'offers',placement['offer_id'])
    application=get_row(conn,'applications',placement['application_id'])
    revision=get_row(conn,'opportunity_revisions',offer['revision_id'])
    opportunity=get_row(conn,'opportunities',revision['opportunity_id'])
    if (opportunity['kind']!='INTERNSHIP' or revision['contract_type'] not in ('INTERNSHIP_AGREEMENT','ACADEMIC_TRIPARTITE')
        or offer['application_id']!=application['id'] or application['opportunity_id']!=opportunity['id']
        or application['candidate_id']!=placement['candidate_id'] or opportunity['organization_id']!=placement['organization_id']):
        raise PlacementScopeError('INTERNSHIP_PLACEMENT_REQUIRED',status_code=404)
    return opportunity,offer,revision

class ApplicationPlacementService:
    def create_application(self,*,opportunity_id,candidate_id,actor_user_id):
        with transaction() as conn:
            if not owns_candidate(actor_user_id,candidate_id): raise PlacementScopeError('CANDIDATE_SCOPE_FORBIDDEN',status_code=403)
            opp=get_row(conn,'opportunities',opportunity_id,True)
            if opp['status']!='PUBLISHED' or (opp['expires_at'] and opp['expires_at']<=now()):
                raise PlacementScopeError('OPPORTUNITY_NOT_OPEN')
            return insert_row(conn,'applications',opportunity_id=opportunity_id,candidate_id=candidate_id,status='SUBMITTED',version=1)

    def create_application_attempt(self,*,application_id,opportunity_id,attempt_no=1,actor_user_id):
        with transaction() as conn:
            app=get_row(conn,'applications',application_id,True)
            if not owns_candidate(actor_user_id,app['candidate_id']): raise PlacementScopeError('CANDIDATE_SCOPE_FORBIDDEN',status_code=403)
            if app['opportunity_id']!=opportunity_id: raise PlacementScopeError('APPLICATION_SCOPE_MISMATCH')
            opp=get_row(conn,'opportunities',opportunity_id)
            return insert_row(conn,'application_attempts',application_id=application_id,opportunity_id=opportunity_id,attempt_no=attempt_no,
                revision_id=opp['current_revision_id'],profile_snapshot={'candidate_id':app['candidate_id']},schedule_result='UNKNOWN',
                matching_version='1.4.0',submitted_at=now(),idempotency_key=str(uuid4()))

    def create_offer(self,*,application_id,opportunity_id,candidate_id,offered_by):
        with transaction() as conn:
            app=get_row(conn,'applications',application_id,True)
            if app['opportunity_id']!=opportunity_id or app['candidate_id']!=candidate_id: raise PlacementScopeError('OFFER_SCOPE_MISMATCH')
            opp=get_row(conn,'opportunities',opportunity_id)
            require_org(actor(offered_by),opp['organization_id'],'OWNER','HR','HOST_COORDINATOR')
            membership=conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.organization_id==opp['organization_id'],
                table('org_memberships').c.user_id==offered_by,table('org_memberships').c.status=='ACTIVE',table('org_memberships').c.revoked_at.is_(None))).scalar_one()
            attempt=conn.execute(select(table('application_attempts')).where(table('application_attempts').c.application_id==application_id)
                .order_by(table('application_attempts').c.attempt_no.desc()).limit(1)).mappings().first()
            if not attempt: raise PlacementScopeError('APPLICATION_ATTEMPT_REQUIRED')
            return insert_row(conn,'offers',application_id=application_id,attempt_id=attempt['id'],revision_id=attempt['revision_id'],
                issuer_membership_id=membership,terms_snapshot={'opportunity_id':opportunity_id},status='PENDING',
                expires_at=now()+timedelta(days=7),idempotency_key=str(uuid4()))

    def respond_to_offer_api_043(self,*,offer_id,candidate_id,decision):
        with transaction() as conn:
            offer=get_row(conn,'offers',offer_id,True); app=get_row(conn,'applications',offer['application_id'])
            if app['candidate_id']!=candidate_id: raise PlacementScopeError('OFFER_ACTOR_MISMATCH',status_code=403)
            if decision not in ('ACCEPT','DECLINE'): raise PlacementScopeError('INVALID_DECISION',status_code=422)
            if offer['status']!='PENDING' or offer['expires_at']<=now(): raise PlacementScopeError('OFFER_NOT_PENDING')
            values={'status':'ACCEPTED' if decision=='ACCEPT' else 'DECLINED','accepted_at':now() if decision=='ACCEPT' else None,'updated_at':now()}
            conn.execute(table('offers').update().where(table('offers').c.id==offer_id).values(**values))
            return {'contract_id':'API-043',**offer,**values}

    def create_placement(self,*,application_id,offer_id,opportunity_id,candidate_id,organization_id,actor,start_date=None,end_date=None):
        from app.services.authority import account_authority,org_authority
        from app.services.organizations import require_capability
        with transaction() as conn:
            get_row(conn,'organizations',organization_id,True)
            offer=get_row(conn,'offers',offer_id,True); app=get_row(conn,'applications',application_id); opp=get_row(conn,'opportunities',opportunity_id)
            revision=get_row(conn,'opportunity_revisions',offer['revision_id'])
            account_authority(conn,actor)
            org_authority(conn,actor.user_id,organization_id,'OWNER','HOST_COORDINATOR')
            if (offer['application_id']!=application_id or app['opportunity_id']!=opportunity_id or app['candidate_id']!=candidate_id
                or opp['organization_id']!=organization_id or revision['opportunity_id']!=opportunity_id):
                raise PlacementScopeError('PLACEMENT_SCOPE_MISMATCH')
            if opp['kind']!='INTERNSHIP' or revision['contract_type'] not in ('INTERNSHIP_AGREEMENT','ACADEMIC_TRIPARTITE'):
                raise PlacementScopeError('INTERNSHIP_PLACEMENT_REQUIRED',status_code=409)
            require_capability(conn,organization_id,'INTERNSHIP_HOST')
            if offer['status']!='ACCEPTED': raise PlacementScopeError('OFFER_NOT_ACCEPTED')
            start=start_date or date.today(); end=end_date or start+timedelta(days=90)
            p=insert_row(conn,'placements',application_id=application_id,offer_id=offer_id,candidate_id=candidate_id,organization_id=organization_id,
                academic_track=False,status='PENDING_START_CONFIRMATION',start_date=start,end_date=end,version=1)
            terms=insert_row(conn,'placement_terms',placement_id=p['id'],version=1,schema_version=1,terms_snapshot=offer['terms_snapshot'],
                daily_limit_minutes=480,weekly_limit_minutes=2400,required_minutes=0)
            conn.execute(table('placements').update().where(table('placements').c.id==p['id']).values(current_terms_id=terms['id']))
            return {**p,'current_terms_id':terms['id']}

    def _party(self,conn,candidate_id,org_id,user_id,party):
        if owns_candidate(user_id,candidate_id):
            if party not in (None,'CANDIDATE'): raise PlacementScopeError('ENGAGEMENT_ACTOR_FORBIDDEN',status_code=403)
            return 'CANDIDATE'
        require_org(actor(user_id),org_id,'OWNER','HR','HOST_COORDINATOR')
        if party not in (None,'ORGANIZATION','EMPLOYER'): raise PlacementScopeError('ENGAGEMENT_ACTOR_FORBIDDEN',status_code=403)
        return 'EMPLOYER'

    def confirm_placement_start(self,*,placement_id,party=None,actor_user_id):
        with transaction() as conn:
            p=get_row(conn,'placements',placement_id,True)
            side=self._party(conn,p['candidate_id'],p['organization_id'],actor_user_id,party)
            if p['status'] not in ('PENDING_START_CONFIRMATION','ACTIVE'): raise PlacementScopeError('PLACEMENT_NOT_CONFIRMABLE')
            terms=get_row(conn,'placement_terms',p['current_terms_id'],True)
            column='candidate_accepted_at' if side=='CANDIDATE' else 'host_accepted_at'
            if terms[column] is None:
                conn.execute(table('placement_terms').update().where(table('placement_terms').c.id==terms['id']).values(**{column:now()}))
                terms[column]=now()
                insert_row(conn,'placement_decisions',placement_id=placement_id,actor_id=actor_user_id,side=side,decision='CONFIRM_START',terms_id=terms['id'],decided_at=now())
            if terms['candidate_accepted_at'] and terms['host_accepted_at']:
                conn.execute(table('placements').update().where(table('placements').c.id==placement_id).values(status='ACTIVE',updated_at=now()))
            return get_row(conn,'placements',placement_id)

    def confirm_engagement_by_actor_api_046(self,*,placement_id,actor_user_id,actor_roles=(),party=None,action='CONFIRM_START'):
        # Canonical engagement IDs refer to job_engagements, never arbitrary placement IDs.
        with transaction() as conn:
            engagement=get_row(conn,'job_engagements',placement_id,True)
            app=get_row(conn,'applications',engagement['application_id']); opp=get_row(conn,'opportunities',app['opportunity_id'])
            side=self._party(conn,app['candidate_id'],opp['organization_id'],actor_user_id,party)
            if engagement['status'] not in ('PENDING_START_CONFIRMATION','ACTIVE','DISPUTED'): raise PlacementScopeError('ENGAGEMENT_NOT_CONFIRMABLE')
            if action not in ('CONFIRM_START','DISPUTE_START'): raise PlacementScopeError('INVALID_ACTION',status_code=422)
            t=table('engagement_confirmations')
            previous=conn.execute(select(t.c.id).where(t.c.engagement_id==placement_id,t.c.side==side,t.c.action==action)).first()
            if not previous: insert_row(conn,'engagement_confirmations',engagement_id=placement_id,user_id=actor_user_id,side=side,action=action,response=action,occurred_at=now())
            decisions=list(conn.execute(select(t).where(t.c.engagement_id==placement_id)).mappings())
            status='DISPUTED' if any(d['action']=='DISPUTE_START' for d in decisions) else ('ACTIVE' if {d['side'] for d in decisions if d['action']=='CONFIRM_START'}=={'CANDIDATE','EMPLOYER'} else 'PENDING_START_CONFIRMATION')
            conn.execute(table('job_engagements').update().where(table('job_engagements').c.id==placement_id).values(status=status,confirmed_started_at=now() if status=='ACTIVE' else None,updated_at=now()))
            return {'contract_id':'API-046',**engagement,'status':status}

placement_service=ApplicationPlacementService()
