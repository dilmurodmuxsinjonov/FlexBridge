"""Two independent review stages authorize bounded existing-staff OWNER continuity."""
from dataclasses import dataclass,field
from datetime import timedelta,timezone
import hashlib
import hmac
import json
from uuid import uuid4
from sqlalchemy import select,text,exists
from app.api.dependencies import require_platform
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import digest,rate_limit
from app.db.storage import table,transaction,now
from app.services.authority import mfa_authority,org_authority
from app.services.governance import GovernanceError
from app.services.organizations import organization_service,require_mfa,evidence_files,due_date,role_id
from app.services.owner_additions import note,owner_grant_exists
from app.services.placements import get_row,insert_row

KIND='ORG_OWNER_CONTINUITY'
STAFF=('HR','HOST_COORDINATOR','MENTOR','BILLING')
STAGES=('MODERATOR','COMPLIANCE')
OPEN=('WAITING_MODERATOR','WAITING_COMPLIANCE')
STAGE_STATE=dict(zip(STAGES,OPEN))


def proposal(conn,case_id):
    rows=table('owner_continuity_requests')
    found=conn.execute(select(rows).where(rows.c.case_id==case_id)).mappings().first()
    if not found:raise GovernanceError('CONTINUITY_REQUEST_NOT_FOUND',status_code=404)
    return dict(found)


def locked(conn,case_id):
    case=get_row(conn,'verification_cases',case_id)
    if case['kind']!=KIND:raise GovernanceError('CONTINUITY_REQUEST_NOT_FOUND',status_code=404)
    org=get_row(conn,'organizations',case['organization_id'],True)
    case=get_row(conn,'verification_cases',case_id,True)
    return org,case,proposal(conn,case_id)


def events(conn,case_id,action=None,stage=None):
    rows=table('owner_continuity_events')
    query=select(rows).where(rows.c.case_id==case_id)
    if action:query=query.where(rows.c.action==action)
    if stage:query=query.where(rows.c.stage==stage)
    return [dict(r) for r in conn.execute(query.order_by(rows.c.created_at,rows.c.id)).mappings()]


def stage_claim(conn,case_id,stage):
    rows=events(conn,case_id,'CLAIM',stage)
    return rows[0] if rows else None


def prelock_users(conn,actor,request):
    identities={actor.user_id,request['applicant_id'],*(r['user_id'] for r in request['owner_roster'])}
    identities.update(e['actor_id'] for e in events(conn,request['case_id'],'CLAIM'))
    users=table('users')
    list(conn.execute(select(users.c.id).where(users.c.id.in_(sorted(identities))).order_by(users.c.id).with_for_update(read=True)))


def contact_binding(conn,user_id,contact_id):
    contacts=table('user_contacts')
    row=conn.execute(select(contacts).where(contacts.c.id==contact_id).with_for_update(read=True)).mappings().first()
    if not row or row['user_id']!=user_id or row['revoked_at'] or row['verified_at'] is None:
        raise GovernanceError('CONTINUITY_CONTACT_NOT_VERIFIED',status_code=403)
    binding=digest('owner-continuity-contact',json.dumps([row['id'],user_id,row['channel'],row['normalized_value'],
        row['verified_at'].astimezone(timezone.utc).isoformat()],separators=(',',':')))
    return dict(row),binding


def stage_authority(conn,actor,stage,grant_id=None):
    if stage not in STAGES:raise GovernanceError('INVALID_CONTINUITY_STAGE',status_code=422)
    mfa_authority(conn,actor)
    grants,roles=table('platform_role_grants'),table('role_catalog')
    query=select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.user_id==actor.user_id,grants.c.revoked_at.is_(None),grants.c.expires_at>now(),
        roles.c.scope_kind=='PLATFORM',roles.c.code==stage)
    if grant_id:query=query.where(grants.c.id==grant_id)
    found=conn.execute(query.order_by(grants.c.id).with_for_update(read=True,of=(grants,roles))).first()
    if not found:raise GovernanceError('FORBIDDEN_ROLE',status_code=403)
    return found.id


