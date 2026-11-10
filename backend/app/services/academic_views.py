"""Current enrollment/purpose and original personal assignment scoped academic lists."""
from sqlalchemy import select,text,func

from app.db.storage import table,transaction,now
from app.db.institution_scope import institution_scope_query,TASHKENT
from app.services.authority import account_authority
from app.services.governance import GovernanceError
from app.services.placements import get_row
from app.services.pagination import page


# Fixed internal table names. Purpose values and all caller values are parameters.
BOUND_COORDINATOR="""placement_academic_bindings.origin='PUBLIC'
 AND placement_academic_bindings.actor_id=:actor
 AND flexbridge.academic_grant_current(:actor,student_supervisions.institution_id,
     placement_academic_bindings.coordinator_grant_id,'COORDINATOR')"""
OWN_SUPERVISION="""((supervision_origins.origin='PUBLIC' AND supervision_origins.actor_id=:actor
 AND flexbridge.academic_grant_current(:actor,student_supervisions.institution_id,
     supervision_origins.coordinator_grant_id,'COORDINATOR')) OR EXISTS(
 SELECT 1 FROM flexbridge.placement_academic_bindings b WHERE b.supervision_id=student_supervisions.id
   AND b.origin='PUBLIC' AND b.actor_id=:actor AND b.enrollment_id=student_supervisions.enrollment_id
   AND b.scope_snapshot->>'agreement_id'=student_supervisions.agreement_id::text
   AND (b.scope_snapshot->>'agreement_version')::integer=(SELECT agreement.version
     FROM flexbridge.institution_agreements agreement WHERE agreement.id=student_supervisions.agreement_id)
   AND flexbridge.academic_grant_current(:actor,student_supervisions.institution_id,b.coordinator_grant_id,'COORDINATOR')))"""
TEACHER_SUPERVISION="""EXISTS(SELECT 1 FROM flexbridge.academic_assignments a
 JOIN flexbridge.academic_assignment_proofs q ON q.assignment_id=a.id
 JOIN flexbridge.placements p ON p.id=a.placement_id
 WHERE a.supervision_id=student_supervisions.id AND q.teacher_user_id=:actor AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE')
   AND flexbridge.academic_teacher_current(a.id,p.current_terms_id))"""
TEACHER_REVISION="""EXISTS(SELECT 1 FROM flexbridge.academic_assignments a
 JOIN flexbridge.academic_assignment_proofs q ON q.assignment_id=a.id
 WHERE a.placement_id=placements.id AND a.supervision_id=student_supervisions.id
   AND q.teacher_user_id=:actor AND flexbridge.academic_teacher_current(a.id,log_revisions.terms_id))"""
BINDING_VERSION="""(placement_academic_bindings.origin='LEGACY_IMPORT' OR (
 placement_terms.terms_snapshot->'academic_scope'=placement_academic_bindings.scope_snapshot
 AND (placement_academic_bindings.scope_snapshot->>'agreement_version')::integer=institution_agreements.version))"""


def pin_roles(conn,actor,institutions,*,coordinator=False,required=False):
    account_authority(conn,actor,require_mfa=coordinator)
    if not institutions:return set()
    m=table('institution_memberships')
    query=institution_scope_query(actor.user_id,allowed=('COORDINATOR',) if coordinator else ('COORDINATOR','TEACHER'),lock=True)
    rows=conn.execute(query.where(m.c.institution_id.in_(institutions)).order_by(m.c.institution_id,m.c.id)).mappings().all()
    # A sensitive role can become current while waiting for these scoped rows.
    account_authority(conn,actor,require_mfa=coordinator)
    if required and not rows:raise GovernanceError('INSTITUTION_SCOPE_FORBIDDEN',status_code=403)
    return {r['institution_id'] for r in rows}


