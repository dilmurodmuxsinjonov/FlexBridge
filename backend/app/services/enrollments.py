"""Own education history and independently reviewed, revision-bound enrollment."""
from datetime import date, timedelta
import hashlib
import json
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import OperationalError

from app.adapters import storage
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import digest, rate_limit
from app.db.institution_scope import TASHKENT
from app.db.storage import now, table
from app.services.authority import account_authority, moderator_authority
from app.services.candidates import candidate_transaction, own_profile
from app.services.governance import GovernanceError
from app.services.organizations import evidence_files
from app.services.placements import get_row, insert_row

OPEN = ('PENDING', 'IN_REVIEW', 'NEEDS_INFO')


def fail(code, status=409):
    return GovernanceError(code, status_code=status)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def proof_insert(conn, name, **values):
    record={'created_at':now(), **values}
    if 'id' in table(name).c:record.setdefault('id',str(uuid4()))
    conn.execute(table(name).insert().values(**record))
    return record


def user_version(conn, user_id):
    return conn.execute(select(table('users').c.auth_version).where(table('users').c.id==user_id)).scalar_one()


def response_due():
    day=now().astimezone(TASHKENT)+timedelta(days=1)
    while day.weekday()>=5:day+=timedelta(days=1)
    return day


def normalize_proposal(actor, institution_id, *, program, start_date, end_date=None,
                       student_ref=None, file_ids=(), evidence_note=''):
    if not isinstance(program,str) or not 1<=len(program.strip())<=250:
        raise fail('ENROLLMENT_PROGRAM_INVALID',422)
    if type(start_date) is not date or (end_date is not None and (type(end_date) is not date or end_date<start_date)):
        raise fail('ENROLLMENT_DATES_INVALID',422)
    if student_ref is not None and (not isinstance(student_ref,str) or not 1<=len(student_ref.strip())<=256):
        raise fail('ENROLLMENT_REFERENCE_INVALID',422)
    ids=sorted(str(value) for value in file_ids)
    if len(ids)>5 or len(set(ids))!=len(ids):raise fail('INVALID_EVIDENCE_FILES',422)
    if not isinstance(evidence_note,str) or len(evidence_note)>4000 or (ids and len(evidence_note.strip())<15):
        raise fail('ENROLLMENT_EVIDENCE_NOTE_INVALID',422)
    return dict(program=program.strip(), start_date=start_date, end_date=end_date,
                student_ref_digest=digest('enrollment-student-ref',actor.user_id+':'+institution_id+':'+student_ref.strip()) if student_ref else None,
                file_ids=ids, evidence_note=evidence_note.strip())


def valid_key(key):
    if not isinstance(key,str) or not 8<=len(key)<=128:raise fail('IDEMPOTENCY_KEY_INVALID',422)


def origin(conn, enrollment_id):
    origins=table('enrollment_origins')
    row=conn.execute(select(origins).where(origins.c.enrollment_id==enrollment_id)).mappings().first()
    if not row:raise fail('ENROLLMENT_NOT_FOUND',404)
    return dict(row)


def locked_enrollment(conn, enrollment_id, *, actor=None):
    first=get_row(conn,'enrollments',enrollment_id)
    institution=get_row(conn,'institutions',first['institution_id'],True)
    profiles=table('candidate_profiles')
    profile=conn.execute(select(profiles).where(profiles.c.id==first['candidate_id']).with_for_update()).mappings().one()
    enrollment=get_row(conn,'enrollments',enrollment_id,True)
    source=origin(conn,enrollment_id)
    case=get_row(conn,'verification_cases',source['case_id'],True) if source['case_id'] else None
    if (enrollment['candidate_id']!=profile['id'] or enrollment['institution_id']!=institution['id']
        or source['candidate_id']!=profile['id'] or source['institution_id']!=institution['id']
        or source['actor_user_id']!=profile['user_id']
        or (case and (case['kind']!='ENROLLMENT' or case['enrollment_id']!=enrollment_id
            or case['requester_id']!=profile['user_id'] or enrollment['verification_case_id']!=case['id']))):
        raise fail('ENROLLMENT_SCOPE_INVALID',403)
    if actor and profile['user_id']!=actor.user_id:raise fail('ENROLLMENT_NOT_FOUND',404)
    return institution,dict(profile),enrollment,source,case