def independent(conn,actor,request,stage):
    members=table('org_memberships')
    related=conn.execute(select(members.c.id).where(members.c.organization_id==request['organization_id'],
        members.c.user_id==actor.user_id).limit(1)).first()
    if actor.user_id==request['applicant_id'] or related:
        raise GovernanceError('SELF_REVIEW_FORBIDDEN',status_code=403)
    other='COMPLIANCE' if stage=='MODERATOR' else 'MODERATOR'
    claimed=stage_claim(conn,request['case_id'],other)
    if claimed and claimed['actor_id']==actor.user_id:
        raise GovernanceError('CONTINUITY_DISTINCT_REVIEWERS_REQUIRED',status_code=403)


def claim_current(conn,claim):
    users,grants,roles=table('users'),table('platform_role_grants'),table('role_catalog')
    return conn.execute(select(grants.c.id).join(users,users.c.id==grants.c.user_id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.id==claim['authority_grant_id'],grants.c.user_id==claim['actor_id'],grants.c.revoked_at.is_(None),
        grants.c.expires_at>now(),users.c.status=='ACTIVE',users.c.auth_version==claim['auth_version'],
        roles.c.code==claim['stage'],roles.c.scope_kind=='PLATFORM').with_for_update(read=True,of=(users,grants,roles))).first() is not None


def intent_current(conn,request):
    members,grants,roles=table('org_memberships'),table('org_role_grants'),table('role_catalog')
    member_ids=[request['membership_id'],*(r['membership_id'] for r in request['owner_roster'])]
    grant_ids=[request['staff_grant_id'],*(r['grant_id'] for r in request['owner_roster'])]
    list(conn.execute(select(members.c.id).where(members.c.id.in_(member_ids)).order_by(members.c.id).with_for_update(read=True)))
    list(conn.execute(select(grants.c.id).where(grants.c.id.in_(grant_ids)).order_by(grants.c.id).with_for_update(read=True)))
    list(conn.execute(select(roles.c.id).where(roles.c.scope_kind=='ORG',roles.c.code.in_((*STAFF,'OWNER'))).order_by(roles.c.id).with_for_update(read=True)))
    try:
        contact,binding=contact_binding(conn,request['applicant_id'],request['contact_id'])
        if contact['verified_at']!=request['contact_verified_at'] or not hmac.compare_digest(binding,request['contact_digest']):return False
        evidence_files(conn,request['applicant_id'],request['evidence_file_ids'])
    except GovernanceError:
        return False
    return conn.execute(text('SELECT flexbridge.continuity_intent_valid(:case,false)'),{'case':request['case_id']}).scalar_one()


