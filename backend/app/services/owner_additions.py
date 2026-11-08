"""An additional OWNER needs a current owner, named staff consent and independent review."""
from dataclasses import dataclass,field
from datetime import timedelta
import hashlib
import hmac
import json
from uuid import uuid4
from sqlalchemy import select
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import digest,rate_limit
from app.db.storage import table,transaction,now
from app.services.authority import mfa_authority,moderator_authority,org_authority
from app.services.governance import GovernanceError
from app.services.organizations import organization_service,require_mfa,evidence_files,due_date,role_id
from app.services.placements import get_row,insert_row

KIND='ORG_OWNER_ADDITION'
STAFF=('HR','HOST_COORDINATOR','MENTOR','BILLING')
FINAL=('APPROVED','REJECTED','CANCELLED')


def note(value,limit=4000):
    if not isinstance(value,str) or not 15<=len(value.strip())<=limit:
        raise GovernanceError('OWNERSHIP_REASON_REQUIRED',status_code=422)
    return value.strip()


def proposal(conn,case_id):
    requests=table('owner_addition_requests')
    row=conn.execute(select(requests).where(requests.c.case_id==case_id)).mappings().first()
    if not row:raise GovernanceError('OWNER_PROPOSAL_NOT_FOUND',status_code=404)
    return dict(row)


def locked_case(conn,case_id):
    first=get_row(conn,'verification_cases',case_id)
    if first['kind']!=KIND or not first['organization_id']:
        raise GovernanceError('UNSUPPORTED_OWNER_CASE',status_code=422)
    org=get_row(conn,'organizations',first['organization_id'],True)
    case=get_row(conn,'verification_cases',case_id,True)
    return org,case,proposal(conn,case_id)


def latest_consent(conn,case_id):
    events=table('owner_addition_consents')
    row=conn.execute(select(events).where(events.c.case_id==case_id).order_by(events.c.event_no.desc()).limit(1)).mappings().first()
    return dict(row) if row else None


def owner_grant_exists(conn,membership_id):
    grants,roles=table('org_role_grants'),table('role_catalog')
    return conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.membership_id==membership_id,grants.c.revoked_at.is_(None),roles.c.scope_kind=='ORG',roles.c.code=='OWNER')).first() is not None


def target_staff(conn,request):
    member=org_authority(conn,request['target_user_id'],request['organization_id'],*STAFF)
    if member['id']!=request['target_membership_id']:
        raise GovernanceError('OWNER_TARGET_MEMBERSHIP_CHANGED')
    return member,get_row(conn,'users',request['target_user_id'])


def consent_staff_grant_current(conn,request,consent):
    grants,roles=table('org_role_grants'),table('role_catalog')
    return conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.id==consent['target_staff_grant_id'],grants.c.membership_id==request['target_membership_id'],
        grants.c.revoked_at.is_(None),roles.c.scope_kind=='ORG',roles.c.code.in_(STAFF))
        .with_for_update(read=True,of=(grants,roles))).first() is not None


def current_contact(conn,user_id,contact_id):
    contacts=table('user_contacts')
    row=conn.execute(select(contacts).where(contacts.c.id==contact_id).with_for_update(read=True)).mappings().first()
    if not row or row['user_id']!=user_id or row['verified_at'] is None or row['revoked_at']:
        raise GovernanceError('OWNER_CONTACT_NOT_VERIFIED',status_code=403)
    binding=digest('owner-consent-contact',json.dumps([row['id'],user_id,row['channel'],row['normalized_value'],
        row['verified_at'].isoformat()],separators=(',',':')))
    return dict(row),binding


def valid_consent(conn,case,request,target):
    consent=latest_consent(conn,case['id'])
    if not consent or consent['revision']!=case['current_revision'] or consent['decision']!='ACCEPT':
        raise GovernanceError('OWNER_TARGET_CONSENT_REQUIRED')
    if (consent['expires_at']<=now() or consent['auth_version']!=target['auth_version']
        or not consent_staff_grant_current(conn,request,consent)):
        raise GovernanceError('OWNER_TARGET_CONSENT_STALE')
    contact,binding=current_contact(conn,target['id'],consent['contact_id'])
    if contact['verified_at']!=consent['contact_verified_at'] or not hmac.compare_digest(binding,consent['contact_digest']):
        raise GovernanceError('OWNER_TARGET_CONSENT_STALE')
    return consent


