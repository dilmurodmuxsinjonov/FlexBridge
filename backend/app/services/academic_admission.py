"""Pending school binding and personally accepted original teacher authority."""
from uuid import uuid4
from datetime import datetime,timezone
from sqlalchemy import select,text

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table,transaction,now
from app.services import authority
from app.services.placements import get_row,insert_row,PlacementScopeError,require_internship_placement
from app.services.placement_admission import fingerprint,evidence,request_record
from app.services.pagination import page
from app.services.governance import GovernanceError
from app.services.academic_notices import queue_notice


def proof_for(conn,name,column,key):
    t=table(name)
    value=conn.execute(select(t).where(t.c[column]==key)).mappings().first()
    return dict(value) if value else None


def snapshot(conn,name,key):
    # Table names are fixed internal callers, never request identifiers.
    return conn.execute(text('SELECT to_jsonb(r) FROM flexbridge.'+name+' r WHERE r.id=:id'),{'id':key}).scalar_one()


def projection(row,field,receipt):
    return {**{k:v.astimezone(timezone.utc).isoformat() if isinstance(v,datetime) else v for k,v in row.items()},field:receipt}


class AcademicAdmissionService:
    audit=AppendOnlyAuditStore()

    def request_student(self,*,actor,placement_id,enrollment_id,terms_id,version,idempotency_key):
        digest=fingerprint('STUDENT_ACADEMIC_REQUEST',placement_id=placement_id,enrollment_id=enrollment_id,terms_id=terms_id,version=version)
        with transaction() as conn:
            hint=get_row(conn,'enrollments',enrollment_id)
            p,terms=self.locked(conn,placement_id,hint['institution_id'])
            enrollment=get_row(conn,'enrollments',enrollment_id,True)
            if get_row(conn,'candidate_profiles',p['candidate_id'])['user_id']!=actor.user_id or enrollment['candidate_id']!=p['candidate_id']:
                raise GovernanceError('ENROLLMENT_SCOPE_FORBIDDEN',status_code=403)
            authority.account_authority(conn,actor)
            old=request_record(conn,'student_academic_requests',actor,idempotency_key,digest)
            if old:return old['receipt']
            if p['current_terms_id']!=terms_id or terms['version']!=version:raise PlacementScopeError('STALE_PLAN_VERSION')
            if proof_for(conn,'placement_academic_bindings','placement_id',placement_id):raise PlacementScopeError('SCHOOL_BINDING_AMENDMENT_REQUIRED')
            i=proof_for(conn,'placement_intakes','placement_id',placement_id)
            if p['status'] not in ('PLANNED','PENDING_START_CONFIRMATION') or not i or not i['academic_required']:
                raise GovernanceError('PENDING_ACADEMIC_PLACEMENT_REQUIRED',status_code=403)
            if not conn.execute(text('SELECT flexbridge.enrollment_is_current(:e)'),{'e':enrollment_id}).scalar_one():
                raise GovernanceError('CURRENT_VERIFIED_ENROLLMENT_REQUIRED',status_code=403)
            t=table('student_academic_requests')
            revision=conn.execute(select(t.c.revision).where(t.c.placement_id==placement_id).order_by(t.c.revision.desc()).limit(1)).scalar_one_or_none()
            rid=str(uuid4());revision=(revision or 0)+1;stamp=now()
            receipt=dict(request_id=rid,placement_id=placement_id,revision=revision,institution_id=enrollment['institution_id'],
                enrollment_id=enrollment_id,terms_id=terms_id,version=version,recorded_at=stamp.isoformat(),requires_bound_plan_acceptance=True)
            conn.execute(t.insert().values(id=rid,created_at=stamp,placement_id=placement_id,revision=revision,
                institution_id=enrollment['institution_id'],enrollment_id=enrollment_id,terms_id=terms_id,**evidence(conn,actor),
                idempotency_key=idempotency_key,request_fingerprint=digest,receipt=receipt))
            self.audit.append_audit_event(actor_id=actor.user_id,action='STUDENT_ACADEMIC_REQUESTED',entity_type='placement',entity_id=placement_id)
            return receipt

    def locked(self,conn,placement_id,institution_id):
        get_row(conn,'institutions',institution_id,True)
        hint=get_row(conn,'placements',placement_id)
        get_row(conn,'organizations',hint['organization_id'],True)
        p=get_row(conn,'placements',placement_id,True)
        require_internship_placement(conn,p)
        terms=get_row(conn,'placement_terms',p['current_terms_id'],True)
        return p,terms

    def locked_assignment(self,conn,assignment_id):
        hint=get_row(conn,'academic_assignments',assignment_id)
        p,terms=self.locked(conn,hint['placement_id'],hint['institution_id'])
        s=get_row(conn,'student_supervisions',hint['supervision_id'],True)
        get_row(conn,'enrollments',s['enrollment_id'],True)
        get_row(conn,'institution_agreements',s['agreement_id'],True)
        a=get_row(conn,'academic_assignments',assignment_id,True)
        if any(a[k]!=hint[k] for k in ('institution_id','placement_id','supervision_id')):
            raise PlacementScopeError('ACADEMIC_SCOPE_CHANGED_RETRY')
        return p,terms,s,a

    def material(self,conn,p,supervision_id,institution_id):
        s=get_row(conn,'student_supervisions',supervision_id,True)
        enrollment=get_row(conn,'enrollments',s['enrollment_id'],True)
        agreement=get_row(conn,'institution_agreements',s['agreement_id'],True)
        if (s['institution_id']!=institution_id or enrollment['institution_id']!=institution_id
            or enrollment['candidate_id']!=p['candidate_id'] or agreement['institution_id']!=institution_id
            or not conn.execute(text('SELECT flexbridge.academic_supervision_current(:s,:c)'),
                                {'s':s['id'],'c':p['candidate_id']}).scalar_one()):
            raise GovernanceError('ACADEMIC_SCOPE_NOT_CURRENT',status_code=403)
        binding=proof_for(conn,'placement_academic_bindings','placement_id',p['id'])
        if binding and binding['origin']=='PUBLIC' and (binding['scope_snapshot']['agreement_id']!=agreement['id']
            or binding['scope_snapshot']['agreement_version']!=agreement['version']):
            raise GovernanceError('ACADEMIC_AGREEMENT_VERSION_CHANGED',status_code=403)
        return s,enrollment,agreement

    def create_supervision(self,actor,*,institution_id,enrollment_id,agreement_id,purpose,legal_basis,idempotency_key):
        if not legal_basis.strip() or len(legal_basis)>2000 or not purpose.strip() or len(purpose)>80:
            raise GovernanceError('INVALID_SUPERVISION_PURPOSE_OR_BASIS',status_code=422)
        digest=fingerprint('SUPERVISION_CREATE',institution_id=institution_id,enrollment_id=enrollment_id,
                           agreement_id=agreement_id,purpose=purpose,legal_basis=legal_basis)
        with transaction() as conn:
            get_row(conn,'institutions',institution_id,True)
            enrollment=get_row(conn,'enrollments',enrollment_id,True)
            agreement=get_row(conn,'institution_agreements',agreement_id,True)
            coordinator=authority.institution_authority(conn,actor,institution_id,'COORDINATOR',require_mfa=True)
            old=request_record(conn,'supervision_origins',actor,idempotency_key,digest)
            if old:return projection(get_row(conn,'student_supervisions',old['supervision_id']),'supervision_receipt',old['receipt'])
            from app.db.institution_scope import TASHKENT
            today=now().astimezone(TASHKENT).date();purposes=agreement['purposes']
            allowed=purpose in purposes if isinstance(purposes,list) else isinstance(purposes,dict) and purposes.get(purpose) is True
            if (enrollment['institution_id']!=institution_id or agreement['institution_id']!=institution_id
                or not conn.execute(text('SELECT flexbridge.enrollment_is_current(:e)'),{'e':enrollment_id}).scalar_one()
                or agreement['status']!='ACTIVE' or agreement['valid_from']>today
                or agreement['valid_to'] is not None and agreement['valid_to']<today or not allowed):
                raise GovernanceError('ACADEMIC_SCOPE_NOT_CURRENT',status_code=403)
            s=insert_row(conn,'student_supervisions',enrollment_id=enrollment_id,institution_id=institution_id,
                coordinator_membership_id=coordinator['id'],agreement_id=agreement_id,purpose=purpose,
                legal_basis=legal_basis,status='ACTIVE',accepted_at=now())
            receipt=dict(supervision_id=s['id'],institution_id=institution_id,enrollment_id=enrollment_id,
                         coordinator_action='RESPONSIBILITY_ACCEPTED',recorded_at=s['accepted_at'].isoformat())
            conn.execute(table('supervision_origins').insert().values(supervision_id=s['id'],created_at=now(),origin='PUBLIC',
                initial_snapshot=snapshot(conn,'student_supervisions',s['id']),**evidence(conn,actor),
                coordinator_grant_id=coordinator['_authority_grant_id'],idempotency_key=idempotency_key,
                request_fingerprint=digest,receipt=receipt))
            self.audit.append_audit_event(actor_id=actor.user_id,action='STUDENT_SUPERVISION_CREATED',entity_type='student_supervision',entity_id=s['id'])
            return projection(get_row(conn,'student_supervisions',s['id']),'supervision_receipt',receipt)

    def _bind(self,conn,actor,p,terms,s,enrollment,agreement,coordinator,key,digest):
        b=proof_for(conn,'placement_academic_bindings','placement_id',p['id'])
        if b:
            if b['institution_id']!=s['institution_id'] or b['supervision_id']!=s['id'] or b['enrollment_id']!=enrollment['id']:
                raise GovernanceError('ACADEMIC_BINDING_MISMATCH',status_code=403)
            if not p['academic_track'] or p['enrollment_id']!=enrollment['id']:
                raise GovernanceError('ACADEMIC_BINDING_MISMATCH',status_code=403)
            return p,terms,b
        intake=proof_for(conn,'placement_intakes','placement_id',p['id'])
        if not intake or not intake['academic_required'] or p['status'] not in ('PLANNED','PENDING_START_CONFIRMATION'):
            raise GovernanceError('PENDING_ACADEMIC_PLACEMENT_REQUIRED',status_code=403)
        requests=table('student_academic_requests')
        choice=conn.execute(select(requests).where(requests.c.placement_id==p['id']).order_by(requests.c.revision.desc()).limit(1)).mappings().first()
        if not choice or choice['institution_id']!=s['institution_id'] or choice['enrollment_id']!=enrollment['id']:
            raise GovernanceError('STUDENT_SCHOOL_CHOICE_REQUIRED',status_code=403)
        scope=dict(institution_id=s['institution_id'],enrollment_id=enrollment['id'],supervision_id=s['id'],
                   agreement_id=agreement['id'],agreement_version=agreement['version'],purpose=s['purpose'],legal_basis=s['legal_basis'])
        new_terms=insert_row(conn,'placement_terms',placement_id=p['id'],version=terms['version']+1,schema_version=terms['schema_version'],
            terms_snapshot={**terms['terms_snapshot'],'academic_scope':scope},daily_limit_minutes=terms['daily_limit_minutes'],
            weekly_limit_minutes=terms['weekly_limit_minutes'],required_minutes=terms['required_minutes'])
        conn.execute(table('placements').update().where(table('placements').c.id==p['id']).values(
            current_terms_id=new_terms['id'],version=p['version']+1,updated_at=now()))
        tasks=table('plan_tasks')
        for task in conn.execute(select(tasks).where(tasks.c.terms_id==terms['id']).order_by(tasks.c.code)).mappings():
            insert_row(conn,'plan_tasks',terms_id=new_terms['id'],**{k:task[k] for k in ('code','title','expected_result','required','target_minutes')})
        receipt=dict(placement_id=p['id'],terms_id=new_terms['id'],version=new_terms['version'],institution_id=s['institution_id'],
                     supervision_id=s['id'],recorded_at=now().isoformat())
        conn.execute(table('placement_academic_bindings').insert().values(placement_id=p['id'],created_at=now(),origin='PUBLIC',
            institution_id=s['institution_id'],enrollment_id=enrollment['id'],supervision_id=s['id'],terms_id=new_terms['id'],
            initial_snapshot=snapshot(conn,'placements',p['id']),scope_snapshot=scope,**evidence(conn,actor),
            coordinator_grant_id=coordinator['_authority_grant_id'],idempotency_key=key,request_fingerprint=digest,receipt=receipt))
        conn.execute(table('placements').update().where(table('placements').c.id==p['id'])
                     .values(academic_track=True,enrollment_id=enrollment['id'],updated_at=now()))
        self.audit.append_audit_event(actor_id=actor.user_id,action='PLACEMENT_ACADEMIC_BOUND',entity_type='placement',entity_id=p['id'])
        return get_row(conn,'placements',p['id']),get_row(conn,'placement_terms',new_terms['id']),proof_for(conn,'placement_academic_bindings','placement_id',p['id'])

    def nominate(self,*,actor,placement_id,institution_id,supervisor_id,supervision_id,idempotency_key):
        digest=fingerprint('ACADEMIC_NOMINATION',placement_id=placement_id,institution_id=institution_id,
                           supervisor_id=supervisor_id,supervision_id=supervision_id)
        with transaction() as conn:
            p,terms=self.locked(conn,placement_id,institution_id)
            s,enrollment,agreement=self.material(conn,p,supervision_id,institution_id)
            coordinator=authority.institution_authority(conn,actor,institution_id,'COORDINATOR',require_mfa=True)
            old=request_record(conn,'academic_assignment_proofs',actor,idempotency_key,digest)
            if old:return projection(get_row(conn,'academic_assignments',old['assignment_id']),'assignment_receipt',old['receipt'])
            if p['status'] not in ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE'):
                raise GovernanceError('PLACEMENT_NOT_ASSIGNABLE',status_code=403)
            member=get_row(conn,'institution_memberships',supervisor_id)
            if s['coordinator_membership_id']!=coordinator['id'] or member['institution_id']!=institution_id:
                raise GovernanceError('SUPERVISION_ACTOR_FORBIDDEN',status_code=403)
            if member['user_id'] in (actor.user_id,get_row(conn,'candidate_profiles',p['candidate_id'])['user_id']):
                raise GovernanceError('SELF_ASSIGNMENT_FORBIDDEN',status_code=403)
            teacher=authority.institution_role_authority(conn,member['user_id'],institution_id,'TEACHER',nowait=True)
            if teacher['id']!=supervisor_id:raise GovernanceError('TEACHER_MEMBERSHIP_REQUIRED',status_code=403)
            p,terms,b=self._bind(conn,actor,p,terms,s,enrollment,agreement,coordinator,idempotency_key,digest)
            a=insert_row(conn,'academic_assignments',placement_id=placement_id,institution_id=institution_id,
                teacher_membership_id=supervisor_id,supervision_id=supervision_id,assigned_by_id=actor.user_id,assigned_at=now())
            receipt=dict(assignment_id=a['id'],placement_id=placement_id,terms_id=terms['id'],version=terms['version'],
                         teacher_user_id=teacher['user_id'],state_at_nomination='NOMINATED',recorded_at=a['assigned_at'].isoformat())
            conn.execute(table('academic_assignment_proofs').insert().values(assignment_id=a['id'],placement_id=placement_id,origin='PUBLIC',
                created_at=now(),teacher_user_id=teacher['user_id'],teacher_grant_id=teacher['_authority_grant_id'],
                teacher_appointment_id=teacher['_authority_appointment_id'],initial_snapshot=snapshot(conn,'academic_assignments',a['id']),
                **evidence(conn,actor),coordinator_grant_id=coordinator['_authority_grant_id'],idempotency_key=idempotency_key,
                request_fingerprint=digest,receipt=receipt))
            queue_notice(conn,placement_id,a['id'],'NOMINATED',a['id'])
            self.audit.append_audit_event(actor_id=actor.user_id,action='ACADEMIC_ASSIGNMENT_CREATED',entity_type='academic_assignment',entity_id=a['id'])
            return projection(get_row(conn,'academic_assignments',a['id']),'assignment_receipt',receipt)

    def teacher(self,conn,actor,p,a):
        proof=proof_for(conn,'academic_assignment_proofs','assignment_id',a['id'])
        if not proof or proof['teacher_user_id']!=actor.user_id or a['revoked_at']:
            raise GovernanceError('ACADEMIC_ASSIGNMENT_FORBIDDEN',status_code=403)
        current=authority.institution_authority(conn,actor,a['institution_id'],'TEACHER')
        if (current['id']!=a['teacher_membership_id'] or current['_authority_grant_id']!=proof['teacher_grant_id']
            or current['_authority_appointment_id']!=proof['teacher_appointment_id']):
            raise GovernanceError('ORIGINAL_TEACHER_AUTHORITY_REQUIRED',status_code=403)
        if get_row(conn,'candidate_profiles',p['candidate_id'])['user_id']==actor.user_id:
            raise GovernanceError('SELF_REVIEW_FORBIDDEN',status_code=403)
        return current

    def accept(self,*,actor,placement_id,assignment_id,terms_id,version,idempotency_key):
        digest=fingerprint('TEACHER_ACCEPT',placement_id=placement_id,assignment_id=assignment_id,terms_id=terms_id,version=version)
        with transaction() as conn:
            p,terms,s,a=self.locked_assignment(conn,assignment_id)
            if p['id']!=placement_id:raise GovernanceError('ACADEMIC_ASSIGNMENT_FORBIDDEN',status_code=403)
            self.material(conn,p,s['id'],a['institution_id'])
            current=self.teacher(conn,actor,p,a)
            old=request_record(conn,'academic_assignment_consents',actor,idempotency_key,digest)
            if old:return old['receipt']
            if p['current_terms_id']!=terms_id or terms['version']!=version:raise PlacementScopeError('STALE_PLAN_VERSION')
            if p['status'] not in ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE'):
                raise PlacementScopeError('PLACEMENT_NOT_ASSIGNABLE')
            t=table('academic_assignments')
            if conn.execute(select(t.c.id).where(t.c.placement_id==placement_id,t.c.id!=assignment_id,
                t.c.accepted_at.is_not(None),t.c.revoked_at.is_(None))).first():raise PlacementScopeError('CURRENT_TEACHER_EXISTS')
            stamp=now();cid=str(uuid4())
            receipt=dict(consent_id=cid,placement_id=placement_id,assignment_id=assignment_id,terms_id=terms_id,version=version,
                         side='TEACHER',recorded_at=stamp.isoformat())
            conn.execute(table('academic_assignment_consents').insert().values(id=cid,created_at=stamp,placement_id=placement_id,
                assignment_id=assignment_id,terms_id=terms_id,**evidence(conn,actor),teacher_grant_id=current['_authority_grant_id'],
                teacher_appointment_id=current['_authority_appointment_id'],idempotency_key=idempotency_key,
                request_fingerprint=digest,receipt=receipt))
            if a['accepted_at'] is None:
                conn.execute(t.update().where(t.c.id==assignment_id).values(accepted_at=stamp,updated_at=stamp))
            queue_notice(conn,placement_id,assignment_id,'ACCEPTED',cid)
            self.audit.append_audit_event(actor_id=actor.user_id,action='ACADEMIC_ASSIGNMENT_ACCEPTED',entity_type='academic_assignment',entity_id=assignment_id)
            return receipt

    def revoke(self,actor,assignment_id,*,idempotency_key=None):
        key=idempotency_key or 'revoke-academic:'+assignment_id
        digest=fingerprint('ACADEMIC_REVOKE',assignment_id=assignment_id)
        with transaction() as conn:
            hint=get_row(conn,'academic_assignments',assignment_id)
            get_row(conn,'institutions',hint['institution_id'],True)
            parent=get_row(conn,'placements',hint['placement_id'])
            get_row(conn,'organizations',parent['organization_id'],True)
            p=get_row(conn,'placements',hint['placement_id'],True)
            a=get_row(conn,'academic_assignments',assignment_id,True)
            if a['institution_id']!=hint['institution_id'] or a['placement_id']!=p['id']:
                raise PlacementScopeError('ACADEMIC_SCOPE_CHANGED_RETRY')
            current=authority.institution_authority(conn,actor,a['institution_id'],'COORDINATOR',require_mfa=True)
            old=request_record(conn,'academic_assignment_events',actor,key,digest)
            if old:return projection(get_row(conn,'academic_assignments',assignment_id),'revocation_receipt',old['receipt'])
            if a['revoked_at'] is not None:return projection(a,'revocation_receipt',None)
            stamp=now();eid=str(uuid4())
            receipt=dict(event_id=eid,assignment_id=assignment_id,placement_id=p['id'],action='REVOKE',recorded_at=stamp.isoformat())
            conn.execute(table('academic_assignment_events').insert().values(id=eid,created_at=stamp,placement_id=p['id'],
                assignment_id=assignment_id,action='REVOKE',**evidence(conn,actor),coordinator_grant_id=current['_authority_grant_id'],
                idempotency_key=key,request_fingerprint=digest,receipt=receipt))
            conn.execute(table('academic_assignments').update().where(table('academic_assignments').c.id==assignment_id)
                         .values(revoked_at=stamp,updated_at=stamp))
            queue_notice(conn,p['id'],assignment_id,'REVOKED',eid)
            self.audit.append_audit_event(actor_id=actor.user_id,action='ACADEMIC_ASSIGNMENT_REVOKED',entity_type='academic_assignment',entity_id=assignment_id)
            return projection(get_row(conn,'academic_assignments',assignment_id),'revocation_receipt',receipt)

    def start_material(self,conn,p):
        b=proof_for(conn,'placement_academic_bindings','placement_id',p['id'])
        if not b or not b['supervision_id']:return None
        s=get_row(conn,'student_supervisions',b['supervision_id'],True)
        get_row(conn,'enrollments',s['enrollment_id'],True)
        get_row(conn,'institution_agreements',s['agreement_id'],True)
        t=table('academic_assignments')
        rows=[dict(r) for r in conn.execute(select(t).where(t.c.placement_id==p['id']).order_by(t.c.id).with_for_update()).mappings()]
        return b,rows

    def pin_start_authority(self,conn,p,terms,material):
        if material is None:raise PlacementScopeError('ACADEMIC_ADMISSION_REQUIRED')
        b,rows=material
        self.material(conn,p,b['supervision_id'],b['institution_id'])
        co=authority.institution_role_authority(conn,b['actor_id'],b['institution_id'],'COORDINATOR',nowait=True)
        if co['_authority_grant_id']!=b['coordinator_grant_id']:raise GovernanceError('ACADEMIC_COORDINATOR_NOT_CURRENT',status_code=403)
        for a in rows:
            if a['revoked_at'] or not a['accepted_at']:continue
            q=proof_for(conn,'academic_assignment_proofs','assignment_id',a['id'])
            if not q:continue
            current=authority.institution_role_authority(conn,q['teacher_user_id'],a['institution_id'],'TEACHER',nowait=True)
            if current['_authority_grant_id']==q['teacher_grant_id'] and current['_authority_appointment_id']==q['teacher_appointment_id']:
                if conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),{'a':a['id'],'t':terms['id']}).scalar_one():return
        raise PlacementScopeError('PERSONAL_TEACHER_ACCEPTANCE_REQUIRED')

    def own_assignments(self,actor,*,limit=50,after=None):
        with transaction() as conn:
            authority.account_authority(conn,actor)
            a,q,g=table('academic_assignments'),table('academic_assignment_proofs'),table('institution_role_grants')
            query=select(a.c.id,a.c.placement_id,a.c.institution_id,a.c.assigned_at,a.c.accepted_at).join(q,q.c.assignment_id==a.c.id)
            query=query.join(g,g.c.id==q.c.teacher_grant_id).where(q.c.teacher_user_id==actor.user_id,a.c.revoked_at.is_(None),
                g.c.appointment_id==q.c.teacher_appointment_id)
            query=query.where(text("flexbridge.academic_grant_current(:actor,academic_assignments.institution_id,academic_assignment_proofs.teacher_grant_id,'TEACHER')")).params(actor=actor.user_id)
            return page(conn,query,a.c.id,a.c.assigned_at,limit=limit,after=after)


academic_service=AcademicAdmissionService()