def current_submission(conn, case):
    versions=table('enrollment_submissions')
    row=conn.execute(select(versions).where(versions.c.case_id==case['id'],versions.c.revision==case['current_revision'])).mappings().first()
    if not row:raise fail('ENROLLMENT_REVISION_NOT_FOUND',404)
    return dict(row)


def pin_material(conn, owner_id, ids):
    if not ids:return {}
    evidence_files(conn,owner_id,ids)
    return {fid:storage.file_snapshot(get_row(conn,'files',fid)) for fid in sorted(ids)}


class EnrollmentService:
    audit_store=AppendOnlyAuditStore()

    def _view_query(self):
        e,o,i,c,d=(table(name) for name in ('enrollments','enrollment_origins','institutions','verification_cases','enrollment_events'))
        today=now().astimezone(TASHKENT).date()
        reviewed=and_(o.c.origin=='PUBLIC',c.c.status=='APPROVED',d.c.id.is_not(None))
        current=and_(e.c.status=='VERIFIED',i.c.status=='VERIFIED',e.c.start_date<=today,
                     or_(e.c.end_date.is_(None),e.c.end_date>=today),
                     or_(and_(o.c.origin=='LEGACY_IMPORT',o.c.initial_snapshot['status'].astext=='VERIFIED'),reviewed))
        return select(e.c.id,e.c.created_at,e.c.institution_id,i.c.name.label('institution_name'),
                      e.c.program,e.c.start_date,e.c.end_date,e.c.status,o.c.origin.label('verification_origin'),
                      o.c.case_id,c.c.status.label('case_status'),c.c.current_revision.label('revision'),c.c.due_at,
                      reviewed.label('reviewed'),current.label('current_student')).select_from(
            e.join(o,o.c.enrollment_id==e.c.id).join(i,i.c.id==e.c.institution_id)
             .outerjoin(c,c.c.id==o.c.case_id).outerjoin(d,and_(d.c.case_id==c.c.id,d.c.revision==c.c.current_revision,d.c.action=='APPROVE')))

    def _report(self,conn,enrollment_id,candidate_id=None):
        e=table('enrollments');query=self._view_query().where(e.c.id==enrollment_id)
        if candidate_id:query=query.where(e.c.candidate_id==candidate_id)
        row=conn.execute(query).mappings().first()
        if not row:raise fail('ENROLLMENT_NOT_FOUND',404)
        result=dict(row)
        result['reviewed']=bool(result['reviewed']);result['current_student']=bool(result['current_student'])
        return result

    def list_own(self,actor,*,limit=50,after_id=None):
        if not 1<=limit<=100:raise fail('ENROLLMENT_LIMIT_INVALID',422)
        with candidate_transaction() as conn:
            profile=own_profile(conn,actor.user_id,'share');account_authority(conn,actor)
            e=table('enrollments');query=self._view_query().where(e.c.candidate_id==profile['id'])
            if after_id:query=query.where(e.c.id>after_id)
            rows=[dict(r) for r in conn.execute(query.order_by(e.c.id).limit(limit+1)).mappings()]
            more=len(rows)>limit;rows=rows[:limit]
            for row in rows:
                row['current_student']=bool(row['current_student']);row['reviewed']=bool(row['reviewed'])
            return {'items':rows,'next_cursor':rows[-1]['id'] if more else None}

    def detail_own(self,actor,enrollment_id):
        with candidate_transaction() as conn:
            profile=own_profile(conn,actor.user_id,'share');account_authority(conn,actor)
            return self._report(conn,enrollment_id,profile['id'])

    def _submission(self,conn,actor,case_id,revision,proposal,snapshots):
        return proof_insert(conn,'enrollment_submissions',case_id=case_id,revision=revision,
                            submitted_by_id=actor.user_id,session_id=actor.session_id,
                            auth_version=user_version(conn,actor.user_id),file_snapshots=snapshots,**proposal)

    def create(self,actor,*,institution_id,idempotency_key,**fields):
        valid_key(idempotency_key);proposal=normalize_proposal(actor,institution_id,**fields)
        request_hash=fingerprint({'institution_id':institution_id,**proposal})
        rate_limit('enrollment-intake',actor.user_id,20,3600)
        with candidate_transaction() as conn:
            inst=get_row(conn,'institutions',institution_id,True);profile=own_profile(conn,actor.user_id,True)
            origins=table('enrollment_origins')
            previous=conn.execute(select(origins).where(origins.c.actor_user_id==actor.user_id,
                origins.c.idempotency_key==idempotency_key)).mappings().first()
            if previous:
                account_authority(conn,actor)
                if previous['request_fingerprint']!=request_hash:raise fail('IDEMPOTENCY_PAYLOAD_CONFLICT')
                return self._report(conn,previous['enrollment_id'],profile['id'])
            if inst['status']!='VERIFIED':raise fail('ENROLLMENT_INSTITUTION_UNAVAILABLE',404)
            snapshots=pin_material(conn,actor.user_id,proposal['file_ids']);account_authority(conn,actor)
            submitted=bool(proposal['file_ids']);status='PENDING' if submitted else 'DECLARED'
            values={key:proposal[key] for key in ('program','start_date','end_date','student_ref_digest')}
            enrollment=insert_row(conn,'enrollments',candidate_id=profile['id'],institution_id=institution_id,status=status,**values)
            case=insert_row(conn,'verification_cases',requester_id=actor.user_id,enrollment_id=enrollment['id'],kind='ENROLLMENT',
                            status='PENDING' if submitted else 'DRAFT',current_revision=1,due_at=response_due())
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id']).values(verification_case_id=case['id']))
            proof_insert(conn,'enrollment_origins',enrollment_id=enrollment['id'],origin='PUBLIC',candidate_id=profile['id'],
                         institution_id=institution_id,actor_user_id=actor.user_id,case_id=case['id'],
                         initial_snapshot=json.loads(json.dumps({'status':status,**values},default=str)),
                         idempotency_key=idempotency_key,request_fingerprint=request_hash)
            self._submission(conn,actor,case['id'],1,proposal,snapshots)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_CREATED',entity_type='enrollment',entity_id=enrollment['id'],
                                               metadata={'case_id':case['id'],'revision':1,'status':status})
            return self._report(conn,enrollment['id'],profile['id'])

    def submit_revision(self,actor,enrollment_id,*,expected_revision,**fields):
        if type(expected_revision) is not int or expected_revision<1:raise fail('ENROLLMENT_REVISION_INVALID',422)
        with candidate_transaction() as conn:
            inst,profile,enrollment,source,case=locked_enrollment(conn,enrollment_id,actor=actor)
            if source['origin']!='PUBLIC':raise fail('LEGACY_ENROLLMENT_REQUIRES_NEW_REQUEST')
            if 'end_date' not in fields:fields['end_date']=enrollment['end_date']
            preserve_ref='student_ref' not in fields
            proposal=normalize_proposal(actor,inst['id'],**fields)
            if preserve_ref:proposal['student_ref_digest']=enrollment['student_ref_digest']
            if case['current_revision']!=expected_revision:
                account_authority(conn,actor)
                previous=current_submission(conn,case)
                if (case['current_revision']==expected_revision+1 and
                    all(previous[key]==value for key,value in proposal.items())):
                    return self._report(conn,enrollment_id,profile['id'])
                raise fail('ENROLLMENT_REVISION_CONFLICT')
            if enrollment['status'] in ('VERIFIED','ENDED','WITHDRAWN') or case['status'] not in ('DRAFT','NEEDS_INFO','REJECTED'):
                raise fail('ENROLLMENT_RESUBMISSION_STATE_CONFLICT')
            if inst['status']!='VERIFIED':raise fail('ENROLLMENT_INSTITUTION_UNAVAILABLE',404)
            if not proposal['file_ids']:raise fail('ENROLLMENT_EVIDENCE_REQUIRED',422)
            snapshots=pin_material(conn,actor.user_id,proposal['file_ids']);account_authority(conn,actor)
            revision=expected_revision+1
            self._submission(conn,actor,case['id'],revision,proposal,snapshots)
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(
                current_revision=revision,status='PENDING',assigned_reviewer_id=None,decision_reason=None,decided_at=None,updated_at=now(),due_at=response_due()))
            values={key:proposal[key] for key in ('program','start_date','end_date','student_ref_digest')}
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment_id)
                         .values(status='PENDING',updated_at=now(),**values))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_SUBMITTED',entity_type='enrollment',entity_id=enrollment_id,
                                               metadata={'case_id':case['id'],'revision':revision})
            return self._report(conn,enrollment_id,profile['id'])

    def end_own(self,actor,enrollment_id,*,idempotency_key,reason,effective_end_date=None):
        valid_key(idempotency_key)
        if not isinstance(reason,str) or not 15<=len(reason.strip())<=2000:raise fail('ENROLLMENT_REASON_INVALID',422)
        request_hash=fingerprint({'enrollment_id':enrollment_id,'reason':reason.strip(),'effective_end_date':effective_end_date})
        with candidate_transaction() as conn:
            _,_,enrollment,source,case=locked_enrollment(conn,enrollment_id,actor=actor)
            account_authority(conn,actor)
            events=table('enrollment_events')
            previous=conn.execute(select(events).where(events.c.actor_id==actor.user_id,events.c.idempotency_key==idempotency_key)).mappings().first()
            if previous:
                if previous['enrollment_id']!=enrollment_id or previous['request_fingerprint']!=request_hash:
                    raise fail('IDEMPOTENCY_PAYLOAD_CONFLICT')
                return previous['receipt']
            if enrollment['status'] in ('ENDED','WITHDRAWN'):raise fail('ENROLLMENT_ALREADY_ENDED')
            today=now().astimezone(TASHKENT).date();end=enrollment['end_date']
            if effective_end_date is not None:
                if (type(effective_end_date) is not date or effective_end_date<enrollment['start_date'] or effective_end_date>today
                    or (end is not None and effective_end_date>end)):
                    raise fail('ENROLLMENT_END_DATE_INVALID',422)
                end=effective_end_date
            elif enrollment['start_date']<=today:end=min(end or today,today)
            action='END' if enrollment['status']=='VERIFIED' else 'WITHDRAW'
            status='ENDED' if action=='END' else 'WITHDRAWN'
            receipt={'enrollment_id':enrollment_id,'case_id':source['case_id'],'status':status,'end_date':end.isoformat() if end else None}
            proof_insert(conn,'enrollment_events',enrollment_id=enrollment_id,case_id=source['case_id'],revision=case['current_revision'] if case else None,
                         action=action,actor_id=actor.user_id,session_id=actor.session_id,auth_version=user_version(conn,actor.user_id),
                         platform_grant_id=None,reason=reason.strip(),idempotency_key=idempotency_key,request_fingerprint=request_hash,receipt=receipt)
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment_id).values(status=status,end_date=end,updated_at=now()))
            if case and case['status']!='APPROVED':
                conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(status='CANCELLED',updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_'+status,entity_type='enrollment',entity_id=enrollment_id)
            return receipt

    def _moderator(self,conn,actor):
        moderator_authority(conn,actor)
        grants,roles=table('platform_role_grants'),table('role_catalog')
        return conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
            grants.c.user_id==actor.user_id,grants.c.revoked_at.is_(None),grants.c.expires_at>now(),
            roles.c.code=='MODERATOR',roles.c.scope_kind=='PLATFORM').order_by(grants.c.id).limit(1)
            .with_for_update(read=True,of=(grants,roles))).scalar_one()

    def _operator_locked(self,conn,case_id):
        first=get_row(conn,'verification_cases',case_id)
        if first['kind']!='ENROLLMENT' or not first['enrollment_id']:raise fail('UNSUPPORTED_VERIFICATION_CASE',422)
        material=locked_enrollment(conn,first['enrollment_id'])
        if not material[4] or material[4]['id']!=case_id:raise fail('ENROLLMENT_SCOPE_INVALID',403)
        return material

    def _assigned(self,actor,source,case):
        if actor.user_id==source['actor_user_id']:raise fail('SELF_REVIEW_FORBIDDEN',403)
        if case['assigned_reviewer_id']!=actor.user_id or case['status']!='IN_REVIEW':
            raise fail('ASSIGNED_REVIEW_REQUIRED',403)

    def queue(self,actor,unassigned=False,limit=50):
        if not 1<=limit<=100:raise fail('ENROLLMENT_LIMIT_INVALID',422)
        with candidate_transaction() as conn:
            self._moderator(conn,actor)
            cases=table('verification_cases')
            query=select(cases.c.id,cases.c.enrollment_id,cases.c.kind,cases.c.status,cases.c.current_revision,cases.c.due_at).where(
                cases.c.kind=='ENROLLMENT',cases.c.status.in_(OPEN),cases.c.requester_id!=actor.user_id)
            query=query.where(cases.c.assigned_reviewer_id.is_(None)) if unassigned else query.where(cases.c.assigned_reviewer_id==actor.user_id)
            return [dict(row) for row in conn.execute(query.order_by(cases.c.due_at,cases.c.id).limit(limit)).mappings()]

    def claim(self,actor,case_id):
        with candidate_transaction() as conn:
            _,_,enrollment,source,case=self._operator_locked(conn,case_id)
            grant=self._moderator(conn,actor)
            if actor.user_id==source['actor_user_id']:raise fail('SELF_REVIEW_FORBIDDEN',403)
            if enrollment['status'] in ('ENDED','WITHDRAWN') or case['status'] not in OPEN:raise fail('CASE_ALREADY_DECIDED')
            if case['assigned_reviewer_id'] not in (None,actor.user_id):raise fail('CASE_ASSIGNED_TO_OTHER',403)
            if case['assigned_reviewer_id']==actor.user_id:
                return {'id':case_id,'status':case['status'],'revision':case['current_revision']}
            proof_insert(conn,'enrollment_events',enrollment_id=enrollment['id'],case_id=case_id,revision=case['current_revision'],action='CLAIM',
                         actor_id=actor.user_id,session_id=actor.session_id,auth_version=user_version(conn,actor.user_id),platform_grant_id=grant,
                         reason='Independent enrollment review assignment.',receipt={})
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id)
                         .values(assigned_reviewer_id=actor.user_id,status='IN_REVIEW',updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_REVIEW_CLAIMED',entity_type='verification_case',entity_id=case_id)
            return {'id':case_id,'status':'IN_REVIEW','revision':case['current_revision']}

    def case_detail(self,actor,case_id):
        with candidate_transaction() as conn:
            _,_,enrollment,source,case=self._operator_locked(conn,case_id)
            self._moderator(conn,actor);self._assigned(actor,source,case)
            versions=table('enrollment_submissions');events=table('enrollment_events')
            submissions=[]
            for row in conn.execute(select(versions).where(versions.c.case_id==case_id).order_by(versions.c.revision)).mappings():
                submissions.append({key:row[key] for key in ('revision','created_at','program','start_date','end_date','evidence_note')})
                submissions[-1]['files']=[{'id':fid,'sha256':row['file_snapshots'][fid]['sha256'],
                    'byte_size':row['file_snapshots'][fid]['byte_size'],
                    'download_path':'/api/v1/operator/verification-cases/'+case_id+'/files/'+fid+'/download'
                        if row['revision']==case['current_revision'] else None} for fid in row['file_ids']]
            decisions=[dict(row) for row in conn.execute(select(events.c.revision,events.c.action,events.c.reason,events.c.created_at)
                .where(events.c.case_id==case_id,events.c.action.in_(('APPROVE','REJECT','NEEDS_INFO')))
                .order_by(events.c.revision)).mappings()]
            return {'case':case,'enrollment':self._report(conn,enrollment['id']),'submissions':submissions,'decisions':decisions}

    def download_evidence(self,actor,case_id,file_id):
        with candidate_transaction() as conn:
            _,_,_,source,case=self._operator_locked(conn,case_id);version=current_submission(conn,case)
            if file_id not in version['file_ids']:raise fail('EVIDENCE_ACCESS_DENIED',403)
            snapshots=pin_material(conn,source['actor_user_id'],[file_id])
            self._moderator(conn,actor);self._assigned(actor,source,case)
            if snapshots[file_id]!=version['file_snapshots'][file_id]:raise fail('ENROLLMENT_EVIDENCE_CHANGED')
            file=get_row(conn,'files',file_id)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_EVIDENCE_DOWNLOAD_AUTHORIZED',
                                               entity_type='verification_case',entity_id=case_id,metadata={'file_id':file_id,'revision':case['current_revision']})
            return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(file['storage_key'],reference=storage.file_reference(file))}

    def decide(self,actor,case_id,*,decision,expected_revision,reason):
        if decision not in ('APPROVE','REJECT','NEEDS_INFO') or type(expected_revision) is not int or expected_revision<1:
            raise fail('ENROLLMENT_DECISION_INVALID',422)
        if not isinstance(reason,str) or not 15<=len(reason.strip())<=2000:raise fail('ENROLLMENT_REASON_INVALID',422)
        reason=reason.strip()
        with candidate_transaction() as conn:
            inst,_,enrollment,source,case=self._operator_locked(conn,case_id)
            if decision=='APPROVE' and case['status']=='IN_REVIEW' and enrollment['status'] not in ('ENDED','WITHDRAWN'):
                version=current_submission(conn,case)
                snapshots=pin_material(conn,source['actor_user_id'],version['file_ids'])
            grant=self._moderator(conn,actor)
            if actor.user_id==source['actor_user_id']:raise fail('SELF_REVIEW_FORBIDDEN',403)
            if case['assigned_reviewer_id']!=actor.user_id:raise fail('ASSIGNED_REVIEW_REQUIRED',403)
            if case['current_revision']!=expected_revision:raise fail('ENROLLMENT_REVISION_CONFLICT')
            events=table('enrollment_events')
            previous=conn.execute(select(events).where(events.c.case_id==case_id,events.c.revision==expected_revision,
                events.c.action.in_(('APPROVE','REJECT','NEEDS_INFO')))).mappings().first()
            if previous:
                if previous['action']==decision and previous['reason']==reason and previous['actor_id']==actor.user_id:
                    return previous['receipt']
                raise fail('ENROLLMENT_DECISION_CONFLICT')
            self._assigned(actor,source,case)
            if enrollment['status'] in ('ENDED','WITHDRAWN'):raise fail('ENROLLMENT_ALREADY_ENDED')
            if decision=='APPROVE':
                if inst['status']!='VERIFIED' or not snapshots or snapshots!=version['file_snapshots']:
                    raise fail('ENROLLMENT_EVIDENCE_CHANGED')
                users=table('users')
                try:
                    owner=conn.execute(select(users.c.id).where(users.c.id==source['actor_user_id'],users.c.status=='ACTIVE')
                        .with_for_update(read=True,nowait=True)).first()
                except OperationalError as exc:
                    if getattr(exc.orig,'sqlstate',None)=='55P03':raise fail('ENROLLMENT_BUSY_RETRY') from exc
                    raise
                if not owner:raise fail('ENROLLMENT_REQUESTER_UNAVAILABLE')
            status={'APPROVE':'APPROVED','REJECT':'REJECTED','NEEDS_INFO':'NEEDS_INFO'}[decision]
            receipt={'case_id':case_id,'enrollment_id':enrollment['id'],'revision':expected_revision,'decision':decision,'case_status':status}
            event=proof_insert(conn,'enrollment_events',enrollment_id=enrollment['id'],case_id=case_id,revision=expected_revision,action=decision,
                               actor_id=actor.user_id,session_id=actor.session_id,auth_version=user_version(conn,actor.user_id),platform_grant_id=grant,
                               reason=reason,receipt=receipt)
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id)
                         .values(status=status,decision_reason=reason,decided_at=event['created_at'],updated_at=now()))
            new_status={'APPROVE':'VERIFIED','REJECT':'REJECTED','NEEDS_INFO':'PENDING'}[decision]
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id']).values(status=new_status,updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='ENROLLMENT_'+decision,entity_type='enrollment',entity_id=enrollment['id'],
                                               metadata={'case_id':case_id,'revision':expected_revision})
            return receipt


enrollment_service=EnrollmentService()