def independent(conn,actor,request):
    members=table('org_memberships')
    related=conn.execute(select(members.c.id).where(members.c.organization_id==request['organization_id'],
        members.c.user_id==actor.user_id).limit(1)).first()
    if actor.user_id in (request['requester_user_id'],request['target_user_id']) or related:
        raise GovernanceError('SELF_REVIEW_FORBIDDEN',status_code=403)


@dataclass
class OwnerAdditionService:
    audit_store:AppendOnlyAuditStore=field(default_factory=AppendOnlyAuditStore)

    def _report(self,conn,case,request,**extra):
        consent=latest_consent(conn,case['id'])
        return {'id':case['id'],'organization_id':request['organization_id'],
            'requester_user_id':request['requester_user_id'],'target_user_id':request['target_user_id'],
            'target_membership_id':request['target_membership_id'],'requested_role':'OWNER',
            'status':case['status'],'revision':case['current_revision'],'decision_reason':case['decision_reason'],
            'consent':None if consent is None else {key:consent[key] for key in ('decision','revision','created_at','expires_at')},**extra}

    def submit(self,actor,org_id,*,target_membership_id,file_ids,evidence_note,idempotency_key):
        require_mfa(actor);evidence_note=note(evidence_note)
        if not isinstance(idempotency_key,str) or not 8<=len(idempotency_key)<=128:
            raise GovernanceError('INVALID_IDEMPOTENCY_KEY',status_code=422)
        rate_limit('owner-addition-request',actor.user_id,20,3600)
        fingerprint=hashlib.sha256(json.dumps([org_id,target_membership_id,sorted(str(v) for v in file_ids),
            evidence_note],separators=(',',':')).encode()).hexdigest()
        with transaction() as conn:
            org=get_row(conn,'organizations',org_id,True);mfa_authority(conn,actor)
            requester=org_authority(conn,actor.user_id,org_id,'OWNER')
            requests,cases=table('owner_addition_requests'),table('verification_cases')
            existing=conn.execute(select(requests).where(requests.c.requester_user_id==actor.user_id,
                requests.c.idempotency_key==idempotency_key)).mappings().first()
            if existing:
                if existing['request_fingerprint']!=fingerprint:raise GovernanceError('IDEMPOTENCY_PAYLOAD_CONFLICT')
                return self._report(conn,get_row(conn,'verification_cases',existing['case_id']),existing,idempotent_replay=True)
            if org['status']!='VERIFIED':raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            target=get_row(conn,'org_memberships',target_membership_id)
            if target['organization_id']!=org_id:raise GovernanceError('ORG_SCOPE_FORBIDDEN',status_code=403)
            if target['user_id']==actor.user_id:raise GovernanceError('OWNER_TARGET_MUST_DIFFER',status_code=422)
            request={'organization_id':org_id,'target_user_id':target['user_id'],'target_membership_id':target['id']}
            target_staff(conn,request)
            if owner_grant_exists(conn,target['id']):raise GovernanceError('TARGET_ALREADY_OWNER')
            pending=conn.execute(select(requests.c.case_id).join(cases,cases.c.id==requests.c.case_id).where(
                requests.c.organization_id==org_id,requests.c.target_membership_id==target['id'],cases.c.status.not_in(FINAL))).first()
            if pending:raise GovernanceError('OWNER_REQUEST_ALREADY_PENDING')
            user=get_row(conn,'users',actor.user_id)
            case=insert_row(conn,'verification_cases',requester_id=actor.user_id,organization_id=org_id,kind=KIND,
                status='WAITING_CONSENT',current_revision=1,due_at=due_date())
            fields={'action':'ADD_OWNER','target_membership_id':target['id'],'target_user_id':target['user_id']}
            organization_service._submission(conn,case,requester['id'],fields,file_ids,evidence_note)
            request={**request,'case_id':case['id'],'created_at':now(),'requester_user_id':actor.user_id,
                'requester_membership_id':requester['id'],'requester_auth_version':user['auth_version'],
                'requester_grant_id':requester['_authority_grant_id'],
                'requester_session_id':actor.session_id,'idempotency_key':idempotency_key,'request_fingerprint':fingerprint}
            conn.execute(requests.insert().values(**request))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_ADDITION_REQUESTED',
                entity_type='verification_case',entity_id=case['id'],metadata={'target_membership_id':target['id'],'revision':1})
            # Fetch defaults as well as explicitly supplied fields.
            return self._report(conn,get_row(conn,'verification_cases',case['id']),request,idempotent_replay=False)

    def consent(self,actor,case_id,*,expected_revision,decision,contact_id=None):
        require_mfa(actor)
        if type(expected_revision) is not int or decision not in ('ACCEPT','DECLINE'):
            raise GovernanceError('INVALID_OWNER_CONSENT',status_code=422)
        if (decision=='ACCEPT')!=(contact_id is not None):raise GovernanceError('OWNER_CONTACT_REQUIRED',status_code=422)
        rate_limit('owner-addition-consent',actor.user_id,30,600)
        with transaction() as conn:
            org,case,request=locked_case(conn,case_id);mfa_authority(conn,actor)
            if actor.user_id!=request['target_user_id']:raise GovernanceError('OWNER_TARGET_ONLY',status_code=403)
            target_member,_=target_staff(conn,request)
            if case['current_revision']!=expected_revision:raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT')
            latest=latest_consent(conn,case_id)
            if case['status'] in FINAL:
                if case['status']=='CANCELLED' and decision=='DECLINE' and latest and latest['decision']=='DECLINE':
                    return self._report(conn,case,request,idempotent_replay=True)
                raise GovernanceError('OWNER_REQUEST_CLOSED')
            if case['status']=='NEEDS_INFO' and decision=='ACCEPT':raise GovernanceError('OWNER_EVIDENCE_RESUBMISSION_REQUIRED')
            user=get_row(conn,'users',actor.user_id);created=now()
            values=dict(id=str(uuid4()),case_id=case_id,created_at=created,revision=expected_revision,
                event_no=1 if not latest else latest['event_no']+1,actor_id=actor.user_id,auth_version=user['auth_version'],
                session_id=actor.session_id,decision=decision,target_staff_grant_id=None,
                contact_id=None,contact_digest=None,contact_verified_at=None,expires_at=None)
            if decision=='ACCEPT':
                contact,binding=current_contact(conn,actor.user_id,contact_id)
                if (latest and latest['revision']==expected_revision and latest['decision']=='ACCEPT'
                    and latest['auth_version']==user['auth_version'] and latest['expires_at']>created
                    and latest['contact_id']==contact_id and latest['contact_verified_at']==contact['verified_at']
                    and consent_staff_grant_current(conn,request,latest)
                    and hmac.compare_digest(latest['contact_digest'],binding)):
                    return self._report(conn,case,request,idempotent_replay=True)
                values.update(target_staff_grant_id=target_member['_authority_grant_id'],contact_id=contact_id,
                    contact_digest=binding,contact_verified_at=contact['verified_at'],expires_at=created+timedelta(hours=24))
            conn.execute(table('owner_addition_consents').insert().values(**values))
            state='CANCELLED' if decision=='DECLINE' else ('IN_REVIEW' if case['assigned_reviewer_id'] else 'PENDING')
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id)
                .values(status=state,decision_reason='Declined by target' if decision=='DECLINE' else None,
                    decided_at=created if decision=='DECLINE' else None,updated_at=created))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_TARGET_'+decision,
                entity_type='verification_case',entity_id=case_id,metadata={'revision':expected_revision,'event_no':values['event_no']})
            return self._report(conn,get_row(conn,'verification_cases',case_id),request,idempotent_replay=False)

    def read(self,actor,case_id):
        require_mfa(actor)
        with transaction() as conn:
            org,case,request=locked_case(conn,case_id);mfa_authority(conn,actor)
            if actor.user_id==request['requester_user_id']:
                org_authority(conn,actor.user_id,org['id'],'OWNER')
            elif actor.user_id!=request['target_user_id']:
                raise GovernanceError('OWNER_REQUEST_SCOPE_FORBIDDEN',status_code=403)
            return self._report(conn,case,request)

    def target_queue(self,actor,limit=50,after=None):
        require_mfa(actor)
        if type(limit) is not int or not 1<=limit<=100:raise GovernanceError('INVALID_PAGE_LIMIT',status_code=422)
        with transaction() as conn:
            mfa_authority(conn,actor)
            requests,cases,orgs=table('owner_addition_requests'),table('verification_cases'),table('organizations')
            query=select(requests.c.case_id,requests.c.organization_id,orgs.c.public_name,cases.c.status,
                cases.c.current_revision,requests.c.created_at).select_from(requests.join(cases,cases.c.id==requests.c.case_id)
                    .join(orgs,orgs.c.id==requests.c.organization_id)).where(requests.c.target_user_id==actor.user_id)
            if after:query=query.where(requests.c.case_id>after)
            rows=[dict(r) for r in conn.execute(query.order_by(requests.c.case_id).limit(limit+1)).mappings()]
            return {'items':rows[:limit],'next_cursor':rows[limit-1]['case_id'] if len(rows)>limit else None}

    def _requester(self,conn,actor,request,require_original_grant=True):
        mfa_authority(conn,actor)
        if actor.user_id!=request['requester_user_id']:raise GovernanceError('OWNER_REQUESTER_ONLY',status_code=403)
        member=org_authority(conn,actor.user_id,request['organization_id'],'OWNER')
        if (member['id']!=request['requester_membership_id'] or (require_original_grant
            and member['_authority_grant_id']!=request['requester_grant_id'])):
            raise GovernanceError('REQUESTER_NO_LONGER_AUTHORIZED')
        return get_row(conn,'users',actor.user_id)

    def resubmit(self,actor,case_id,*,expected_revision,file_ids,evidence_note):
        require_mfa(actor);evidence_note=note(evidence_note)
        if type(expected_revision) is not int:raise GovernanceError('INVALID_REVISION',status_code=422)
        with transaction() as conn:
            org,case,request=locked_case(conn,case_id);user=self._requester(conn,actor,request)
            if case['status']!='NEEDS_INFO' or case['current_revision']!=expected_revision:
                raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT')
            if user['auth_version']!=request['requester_auth_version']:raise GovernanceError('OWNER_REQUEST_AUTH_CHANGED')
            if org['status']!='VERIFIED':raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            target_staff(conn,request)
            revised={**case,'current_revision':expected_revision+1,'status':'WAITING_CONSENT'}
            fields={'action':'ADD_OWNER','target_membership_id':request['target_membership_id'],'target_user_id':request['target_user_id']}
            organization_service._submission(conn,revised,request['requester_membership_id'],fields,file_ids,evidence_note)
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id).values(
                status='WAITING_CONSENT',current_revision=revised['current_revision'],decision_reason=None,decided_at=None,
                due_at=due_date(),updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_ADDITION_RESUBMITTED',
                entity_type='verification_case',entity_id=case_id,metadata={'revision':revised['current_revision']})
            return self._report(conn,get_row(conn,'verification_cases',case_id),request)

    def cancel(self,actor,case_id,reason):
        require_mfa(actor);reason=note(reason,2000)
        with transaction() as conn:
            org,case,request=locked_case(conn,case_id);self._requester(conn,actor,request,require_original_grant=False)
            if case['status'] in FINAL:
                audits=table('audit_events')
                prior=conn.execute(select(audits.c.id).where(audits.c.object_key==case_id,
                    audits.c.actor_id==actor.user_id,audits.c.action=='OWNER_ADDITION_CANCELLED')).first()
                if case['status']=='CANCELLED' and case['decision_reason']==reason and prior:
                    return self._report(conn,case,request,idempotent_replay=True)
                raise GovernanceError('OWNER_REQUEST_CLOSED')
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id)
                .values(status='CANCELLED',decision_reason=reason,decided_at=now(),updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_ADDITION_CANCELLED',
                entity_type='verification_case',entity_id=case_id,metadata={'revision':case['current_revision'],'reason':reason})
            return self._report(conn,get_row(conn,'verification_cases',case_id),request,idempotent_replay=False)

    def operator_detail(self,conn,actor,case):
        request=proposal(conn,case['id']);independent(conn,actor,request)
        target=get_row(conn,'users',request['target_user_id'])
        return {**self._report(conn,case,request),'target_display_name':target['display_name']}

    def decide_locked(self,conn,actor,org,case,*,decision,expected_revision,reason):
        moderator_authority(conn,actor);reason=note(reason,2000)
        request=proposal(conn,case['id']);independent(conn,actor,request)
        if type(expected_revision) is not int or decision not in ('APPROVE','REJECT','NEEDS_INFO'):
            raise GovernanceError('INVALID_OWNER_DECISION',status_code=422)
        if case['assigned_reviewer_id']!=actor.user_id:raise GovernanceError('ASSIGNED_REVIEW_REQUIRED',status_code=403)
        if case['current_revision']!=expected_revision:raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT')
        state={'APPROVE':'APPROVED','REJECT':'REJECTED','NEEDS_INFO':'NEEDS_INFO'}[decision]
        events=table('org_ownership_events')
        if case['status']==state and case['decision_reason']==reason:
            event=conn.execute(select(events.c.id).where(events.c.verification_case_id==case['id'],
                events.c.new_membership_id==request['target_membership_id'],events.c.approved_by_id==actor.user_id)).scalar_one_or_none()
            if decision=='APPROVE' and not event:raise GovernanceError('OWNER_APPROVAL_PROOF_MISSING')
            return self._report(conn,case,request,idempotent_replay=True,ownership_event_id=event)
        if case['status']!='IN_REVIEW':raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT')
        event_id=None
        if decision=='APPROVE':
            if org['status']!='VERIFIED':raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            requester=org_authority(conn,request['requester_user_id'],org['id'],'OWNER')
            requester_user=get_row(conn,'users',request['requester_user_id'])
            if (requester['id']!=request['requester_membership_id'] or requester['_authority_grant_id']!=request['requester_grant_id']
                or requester_user['auth_version']!=request['requester_auth_version']):
                raise GovernanceError('REQUESTER_NO_LONGER_AUTHORIZED')
            target_member,target_user=target_staff(conn,request)
            if owner_grant_exists(conn,target_member['id']):raise GovernanceError('TARGET_ALREADY_OWNER')
            valid_consent(conn,case,request,target_user)
            evidence=table('verification_evidence')
            ids=list(conn.execute(select(evidence.c.file_id).where(evidence.c.case_id==case['id'],
                evidence.c.revision==expected_revision,evidence.c.file_id.is_not(None))).scalars())
            evidence_files(conn,request['requester_user_id'],ids)
            insert_row(conn,'org_role_grants',membership_id=target_member['id'],role_id=role_id(conn,'OWNER'),granted_by_id=actor.user_id)
            event=insert_row(conn,'org_ownership_events',organization_id=org['id'],new_membership_id=target_member['id'],
                verification_case_id=case['id'],approved_by_id=actor.user_id,effective_at=now())
            event_id=event['id']
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(
            status=state,decision_reason=reason,decided_at=None if decision=='NEEDS_INFO' else now(),updated_at=now()))
        self.audit_store.append_audit_event(actor_id=actor.user_id,action='OWNER_ADDITION_'+state,
            entity_type='verification_case',entity_id=case['id'],metadata={'revision':expected_revision,
                'target_membership_id':request['target_membership_id'],'ownership_event_id':event_id,'decision_reason':reason})
        return self._report(conn,get_row(conn,'verification_cases',case['id']),request,idempotent_replay=False,ownership_event_id=event_id)


owner_addition_service=OwnerAdditionService()
