"""Minimum submitted diary detail under an exact current academic relationship."""
from sqlalchemy import select,text

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table,transaction
from app.services.placements import get_row,PlacementScopeError,require_internship_placement
from app.services.academic_admission import proof_for
from app.services.academic_views import pin_roles,BOUND_COORDINATOR,TEACHER_REVISION,BINDING_VERSION


class AcademicRecordService:
    audit=AppendOnlyAuditStore()

    def _locked_revision(self,conn,revision_id):
        hint=get_row(conn,'log_revisions',revision_id)
        log_hint=get_row(conn,'daily_logs',hint['daily_log_id'])
        binding=proof_for(conn,'placement_academic_bindings','placement_id',log_hint['placement_id'])
        if not binding or not binding['supervision_id']:raise PlacementScopeError('ACADEMIC_REVISION_NOT_FOUND',status_code=404)
        get_row(conn,'institutions',binding['institution_id'],True)
        parent=get_row(conn,'placements',log_hint['placement_id'])
        get_row(conn,'organizations',parent['organization_id'],True)
        placement=get_row(conn,'placements',parent['id'],True)
        require_internship_placement(conn,placement)
        get_row(conn,'placement_terms',placement['current_terms_id'],True)
        supervision=get_row(conn,'student_supervisions',binding['supervision_id'],True)
        get_row(conn,'enrollments',supervision['enrollment_id'],True)
        get_row(conn,'institution_agreements',supervision['agreement_id'],True)
        a=table('academic_assignments')
        conn.execute(select(a.c.id).where(a.c.placement_id==placement['id']).order_by(a.c.id).with_for_update()).all()
        log=get_row(conn,'daily_logs',hint['daily_log_id'],True)
        revision=get_row(conn,'log_revisions',revision_id,True)
        if log['placement_id']!=placement['id'] or revision['daily_log_id']!=log['id']:
            raise PlacementScopeError('ACADEMIC_SCOPE_CHANGED_RETRY')
        return placement,revision,binding

    def detail(self,actor,revision_id):
        with transaction() as conn:
            placement,revision,binding=self._locked_revision(conn,revision_id)
            pin_roles(conn,actor,[binding['institution_id']],required=True)
            r,l,p,b,s,e,g,c,t,rt=(table(n) for n in ('log_revisions','daily_logs','placements','placement_academic_bindings',
                'student_supervisions','enrollments','institution_agreements','candidate_profiles','placement_terms','placement_terms'))
            revision_terms=rt.alias('revision_terms')
            query=select(r.c.id,r.c.revision,r.c.terms_id,r.c.day_type,r.c.summary,r.c.total_minutes,r.c.submitted_at,
                l.c.id.label('daily_log_id'),l.c.local_date,p.c.id.label('placement_id'),p.c.status.label('placement_status'),
                (l.c.current_revision_id==r.c.id).label('is_current_revision'),
                s.c.institution_id,s.c.purpose,revision_terms.c.version.label('terms_version')).select_from(
                r.join(l,l.c.id==r.c.daily_log_id).join(p,p.c.id==l.c.placement_id).join(b,b.c.placement_id==p.c.id)
                .join(s,s.c.id==b.c.supervision_id).join(e,e.c.id==s.c.enrollment_id).join(g,g.c.id==s.c.agreement_id)
                .join(c,c.c.id==p.c.candidate_id).join(t,t.c.id==p.c.current_terms_id)
                .join(revision_terms,(revision_terms.c.id==r.c.terms_id)&(revision_terms.c.placement_id==p.c.id)))
            query=query.where(r.c.id==revision_id,r.c.daily_log_id==l.c.id,r.c.author_id==c.c.user_id,r.c.status=='SUBMITTED',
                r.c.submitted_at.is_not(None),c.c.user_id!=actor.user_id,p.c.id==placement['id'],p.c.academic_track.is_(True),
                p.c.status.in_(('ACTIVE','COMPLETION_PENDING','COMPLETED','CANCELLED')),
                b.c.institution_id==binding['institution_id'],b.c.enrollment_id==p.c.enrollment_id,
                s.c.enrollment_id==p.c.enrollment_id,e.c.candidate_id==c.c.id,s.c.institution_id==b.c.institution_id,
                text('flexbridge.academic_supervision_current(student_supervisions.id,candidate_profiles.id)'),
                text(BINDING_VERSION),text('('+BOUND_COORDINATOR+' OR '+TEACHER_REVISION+')')).params(actor=actor.user_id)
            row=conn.execute(query).mappings().first()
            if not row:raise PlacementScopeError('ACADEMIC_REVISION_NOT_FOUND',status_code=404)
            result=dict(row)
            entries,tasks=table('log_task_entries'),table('plan_tasks')
            # The result text is the scoped diary record; private file references are separate.
            result['tasks']=[dict(v) for v in conn.execute(select(entries.c.id,tasks.c.id.label('plan_task_id'),entries.c.result_text,
                entries.c.minutes,tasks.c.code,tasks.c.title)
                .outerjoin(tasks,(tasks.c.id==entries.c.plan_task_id)&(tasks.c.terms_id==revision['terms_id']))
                .where(entries.c.revision_id==revision_id).order_by(entries.c.created_at,entries.c.id)).mappings()]
            for name,key in (('workplace_log_reviews','workplace_reviews'),('academic_log_reviews','academic_reviews')):
                reviews=table(name)
                assignment=reviews.c.mentor_assignment_id if name=='workplace_log_reviews' else reviews.c.academic_assignment_id
                result[key]=[dict(v) for v in conn.execute(select(reviews.c.id,assignment,reviews.c.decision,reviews.c.comment,reviews.c.decided_at)
                    .where(reviews.c.revision_id==revision_id,reviews.c.placement_id==placement['id'])
                    .order_by(reviews.c.decided_at,reviews.c.id)).mappings()]
            self.audit.append_audit_event(actor_id=actor.user_id,action='ACADEMIC_REVISION_VIEWED',
                entity_type='log_revision',entity_id=revision_id,metadata={'institution_id':binding['institution_id'],'purpose':row['purpose']})
            return result


academic_record_service=AcademicRecordService()
