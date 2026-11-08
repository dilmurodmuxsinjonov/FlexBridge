"""SQL-backed diary revisions; ownership is checked before any draft is written."""
from datetime import date
from uuid import uuid4
from sqlalchemy import select
from app.db.storage import table,transaction,now
from app.api.dependencies import owns_candidate,require_org,require_institution,ActorContext
from app.services.placements import get_row,insert_row,PlacementScopeError

class InternshipLogScopeError(Exception):
    def __init__(self,code,message='',status_code=409,sqlstate='23503',rejected_revision_id=None):
        super().__init__(message or code)
        self.code,self.status_code,self.sqlstate,self.rejected_revision_id=code,status_code,sqlstate,rejected_revision_id

class InternshipLogService:
    def create_mentor_assignment(self,*,placement_id,organization_id,mentor_id,actor_user_id):
        with transaction() as conn:
            p=get_row(conn,'placements',placement_id,True)
            if p['organization_id']!=organization_id: raise InternshipLogScopeError('MENTOR_ORG_MISMATCH')
            require_org(ActorContext(actor_user_id,'',()),organization_id,'OWNER','HOST_COORDINATOR')
            membership=conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==mentor_id,
                table('org_memberships').c.organization_id==organization_id,table('org_memberships').c.status=='ACTIVE',table('org_memberships').c.revoked_at.is_(None))).scalar_one_or_none()
            if not membership: raise InternshipLogScopeError('MENTOR_MEMBERSHIP_REQUIRED')
            return insert_row(conn,'mentor_assignments',placement_id=placement_id,organization_id=organization_id,membership_id=membership,
                assigned_by_id=actor_user_id,assigned_at=now())

    def create_academic_assignment(self,*,placement_id,institution_id,supervisor_id,supervision_id,actor_user_id):
        with transaction() as conn:
            require_institution(ActorContext(actor_user_id,'',()),institution_id,'COORDINATOR')
            membership=get_row(conn,'institution_memberships',supervisor_id)
            supervision=get_row(conn,'student_supervisions',supervision_id)
            placement=get_row(conn,'placements',placement_id)
            if membership['institution_id']!=institution_id or membership['status']!='ACTIVE' or membership['revoked_at']:
                raise InternshipLogScopeError('TEACHER_MEMBERSHIP_REQUIRED')
            if (supervision['institution_id']!=institution_id or supervision['enrollment_id']!=placement['enrollment_id']
                or supervision['status']!='ACTIVE' or supervision['revoked_at'] or not supervision['accepted_at']):
                raise InternshipLogScopeError('SUPERVISION_SCOPE_MISMATCH')
            return insert_row(conn,'academic_assignments',placement_id=placement_id,institution_id=institution_id,teacher_membership_id=supervisor_id,
                supervision_id=supervision_id,assigned_by_id=actor_user_id,assigned_at=now())

    def review(self,*,daily_log_id,placement_id,assignment_id,actor_user_id,decision,comment,academic=False):
        with transaction() as conn:
            log=get_row(conn,'daily_logs',daily_log_id,True)
            revision=get_row(conn,'log_revisions',log['current_revision_id'])
            assignment=get_row(conn,'academic_assignments' if academic else 'mentor_assignments',assignment_id)
            member=get_row(conn,'institution_memberships' if academic else 'org_memberships',assignment['teacher_membership_id' if academic else 'membership_id'])
            if (log['placement_id']!=placement_id or assignment['placement_id']!=placement_id or member['user_id']!=actor_user_id
                or member['status']!='ACTIVE' or member['revoked_at'] or assignment['revoked_at'] or not assignment['accepted_at']):
                raise InternshipLogScopeError('REVIEW_SCOPE_FORBIDDEN',status_code=403)
            if revision['status']!='SUBMITTED': raise InternshipLogScopeError('SUBMITTED_REVISION_REQUIRED')
            if decision not in ('APPROVED','REJECTED','CHANGES_REQUESTED'): raise InternshipLogScopeError('INVALID_REVIEW_DECISION',status_code=422)
            return insert_row(conn,'academic_log_reviews' if academic else 'workplace_log_reviews',revision_id=revision['id'],placement_id=placement_id,
                **{'academic_assignment_id' if academic else 'mentor_assignment_id':assignment_id},decision=decision,comment=comment,decided_at=now())

    def _owned(self,conn,placement_id,author_id):
        try: p=get_row(conn,'placements',placement_id,True)
        except PlacementScopeError: raise InternshipLogScopeError('PLACEMENT_NOT_FOUND',status_code=404)
        if not owns_candidate(author_id,p['candidate_id']): raise InternshipLogScopeError('PLACEMENT_AUTHOR_FORBIDDEN',status_code=403)
        if p['status']!='ACTIVE': raise InternshipLogScopeError('ACTIVE_PLACEMENT_REQUIRED')
        if not p['current_terms_id']: raise InternshipLogScopeError('PLACEMENT_TERMS_REQUIRED')
        return p

    def get_log(self,log_id):
        with transaction() as conn:
            try: row=get_row(conn,'daily_logs',log_id)
            except PlacementScopeError: return None
            rev=get_row(conn,'log_revisions',row['current_revision_id'])
            return {**row,'author_id':rev['author_id'],'log_date':row['local_date'].isoformat(),'status':rev['status']}

    def save_draft_daily_log_api_054(self,*,placement_id,author_id,log_date,summary_text,total_minutes=240,day_type='WORKED',tasks=None):
        with transaction() as conn:
            p=self._owned(conn,placement_id,author_id)
            terms=get_row(conn,'placement_terms',p['current_terms_id'])
            local_date=date.fromisoformat(str(log_date))
            if not p['start_date']<=local_date<=min(p['end_date'],date.today()): raise InternshipLogScopeError('INVALID_LOG_DATE',status_code=422)
            if day_type not in ('WORKED','ABSENT') or not 0<=total_minutes<=min(480,terms['daily_limit_minutes']) or (day_type=='ABSENT' and total_minutes):
                raise InternshipLogScopeError('INVALID_DAILY_LOG_MINUTES',status_code=422)
            t=table('daily_logs')
            old=conn.execute(select(t).where(t.c.placement_id==placement_id,t.c.local_date==local_date).with_for_update()).mappings().first()
            if old:
                previous=get_row(conn,'log_revisions',old['current_revision_id'])
                if previous['status']!='DRAFT': raise InternshipLogScopeError('SUBMITTED_LOG_IMMUTABLE')
                log=dict(old); version=old['version']+1
            else:
                log=insert_row(conn,'daily_logs',placement_id=placement_id,local_date=local_date,version=1); version=1
            revision=insert_row(conn,'log_revisions',daily_log_id=log['id'],revision=version,terms_id=p['current_terms_id'],author_id=author_id,
                day_type=day_type,summary=summary_text,total_minutes=total_minutes,status='DRAFT',idempotency_key=str(uuid4()))
            entries=tasks if tasks else ([{'minutes':total_minutes,'title':summary_text or 'Daily work'}] if total_minutes else [])
            if sum(e['minutes'] for e in entries)!=total_minutes: raise InternshipLogScopeError('TASK_MINUTES_MISMATCH',status_code=422)
            for e in entries:
                insert_row(conn,'log_task_entries',revision_id=revision['id'],result_text=e['title'],minutes=e['minutes'],start_minute=e.get('start_minute'),end_minute=e.get('end_minute'))
            conn.execute(t.update().where(t.c.id==log['id']).values(current_revision_id=revision['id'],version=version,updated_at=now()))
            return {'contract_id':'API-054',**log,'current_revision_id':revision['id'],'version':version,'status':'DRAFT','log_date':local_date.isoformat()}

    def submit_daily_log_api_056(self,*,placement_id,author_id,log_date,log_id=None):
        with transaction() as conn:
            self._owned(conn,placement_id,author_id)
            row=get_row(conn,'daily_logs',log_id,True)
            if row['placement_id']!=placement_id: raise InternshipLogScopeError('LOG_PLACEMENT_MISMATCH')
            rev=get_row(conn,'log_revisions',row['current_revision_id'],True)
            if rev['author_id']!=author_id: raise InternshipLogScopeError('LOG_AUTHOR_FORBIDDEN',status_code=403)
            if rev['status']!='DRAFT': raise InternshipLogScopeError('LOG_NOT_DRAFT')
            if rev['day_type']=='WORKED' and not 1<=rev['total_minutes']<=480: raise InternshipLogScopeError('INVALID_SUBMIT_LOG_MINUTES',status_code=422)
            conn.execute(table('log_revisions').update().where(table('log_revisions').c.id==rev['id']).values(status='SUBMITTED',submitted_at=now(),updated_at=now()))
            return {'contract_id':'API-056',**row,'status':'SUBMITTED'}

    def create_daily_log_with_revision(self,**kwargs):
        with transaction():
            draft=self.save_draft_daily_log_api_054(**kwargs)
            return self.submit_daily_log_api_056(placement_id=kwargs['placement_id'],author_id=kwargs['author_id'],log_date=kwargs['log_date'],log_id=draft['id'])

internship_log_service=InternshipLogService()