class AcademicViewService:
    def supervisions(self,actor,institution_id,*,enrollment_id=None,purpose=None,limit=50,after=None):
        with transaction() as conn:
            get_row(conn,'institutions',institution_id,True)
            pin_roles(conn,actor,[institution_id],required=True)
            s,e,o,c,u=(table(n) for n in ('student_supervisions','enrollments','supervision_origins','candidate_profiles','users'))
            query=select(s.c.id,s.c.institution_id,s.c.enrollment_id,s.c.purpose,s.c.accepted_at.label('coordinator_accepted_at'),
                u.c.display_name.label('student_name')).select_from(s.join(e,e.c.id==s.c.enrollment_id)
                .join(o,o.c.supervision_id==s.c.id).join(c,c.c.id==e.c.candidate_id).join(u,u.c.id==c.c.user_id))
            query=query.where(s.c.institution_id==institution_id,c.c.user_id!=actor.user_id,
                func.flexbridge.academic_supervision_current(s.c.id,c.c.id),text('('+OWN_SUPERVISION+' OR '+TEACHER_SUPERVISION+')'))
            if enrollment_id is not None:query=query.where(s.c.enrollment_id==enrollment_id)
            if purpose is not None:query=query.where(s.c.purpose==purpose)
            result=page(conn,query.params(actor=actor.user_id),s.c.id,s.c.created_at,limit=limit,after=after)
            for row in result['items']:row['assignments_url']='/api/v1/student-supervisions/'+row['id']+'/academic-assignments'
            return result

    def supervision_assignments(self,actor,supervision_id,*,limit=50,after=None):
        with transaction() as conn:
            hint=get_row(conn,'student_supervisions',supervision_id)
            get_row(conn,'institutions',hint['institution_id'],True)
            pin_roles(conn,actor,[hint['institution_id']],required=True)
            s,e,b,p,a,q,m,u,c,t,g=(table(n) for n in ('student_supervisions','enrollments','placement_academic_bindings','placements',
                'academic_assignments','academic_assignment_proofs','institution_memberships','users','candidate_profiles','placement_terms','institution_agreements'))
            query=select(a.c.id,a.c.placement_id,a.c.teacher_membership_id,u.c.display_name.label('teacher_name'),a.c.accepted_at,
                a.c.revoked_at,p.c.status,p.c.current_terms_id,t.c.version).select_from(s.join(e,e.c.id==s.c.enrollment_id)
                .join(b,b.c.supervision_id==s.c.id).join(p,p.c.id==b.c.placement_id).join(a,(a.c.placement_id==p.c.id)&(a.c.supervision_id==s.c.id))
                .join(q,q.c.assignment_id==a.c.id).join(m,m.c.id==a.c.teacher_membership_id).join(u,u.c.id==m.c.user_id)
                .join(c,c.c.id==p.c.candidate_id).join(t,t.c.id==p.c.current_terms_id).join(g,g.c.id==s.c.agreement_id))
            query=query.where(s.c.id==supervision_id,s.c.institution_id==hint['institution_id'],c.c.user_id!=actor.user_id,
                p.c.academic_track.is_(True),p.c.enrollment_id==s.c.enrollment_id,b.c.enrollment_id==s.c.enrollment_id,
                b.c.institution_id==s.c.institution_id,a.c.institution_id==s.c.institution_id,
                func.flexbridge.academic_supervision_current(s.c.id,c.c.id),text(BINDING_VERSION),text('('+BOUND_COORDINATOR+''' OR (
                  academic_assignment_proofs.teacher_user_id=:actor AND placements.status IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE')
                  AND flexbridge.academic_teacher_current(academic_assignments.id,placements.current_terms_id)))'''))
            return page(conn,query.params(actor=actor.user_id),a.c.id,a.c.assigned_at,limit=limit,after=after)

    def assignment_queue(self,actor,institution_id,*,limit=50,after=None):
        with transaction() as conn:
            get_row(conn,'institutions',institution_id,True)
            pin_roles(conn,actor,[institution_id],coordinator=True,required=True)
            r,p,i,e,c,u,b=(table(n) for n in ('student_academic_requests','placements','placement_intakes','enrollments','candidate_profiles','users','placement_academic_bindings'))
            query=select(r.c.id,r.c.revision.label('request_revision'),r.c.placement_id,r.c.enrollment_id,r.c.institution_id,
                r.c.terms_id,u.c.display_name.label('student_name')).select_from(r.join(p,p.c.id==r.c.placement_id)
                .join(i,i.c.placement_id==p.c.id).join(e,e.c.id==r.c.enrollment_id).join(c,c.c.id==p.c.candidate_id)
                .join(u,u.c.id==c.c.user_id).outerjoin(b,b.c.placement_id==p.c.id))
            query=query.where(r.c.institution_id==institution_id,e.c.institution_id==institution_id,e.c.candidate_id==c.c.id,
                r.c.actor_id==c.c.user_id,c.c.user_id!=actor.user_id,r.c.terms_id==p.c.current_terms_id,
                p.c.status.in_(('PLANNED','PENDING_START_CONFIRMATION')),i.c.academic_required.is_(True),b.c.placement_id.is_(None),
                func.flexbridge.enrollment_is_current(e.c.id),text('''NOT EXISTS(SELECT 1 FROM flexbridge.student_academic_requests newer
                  WHERE newer.placement_id=student_academic_requests.placement_id AND newer.revision>student_academic_requests.revision)'''))
            result=page(conn,query,r.c.id,r.c.created_at,limit=limit,after=after)
            result['agreement_options']='/api/v1/institutions/'+institution_id+'/academic-agreements'
            result['teacher_options']='/api/v1/institutions/'+institution_id+'/academic-teachers'
            return result

    def agreements(self,actor,institution_id,*,limit=50,after=None):
        with transaction() as conn:
            get_row(conn,'institutions',institution_id,True)
            pin_roles(conn,actor,[institution_id],coordinator=True,required=True)
            a=table('institution_agreements');today=now().astimezone(TASHKENT).date()
            query=select(a.c.id,a.c.version,a.c.purposes,a.c.valid_from,a.c.valid_to).where(a.c.institution_id==institution_id,
                a.c.status=='ACTIVE',a.c.valid_from<=today,(a.c.valid_to.is_(None)|(a.c.valid_to>=today)))
            return page(conn,query,a.c.id,a.c.created_at,limit=limit,after=after)

    def teachers(self,actor,institution_id,*,limit=50,after=None):
        with transaction() as conn:
            get_row(conn,'institutions',institution_id,True)
            pin_roles(conn,actor,[institution_id],coordinator=True,required=True)
            m,u=(table(n) for n in ('institution_memberships','users'))
            query=select(m.c.id,u.c.display_name).join(u,u.c.id==m.c.user_id).where(m.c.institution_id==institution_id,
                u.c.id!=actor.user_id,text('''EXISTS(SELECT 1 FROM flexbridge.institution_role_grants g
                  WHERE g.membership_id=institution_memberships.id AND flexbridge.academic_grant_current(
                    institution_memberships.user_id,institution_memberships.institution_id,g.id,'TEACHER'))'''))
            return page(conn,query,m.c.id,m.c.created_at,limit=limit,after=after)

    def review_queue(self,actor,*,limit=50,after=None):
        with transaction() as conn:
            # Hints carry no private student data and cannot cause late institution locks.
            hints=sorted({r['institution_id'] for r in conn.execute(institution_scope_query(actor.user_id)).mappings()})
            for institution_id in hints:get_row(conn,'institutions',institution_id,True)
            allowed=pin_roles(conn,actor,hints)
            if not allowed:return {'items':[],'next_after':None}
            l,r,p,b,s,e,o,g,c,u,t=(table(n) for n in ('daily_logs','log_revisions','placements','placement_academic_bindings',
                'student_supervisions','enrollments','supervision_origins','institution_agreements','candidate_profiles','users','placement_terms'))
            query=select(r.c.id,l.c.id.label('daily_log_id'),p.c.id.label('placement_id'),s.c.institution_id,s.c.purpose,
                l.c.local_date,r.c.revision,r.c.submitted_at,u.c.display_name.label('student_name')).select_from(
                l.join(r,r.c.id==l.c.current_revision_id).join(p,p.c.id==l.c.placement_id).join(b,b.c.placement_id==p.c.id)
                .join(s,s.c.id==b.c.supervision_id).join(e,e.c.id==s.c.enrollment_id).join(o,o.c.supervision_id==s.c.id)
                .join(g,g.c.id==s.c.agreement_id).join(c,c.c.id==p.c.candidate_id).join(u,u.c.id==c.c.user_id)
                .join(t,t.c.id==p.c.current_terms_id))
            query=query.where(s.c.institution_id.in_(allowed),p.c.status=='ACTIVE',p.c.academic_track.is_(True),
                p.c.enrollment_id==s.c.enrollment_id,b.c.enrollment_id==s.c.enrollment_id,b.c.institution_id==s.c.institution_id,
                r.c.daily_log_id==l.c.id,r.c.status=='SUBMITTED',r.c.submitted_at.is_not(None),r.c.author_id==c.c.user_id,
                c.c.user_id!=actor.user_id,func.flexbridge.academic_supervision_current(s.c.id,c.c.id),
                text(BINDING_VERSION),
                text('('+BOUND_COORDINATOR+' OR '+TEACHER_REVISION+')'))
            return page(conn,query.params(actor=actor.user_id),r.c.id,r.c.submitted_at,limit=limit,after=after)


academic_view_service=AcademicViewService()