@dataclass
class OwnerContinuityService:
    audit_store:AppendOnlyAuditStore=field(default_factory=AppendOnlyAuditStore)

    def _report(self,conn,case,request,**extra):
        decisions=[{k:e[k] for k in ('stage','action','reason','created_at')} for e in events(conn,case['id']) if e['action']!='CLAIM']
        return {'id':case['id'],'organization_id':request['organization_id'],'status':case['status'],'revision':1,
            'created_at':request['created_at'],'consent_expires_at':request['expires_at'],
            'decision_reason':case['decision_reason'],'decisions':decisions,**extra}

    def _state(self,conn,case,request,status,reason,actor_id,action):
        at=now();terminal=status not in OPEN
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(
            status=status,decision_reason=reason if terminal else None,decided_at=at if terminal else None,updated_at=at))
        conn.execute(table('recovery_requests').update().where(table('recovery_requests').c.id==request['recovery_id']).values(
            status='COMPLETED' if status=='APPROVED' else status,resolved_at=at if terminal else None,updated_at=at))
        self.audit_store.append_audit_event(actor_id=actor_id,action=action,entity_type='verification_case',entity_id=case['id'],
            metadata={'revision':1,'reason':reason,'status':status})
        return get_row(conn,'verification_cases',case['id'])

    def _prune(self,conn,case,request,actor):
        if case['status'] not in OPEN:return None
        if not intent_current(conn,request) or any(not claim_current(conn,c) for c in events(conn,case['id'],'CLAIM')):
            case=self._state(conn,case,request,'EXPIRED','Original consent or authority is no longer current',actor.user_id,'OWNER_CONTINUITY_EXPIRED')
            return {'id':case['id'],'organization_id':request['organization_id'],'status':case['status'],
                'revision':1,'closed_automatically':True}
        return None

    def submit(self,actor,org_id,*,contact_id,file_ids,evidence_note,idempotency_key):
        require_mfa(actor);evidence_note=note(evidence_note)
        if not isinstance(idempotency_key,str) or not 8<=len(idempotency_key)<=128:raise GovernanceError('INVALID_IDEMPOTENCY_KEY',status_code=422)
        rate_limit('owner-continuity-intake',actor.user_id,10,86400)
        ids=sorted(str(v) for v in file_ids)
        fingerprint=hashlib.sha256(json.dumps([org_id,contact_id,ids,evidence_note],separators=(',',':')).encode()).hexdigest()
        with transaction() as conn:
            org=get_row(conn,'organizations',org_id,True);mfa_authority(conn,actor)
            requests=table('owner_continuity_requests');cases=table('verification_cases')
            old=conn.execute(select(requests).where(requests.c.applicant_id==actor.user_id,requests.c.idempotency_key==idempotency_key)).mappings().first()
            if old:
                if old['request_fingerprint']!=fingerprint:raise GovernanceError('IDEMPOTENCY_PAYLOAD_CONFLICT')
                previous_case=get_row(conn,'verification_cases',old['case_id'],True)
                prelock_users(conn,actor,old)
                closed=self._prune(conn,previous_case,old,actor)
                if closed:return {**closed,'idempotent_replay':True}
                return self._report(conn,previous_case,old,idempotent_replay=True)
            member=org_authority(conn,actor.user_id,org_id,*STAFF)
            if org['status']!='VERIFIED':raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            if owner_grant_exists(conn,member['id']):raise GovernanceError('CONTINUITY_APPLICANT_ALREADY_OWNER')
            pending=conn.execute(select(cases.c.id).where(cases.c.organization_id==org_id,cases.c.kind==KIND,cases.c.status.in_(OPEN))).scalar_one_or_none()
            if pending:
                pending_case=get_row(conn,'verification_cases',pending,True);pending_request=proposal(conn,pending)
                prelock_users(conn,actor,pending_request)
                if not self._prune(conn,pending_case,pending_request,actor):raise GovernanceError('CONTINUITY_REQUEST_ALREADY_PENDING')
            contact,binding=contact_binding(conn,actor.user_id,contact_id)
            roster=conn.execute(text('SELECT flexbridge.continuity_owner_roster(:org)'),{'org':org_id}).scalar_one()
            if not 1<=len(roster)<=256:raise GovernanceError('CONTINUITY_ACTIVE_OWNER_ROSTER_REQUIRED',status_code=422)
            ids=evidence_files(conn,actor.user_id,ids);created=now()
            recovery=insert_row(conn,'recovery_requests',user_id=actor.user_id,kind=KIND,status=OPEN[0],
                requester_contact_digest=binding,evidence_file_id=ids[0])
            case=insert_row(conn,'verification_cases',requester_id=actor.user_id,organization_id=org_id,kind=KIND,
                status=OPEN[0],current_revision=1,due_at=due_date())
            organization_service._submission(conn,case,member['id'],{'action':'STAFF_OWNER_CONTINUITY'},ids,evidence_note)
            request=dict(case_id=case['id'],recovery_id=recovery['id'],organization_id=org_id,applicant_id=actor.user_id,
                membership_id=member['id'],staff_grant_id=member['_authority_grant_id'],auth_version=get_row(conn,'users',actor.user_id)['auth_version'],
                session_id=actor.session_id,contact_id=contact_id,contact_digest=binding,contact_verified_at=contact['verified_at'],
                created_at=created,expires_at=created+timedelta(hours=24),owner_roster=roster,evidence_file_ids=sorted(ids),
                evidence_note=evidence_note,idempotency_key=idempotency_key,request_fingerprint=fingerprint)
            prelock_users(conn,actor,request)
            conn.execute(requests.insert().values(**request))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_CONTINUITY_REQUESTED',entity_type='verification_case',
                entity_id=case['id'],metadata={'revision':1,'owner_count':len(roster)})
            return self._report(conn,get_row(conn,'verification_cases',case['id']),request,idempotent_replay=False)

    def read(self,actor,case_id):
        require_mfa(actor)
        with transaction() as conn:
            org,case,request=locked(conn,case_id);prelock_users(conn,actor,request);mfa_authority(conn,actor)
            if actor.user_id!=request['applicant_id']:raise GovernanceError('CONTINUITY_APPLICANT_ONLY',status_code=403)
            closed=self._prune(conn,case,request,actor)
            return closed or self._report(conn,case,request)

    def withdraw(self,actor,case_id,reason):
        require_mfa(actor);reason=note(reason,2000)
        with transaction() as conn:
            org,case,request=locked(conn,case_id);prelock_users(conn,actor,request);mfa_authority(conn,actor)
            if actor.user_id!=request['applicant_id']:raise GovernanceError('CONTINUITY_APPLICANT_ONLY',status_code=403)
            if case['status'] not in OPEN:
                prior=table('audit_events')
                own=conn.execute(select(prior.c.id).where(prior.c.object_key==case_id,prior.c.actor_id==actor.user_id,
                    prior.c.action=='OWNER_CONTINUITY_WITHDRAWN')).first()
                if case['status']=='CANCELLED' and case['decision_reason']==reason and own:return self._report(conn,case,request,idempotent_replay=True)
                raise GovernanceError('CONTINUITY_CASE_CLOSED')
            case=self._state(conn,case,request,'CANCELLED',reason,actor.user_id,'OWNER_CONTINUITY_WITHDRAWN')
            return self._report(conn,case,request,idempotent_replay=False)

    def _event(self,conn,actor,stage,action,request,grant_id,**extra):
        row=dict(id=str(uuid4()),case_id=request['case_id'],stage=stage,action=action,actor_id=actor.user_id,
            authority_grant_id=grant_id,auth_version=get_row(conn,'users',actor.user_id)['auth_version'],
            session_id=actor.session_id,created_at=now(),claim_id=None,reason=None,
            result_owner_grant_id=None,ownership_event_id=None)
        row.update(extra)
        conn.execute(table('owner_continuity_events').insert().values(**row))
        return row

    def queue(self,actor,stage,unassigned=False,limit=50):
        require_platform(actor,stage);require_mfa(actor)
        if stage not in STAGES or type(limit) is not int or not 1<=limit<=100:raise GovernanceError('INVALID_CONTINUITY_PAGE',status_code=422)
        with transaction() as conn:
            stage_authority(conn,actor,stage)
            cases,requests,review,members=table('verification_cases'),table('owner_continuity_requests'),table('owner_continuity_events'),table('org_memberships')
            own_claim=exists(select(review.c.id).where(review.c.case_id==cases.c.id,review.c.stage==stage,
                review.c.action=='CLAIM',review.c.actor_id==actor.user_id))
            any_claim=exists(select(review.c.id).where(review.c.case_id==cases.c.id,review.c.stage==stage,review.c.action=='CLAIM'))
            other_stage_self=exists(select(review.c.id).where(review.c.case_id==cases.c.id,review.c.stage!=stage,
                review.c.action=='CLAIM',review.c.actor_id==actor.user_id))
            related=exists(select(members.c.id).where(members.c.organization_id==cases.c.organization_id,members.c.user_id==actor.user_id))
            query=select(cases.c.id,cases.c.organization_id,cases.c.status,cases.c.due_at,requests.c.created_at).join(
                requests,requests.c.case_id==cases.c.id).where(cases.c.kind==KIND,cases.c.status==STAGE_STATE[stage],
                requests.c.applicant_id!=actor.user_id,~related,~other_stage_self,~any_claim if unassigned else own_claim)
            return [dict(r) for r in conn.execute(query.order_by(cases.c.due_at,cases.c.id).limit(limit)).mappings()]

    def claim(self,actor,case_id,stage):
        require_platform(actor,stage);require_mfa(actor)
        with transaction() as conn:
            org,case,request=locked(conn,case_id);prelock_users(conn,actor,request)
            grant=stage_authority(conn,actor,stage);independent(conn,actor,request,stage)
            closed=self._prune(conn,case,request,actor)
            if closed:return closed
            claimed=stage_claim(conn,case_id,stage)
            if claimed:
                if claimed['actor_id']!=actor.user_id:raise GovernanceError('CASE_ASSIGNED_TO_OTHER',status_code=403)
                stage_authority(conn,actor,stage,claimed['authority_grant_id'])
                if not claim_current(conn,claimed):raise GovernanceError('CONTINUITY_CLAIM_NO_LONGER_CURRENT',status_code=403)
                return self._report(conn,case,request,idempotent_replay=True,assigned_stage=stage)
            if case['status']!=STAGE_STATE[stage]:raise GovernanceError('CONTINUITY_STAGE_CONFLICT')
            self._event(conn,actor,stage,'CLAIM',request,grant)
            if stage=='MODERATOR':
                conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id)
                    .values(assigned_reviewer_id=actor.user_id,updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_CONTINUITY_STAGE_CLAIMED',
                entity_type='verification_case',entity_id=case_id,metadata={'stage':stage,'revision':1})
            return self._report(conn,get_row(conn,'verification_cases',case_id),request,idempotent_replay=False,assigned_stage=stage)

    def _review_context(self,conn,actor,case_id,stage):
        org,case,request=locked(conn,case_id);prelock_users(conn,actor,request)
        stage_authority(conn,actor,stage);independent(conn,actor,request,stage)
        claimed=stage_claim(conn,case_id,stage)
        if not claimed or claimed['actor_id']!=actor.user_id:raise GovernanceError('ASSIGNED_REVIEW_REQUIRED',status_code=403)
        closed=self._prune(conn,case,request,actor)
        if not closed:
            stage_authority(conn,actor,stage,claimed['authority_grant_id'])
            if not claim_current(conn,claimed):raise GovernanceError('CONTINUITY_CLAIM_NO_LONGER_CURRENT',status_code=403)
        return org,case,request,claimed,closed

    def detail(self,actor,case_id,stage):
        require_platform(actor,stage);require_mfa(actor)
        with transaction() as conn:
            org,case,request,claimed,closed=self._review_context(conn,actor,case_id,stage)
            if closed:return closed
            applicant=get_row(conn,'users',request['applicant_id'])
            owners=[{'user_id':r['user_id'],'membership_id':r['membership_id'],
                'display_name':get_row(conn,'users',r['user_id'])['display_name']} for r in request['owner_roster']]
            reviewers=[{'stage':e['stage'],'user_id':e['actor_id'],
                'display_name':get_row(conn,'users',e['actor_id'])['display_name']} for e in events(conn,case_id,'CLAIM')]
            return {**self._report(conn,case,request),'organization':{k:org[k] for k in ('id','tax_id','legal_name','public_name','region','description','website')},
                'applicant':{'id':applicant['id'],'display_name':applicant['display_name'],'membership_id':request['membership_id']},
                'owner_roster':owners,'reviewers':reviewers,'evidence_file_ids':request['evidence_file_ids'],'evidence_note':request['evidence_note']}

    def download(self,actor,case_id,stage,file_id):
        from app.adapters import storage
        require_platform(actor,stage);require_mfa(actor)
        with transaction() as conn:
            org,case,request,claimed,closed=self._review_context(conn,actor,case_id,stage)
            if closed:return closed
            if file_id not in request['evidence_file_ids']:raise GovernanceError('EVIDENCE_ACCESS_DENIED',status_code=403)
            evidence_files(conn,request['applicant_id'],[file_id]);file=get_row(conn,'files',file_id)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_CONTINUITY_EVIDENCE_AUTHORIZED',
                entity_type='verification_case',entity_id=case_id,metadata={'stage':stage,'file_id':file_id})
            return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(file['storage_key'],reference=storage.file_reference(file))}

    def decide(self,actor,case_id,stage,*,decision,expected_revision,reason):
        require_platform(actor,stage);require_mfa(actor);reason=note(reason,2000)
        allowed=('RECOMMEND','REJECT','NEEDS_INFO') if stage=='MODERATOR' else ('APPROVE','REJECT','NEEDS_INFO')
        if stage not in STAGES or type(expected_revision) is not int or expected_revision!=1 or decision not in allowed:
            raise GovernanceError('INVALID_CONTINUITY_DECISION',status_code=422)
        with transaction() as conn:
            org,case,request,claimed,closed=self._review_context(conn,actor,case_id,stage)
            if closed:return closed
            prior=[e for e in events(conn,case_id,stage=stage) if e['action']!='CLAIM']
            if prior:
                previous=prior[0]
                if previous['action']!=decision or previous['reason']!=reason:raise GovernanceError('CONTINUITY_DECISION_CONFLICT')
                return self._report(conn,case,request,idempotent_replay=True,ownership_event_id=previous['ownership_event_id'])
            if case['status']!=STAGE_STATE[stage]:raise GovernanceError('CONTINUITY_STAGE_CONFLICT')
            event_id=None;extra={}
            if decision=='APPROVE':
                # _prune held original intent, roster, current claims/contact/evidence through this UOW.
                grant=insert_row(conn,'org_role_grants',membership_id=request['membership_id'],role_id=role_id(conn,'OWNER'),granted_by_id=actor.user_id)
                event_id=str(uuid4());extra={'result_owner_grant_id':grant['id'],'ownership_event_id':event_id}
            self._event(conn,actor,stage,decision,request,claimed['authority_grant_id'],claim_id=claimed['id'],reason=reason,**extra)
            if decision=='APPROVE':
                insert_row(conn,'org_ownership_events',id=event_id,organization_id=org['id'],new_membership_id=request['membership_id'],
                    verification_case_id=case_id,approved_by_id=actor.user_id,effective_at=grant['created_at'])
            state={'RECOMMEND':'WAITING_COMPLIANCE','APPROVE':'APPROVED','REJECT':'REJECTED','NEEDS_INFO':'NEEDS_INFO'}[decision]
            case=self._state(conn,case,request,state,reason,actor.user_id,'OWNER_CONTINUITY_'+decision)
            return self._report(conn,case,request,idempotent_replay=False,ownership_event_id=event_id)

    def owner_pending(self,actor,org_id):
        require_mfa(actor)
        with transaction() as conn:
            get_row(conn,'organizations',org_id,True);mfa_authority(conn,actor);org_authority(conn,actor.user_id,org_id,'OWNER')
            cases=table('verification_cases')
            found=conn.execute(select(cases.c.id).where(cases.c.organization_id==org_id,cases.c.kind==KIND,cases.c.status.in_(OPEN))).scalar_one_or_none()
            if not found:return {'items':[]}
            case=get_row(conn,'verification_cases',found,True);request=proposal(conn,found);prelock_users(conn,actor,request)
            if self._prune(conn,case,request,actor):return {'items':[]}
            applicant=get_row(conn,'users',request['applicant_id'])
            return {'items':[{'id':found,'status':case['status'],'created_at':request['created_at'],
                'applicant_id':applicant['id'],'applicant_display_name':applicant['display_name']}]}

    def object(self,actor,org_id,case_id,reason):
        require_mfa(actor);reason=note(reason,2000)
        with transaction() as conn:
            org,case,request=locked(conn,case_id);prelock_users(conn,actor,request);mfa_authority(conn,actor)
            if org['id']!=org_id:raise GovernanceError('ORG_SCOPE_FORBIDDEN',status_code=403)
            org_authority(conn,actor.user_id,org_id,'OWNER')
            if case['status'] not in OPEN:
                audits=table('audit_events')
                prior=conn.execute(select(audits.c.id).where(audits.c.object_key==case_id,audits.c.actor_id==actor.user_id,
                    audits.c.action=='OWNER_CONTINUITY_OBJECTED')).first()
                if case['status']=='CANCELLED' and case['decision_reason']==reason and prior:return {'id':case_id,'status':'CANCELLED','idempotent_replay':True}
                raise GovernanceError('CONTINUITY_CASE_CLOSED')
            case=self._state(conn,case,request,'CANCELLED',reason,actor.user_id,'OWNER_CONTINUITY_OBJECTED')
            return {'id':case_id,'status':case['status'],'idempotent_replay':False}


owner_continuity_service=OwnerContinuityService()
