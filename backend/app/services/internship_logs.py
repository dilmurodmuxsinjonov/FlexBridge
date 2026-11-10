"""SQL-backed diary revisions; ownership is checked before any draft is written."""
from datetime import date
from uuid import uuid4
from sqlalchemy import select,text
from sqlalchemy.exc import OperationalError
from app.db.storage import table,transaction,now
from app.api.dependencies import owns_candidate,require_org,ActorContext
from app.services.placements import get_row,insert_row,PlacementScopeError,require_internship_placement
from app.core.audit import AppendOnlyAuditStore

class InternshipLogScopeError(Exception):
    def __init__(self,code,message='',status_code=409,sqlstate='23503',rejected_revision_id=None):
        super().__init__(message or code)
        self.code,self.status_code,self.sqlstate,self.rejected_revision_id=code,status_code,sqlstate,rejected_revision_id

class InternshipLogService:
    audit_store=AppendOnlyAuditStore()
    def create_mentor_assignment(self,*,placement_id,organization_id,mentor_id,actor,idempotency_key):
        from app.services.placement_admission import admission_service
        return admission_service.nominate_mentor(actor=actor,placement_id=placement_id,
            organization_id=organization_id,mentor_id=mentor_id,idempotency_key=idempotency_key)

    def _academic_binding(self,conn,placement,supervision,institution_id):
        from app.db.institution_scope import TASHKENT
        require_internship_placement(conn,placement)
        if (not placement['academic_track'] or placement['status']!='ACTIVE' or
            supervision['institution_id']!=institution_id or supervision['enrollment_id']!=placement['enrollment_id']
            or supervision['status']!='ACTIVE' or supervision['revoked_at'] or not supervision['accepted_at']
            or supervision['accepted_at']>now()):
            raise InternshipLogScopeError('SUPERVISION_SCOPE_MISMATCH',status_code=403)
        # These are business rows; acquire them before actor/session authority.
        enrollment=get_row(conn,'enrollments',supervision['enrollment_id'],True)
        agreement=get_row(conn,'institution_agreements',supervision['agreement_id'],True)
        today=now().astimezone(TASHKENT).date()
        purpose=supervision['purpose'];purposes=agreement['purposes']
        enabled=(purpose in purposes) if isinstance(purposes,list) else (isinstance(purposes,dict) and purposes.get(purpose) is True)
        if (enrollment['institution_id']!=institution_id or enrollment['candidate_id']!=placement['candidate_id'] or
            not conn.execute(text('SELECT flexbridge.academic_supervision_current(:s,:c)'),
                {'s':supervision['id'],'c':placement['candidate_id']}).scalar_one() or
            not conn.execute(text('SELECT flexbridge.enrollment_is_current(:id)'),{'id':enrollment['id']}).scalar_one() or
            enrollment['status']!='VERIFIED' or enrollment['start_date']>today or
            (enrollment['end_date'] is not None and enrollment['end_date']<today) or
            agreement['institution_id']!=institution_id or agreement['status']!='ACTIVE' or agreement['valid_from']>today or
            (agreement['valid_to'] is not None and agreement['valid_to']<today) or not enabled or not supervision['legal_basis'].strip()):
            raise InternshipLogScopeError('ACADEMIC_SCOPE_NOT_CURRENT',status_code=403)

    def _locked_academic_assignment(self,conn,assignment_id):
        from app.services.academic_admission import academic_service
        placement,_,supervision,assignment=academic_service.locked_assignment(conn,assignment_id)
        return placement,supervision,assignment

    def create_academic_assignment(self,*,actor,placement_id,institution_id,supervisor_id,supervision_id,idempotency_key):
        from app.services.academic_admission import academic_service
        return academic_service.nominate(actor=actor,placement_id=placement_id,institution_id=institution_id,
            supervisor_id=supervisor_id,supervision_id=supervision_id,idempotency_key=idempotency_key)

    def revoke_academic_assignment(self,actor,assignment_id):
        from app.services.academic_admission import academic_service
        return academic_service.revoke(actor,assignment_id)

    def review_academic(self,*,actor,daily_log_id,placement_id,assignment_id,decision,comment):
        from app.services.academic_admission import academic_service
        with transaction() as conn:
            placement,supervision,assignment=self._locked_academic_assignment(conn,assignment_id)
            log=get_row(conn,'daily_logs',daily_log_id,True)
            if placement['id']!=placement_id or log['placement_id']!=placement_id:
                raise InternshipLogScopeError('REVIEW_SCOPE_FORBIDDEN',status_code=403)
            self._academic_binding(conn,placement,supervision,assignment['institution_id'])
            revision=get_row(conn,'log_revisions',log['current_revision_id'],True)
            if not owns_candidate(revision['author_id'],placement['candidate_id']):
                raise InternshipLogScopeError('REVISION_AUTHOR_FORBIDDEN',status_code=403)
            authority=academic_service.teacher(conn,actor,placement,assignment)
            if (authority['id']!=assignment['teacher_membership_id'] or assignment['revoked_at'] or not assignment['accepted_at']
                or assignment['accepted_at']>now() or not conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),
                    {'a':assignment_id,'t':revision['terms_id']}).scalar_one()):
                raise InternshipLogScopeError('REVIEW_SCOPE_FORBIDDEN',status_code=403)
            if revision['author_id']==actor.user_id:raise InternshipLogScopeError('SELF_REVIEW_FORBIDDEN',status_code=403)
            if revision['status']!='SUBMITTED':raise InternshipLogScopeError('SUBMITTED_REVISION_REQUIRED')
            if decision not in ('APPROVED','REJECTED','CHANGES_REQUESTED'):
                raise InternshipLogScopeError('INVALID_REVIEW_DECISION',status_code=422)
            review=insert_row(conn,'academic_log_reviews',revision_id=revision['id'],placement_id=placement_id,
                academic_assignment_id=assignment_id,decision=decision,comment=comment,decided_at=now())
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ACADEMIC_LOG_REVIEWED',entity_type='academic_log_review',entity_id=review['id'])
            return review

    def review(self,*,daily_log_id,placement_id,assignment_id,actor,decision,comment,academic=False):
        if academic:raise InternshipLogScopeError('ACADEMIC_USE_SCOPED_SERVICE',status_code=422)
        from app.services.placement_admission import admission_service
        with transaction() as conn:
            placement,_=admission_service._locked(conn,placement_id)
            log=get_row(conn,'daily_logs',daily_log_id,True)
            revision=get_row(conn,'log_revisions',log['current_revision_id'],True)
            assignment=get_row(conn,'mentor_assignments',assignment_id,True)
            if (placement['status']!='ACTIVE' or log['placement_id']!=placement_id or assignment['placement_id']!=placement_id
                or assignment['revoked_at'] or not assignment['accepted_at'] or revision['author_id']==actor.user_id):
                raise InternshipLogScopeError('REVIEW_SCOPE_FORBIDDEN',status_code=403)
            admission_service._mentor(conn,actor,placement,assignment)
            proof=table('mentor_assignment_proofs');consent=table('placement_consents')
            origin=conn.execute(select(proof.c.origin).where(proof.c.assignment_id==assignment_id)).scalar_one()
            if origin=='PUBLIC' and not conn.execute(select(consent.c.id).where(consent.c.assignment_id==assignment_id,
                consent.c.terms_id==revision['terms_id'],consent.c.side=='MENTOR')).first():
                raise InternshipLogScopeError('MENTOR_PLAN_ACCEPTANCE_REQUIRED',status_code=403)
            if revision['status']!='SUBMITTED': raise InternshipLogScopeError('SUBMITTED_REVISION_REQUIRED')
            if decision not in ('APPROVED','REJECTED','CHANGES_REQUESTED'): raise InternshipLogScopeError('INVALID_REVIEW_DECISION',status_code=422)
            review=insert_row(conn,'workplace_log_reviews',revision_id=revision['id'],placement_id=placement_id,
                mentor_assignment_id=assignment_id,decision=decision,comment=comment,decided_at=now())
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='WORKPLACE_LOG_REVIEWED',entity_type='workplace_log_review',entity_id=review['id'])
            return review

    def _owned(self,conn,placement_id,author_id):
        try: p=get_row(conn,'placements',placement_id,True)
        except PlacementScopeError: raise InternshipLogScopeError('PLACEMENT_NOT_FOUND',status_code=404)
        if not owns_candidate(author_id,p['candidate_id']): raise InternshipLogScopeError('PLACEMENT_AUTHOR_FORBIDDEN',status_code=403)
        require_internship_placement(conn,p)
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
            from app.db.institution_scope import TASHKENT
            if not p['start_date']<=local_date<=min(p['end_date'],now().astimezone(TASHKENT).date()): raise InternshipLogScopeError('INVALID_LOG_DATE',status_code=422)
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
