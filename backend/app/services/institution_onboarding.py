"""Named, independently reviewed institutional claims; intake never grants a role."""
from datetime import date,datetime,timedelta,timezone
from app.adapters.storage import file_snapshot
import hashlib
import hmac
import json
import re
from uuid import uuid4
from sqlalchemy import select,func,text
from sqlalchemy.exc import OperationalError
from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import digest,normalize_contact,rate_limit
from app.db.storage import table,transaction,now
from app.db.institution_scope import TASHKENT,institution_scope_query
from app.services.authority import account_authority,institution_authority,institution_role_authority,moderator_authority
from app.services.governance import GovernanceError
from app.services.identity import contact_row
from app.services.organizations import evidence_files
from app.services.placements import get_row,insert_row

KIND='INSTITUTION_APPOINTMENT'
CONSENT_LIFETIME=timedelta(hours=24)


def busy():return GovernanceError('INSTITUTION_BUSY_RETRY',status_code=409)


def safe_json(value):
    def encode(item):
        if isinstance(item,datetime):return item.astimezone(timezone.utc).isoformat()
        return str(item)
    return json.loads(json.dumps(value,default=encode))


def agreement_snapshot(row):
    return safe_json({key:row.get(key) for key in ('id','institution_id','version','valid_from','valid_to','purposes','signed_file_id')})


def fingerprint(value):return hashlib.sha256(json.dumps(safe_json(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def registry_identity(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{2,63}',value.strip(' ')):
        raise GovernanceError('INVALID_INSTITUTION_REGISTRY_CODE',status_code=422)
    # This matches the migration's upper(btrim(...)) expression for supported codes.
    # It is application identity normalization, not a government registry lookup.
    return value.strip(' ').upper()


def response_due():
    day=now().astimezone(TASHKENT);remaining=3
    while remaining:
        day+=timedelta(days=1)
        if day.weekday()<5:remaining-=1
    return day


def pin_user(conn,user_id):
    try:
        row=conn.execute(select(table('users')).where(table('users').c.id==user_id).with_for_update(read=True,nowait=True)).mappings().first()
    except OperationalError as exc:
        if getattr(exc.orig,'sqlstate',None)=='55P03':raise busy() from exc
        raise
    if not row or row['status']!='ACTIVE':raise GovernanceError('INSTITUTION_TARGET_UNAVAILABLE',status_code=403)
    return dict(row)


def pin_contact(conn,user_id,contact_id):
    contacts=table('user_contacts');first=get_row(conn,'user_contacts',contact_id)
    if first['user_id']!=user_id:raise GovernanceError('INSTITUTION_CONTACT_UNAVAILABLE',status_code=403)
    pin_user(conn,user_id)
    key=digest('contact-lock',first['channel']+':'+first['normalized_value'])
    if not conn.execute(text('SELECT pg_try_advisory_xact_lock(hashtextextended(:key,0))'),{'key':key}).scalar_one():raise busy()
    try:
        row=conn.execute(select(contacts).where(contacts.c.id==contact_id).with_for_update(read=True,nowait=True)).mappings().first()
    except OperationalError as exc:
        if getattr(exc.orig,'sqlstate',None)=='55P03':raise busy() from exc
        raise
    if (not row or row['user_id']!=user_id or row['revoked_at'] or not row['verified_at'] or row['verified_at']>now()
        or (row['channel'],row['normalized_value'])!=(first['channel'],first['normalized_value'])):
        raise GovernanceError('INSTITUTION_CONTACT_UNAVAILABLE',status_code=403)
    binding=digest('institution-appointment-contact',json.dumps([row['id'],user_id,row['channel'],row['normalized_value'],
        row['verified_at'].astimezone(timezone.utc).isoformat()],separators=(',',':')))
    return dict(row),binding


def proof_insert(conn,name,**values):
    t=table(name);row={'created_at':now(),**values}
    if 'id' in t.c:row.setdefault('id',str(uuid4()))
    conn.execute(t.insert().values(**row));return row


def request_row(conn,appointment_id):
    t=table('institution_onboarding_requests')
    row=conn.execute(select(t).where(t.c.appointment_id==appointment_id)).mappings().first()
    if not row:raise GovernanceError('INSTITUTION_APPOINTMENT_NOT_FOUND',status_code=404)
    return dict(row)


def locked_request(conn,appointment_id):
    request=request_row(conn,appointment_id)
    inst=get_row(conn,'institutions',request['institution_id'],True)
    case=get_row(conn,'verification_cases',request['case_id'],True)
    appointment=get_row(conn,'institution_appointments',appointment_id,True)
    if (case['kind']!=KIND or case['appointment_id']!=appointment_id or appointment['verification_case_id']!=case['id']
        or appointment['institution_id']!=inst['id'] or appointment['user_id']!=request['target_user_id']):
        raise GovernanceError('INSTITUTION_CASE_SCOPE_MISMATCH',status_code=403)
    return inst,case,appointment,request


def submission(conn,case):
    t=table('institution_onboarding_submissions')
    row=conn.execute(select(t).where(t.c.case_id==case['id'],t.c.revision==case['current_revision'])).mappings().first()
    if not row:raise GovernanceError('INSTITUTION_SUBMISSION_NOT_FOUND',status_code=404)
    return dict(row)


def latest_consent(conn,case_id):
    t=table('institution_onboarding_consents')
    row=conn.execute(select(t).where(t.c.case_id==case_id).order_by(t.c.event_no.desc()).limit(1)).mappings().first()
    return dict(row) if row else None


def activated_grant(conn,appointment_id):
    t=table('institution_role_grants')
    row=conn.execute(select(t).where(t.c.appointment_id==appointment_id).order_by(t.c.created_at,t.c.id).limit(1)).mappings().first()
    return dict(row) if row else None


class InstitutionOnboardingService:
    audit_store=AppendOnlyAuditStore()

    def _report(self,conn,inst,case,appointment,request):
        consent=latest_consent(conn,case['id']);grant=activated_grant(conn,appointment['id'])
        revision=submission(conn,case)
        visible_files={revision['document_file_id'],revision['payload']['agreement_snapshot']['signed_file_id']}
        proposal={'institution':revision['payload']['institution_fields'],'legal_basis':revision['legal_basis'],
            'agreement':revision['payload']['agreement_snapshot'],
            'files':[{'id':fid,'sha256':revision['payload']['file_snapshots'][fid]['sha256'],
                'byte_size':revision['payload']['file_snapshots'][fid]['byte_size'],
                'download_path':'/api/v1/institution-appointments/'+appointment['id']+'/files/'+fid+'/download'} for fid in sorted(visible_files)]}
        return {'id':appointment['id'],'institution_id':inst['id'],'case_id':case['id'],'mode':request['mode'],
            'requested_role':'COORDINATOR' if request['mode']=='FIRST_COORDINATOR' else 'TEACHER',
            'status':appointment['status'],'case_status':case['status'],'revision':case['current_revision'],
            'due_at':case['due_at'],'decision_reason':case['decision_reason'],'valid_from':appointment['valid_from'],
            'valid_to':appointment['valid_to'],'accepted_at':appointment['accepted_at'],
            'ever_activated':grant is not None,'proposal':proposal,'consent':None if consent is None else
                {key:consent[key] for key in ('decision','revision','created_at','expires_at')}}

    def options(self,actor):
        with transaction() as conn:account_authority(conn,actor)
        return {'signed_in':True,'submission_requires_mfa':True,'domain_is_sufficient':False,
            'first_role':'COORDINATOR','staff_role':'TEACHER','first_response_target_weekdays':3,
            'target_is_not_consent_expiry':True,'requires':['verified_contact','appointment_pdf','agreement','legal_basis','independent_review','named_revision_acceptance']}

    def status(self,actor,appointment_id):
        with transaction() as conn:
            inst,case,appointment,request=locked_request(conn,appointment_id)
            account_authority(conn,actor)
            if actor.user_id not in (request['requester_user_id'],request['target_user_id']):
                raise GovernanceError('INSTITUTION_APPOINTMENT_FORBIDDEN',status_code=403)
            return self._report(conn,inst,case,appointment,request)

    def submit(self,actor,*,registry_code,document_file_id,contact_id,valid_from,valid_to,legal_basis,file_ids,evidence_note,
        idempotency_key,name=None,region=None,agreement_id=None,agreement_file_id=None,agreement_valid_from=None,
        agreement_valid_to=None,purposes=None,target_channel=None,target_destination=None):
        normalized=registry_identity(registry_code)
        if not 8<=len(idempotency_key)<=128:raise GovernanceError('INVALID_IDEMPOTENCY_KEY',status_code=422)
        if not isinstance(legal_basis,str) or not 15<=len(legal_basis.strip())<=4000:
            raise GovernanceError('INSTITUTION_LEGAL_BASIS_REQUIRED',status_code=422)
        if not isinstance(evidence_note,str) or not 15<=len(evidence_note.strip())<=4000:
            raise GovernanceError('INSTITUTION_EVIDENCE_NOTE_REQUIRED',status_code=422)
        today=now().astimezone(TASHKENT).date()
        if not isinstance(valid_from,date) or (valid_to is not None and (not isinstance(valid_to,date) or valid_to<max(today,valid_from))):
            raise GovernanceError('INVALID_APPOINTMENT_DATES',status_code=422)
        target_value=normalize_contact(target_channel,target_destination or '') if target_channel else None
        if bool(target_channel)!=bool(target_destination):raise GovernanceError('INSTITUTION_TARGET_REQUIRED',status_code=422)
        values=dict(registry_code=normalized,document_file_id=str(document_file_id),contact_id=str(contact_id),valid_from=valid_from,valid_to=valid_to,
            legal_basis=legal_basis.strip(),file_ids=sorted(str(x) for x in file_ids),evidence_note=evidence_note.strip(),name=name,region=region,
            agreement_id=str(agreement_id) if agreement_id else None,agreement_file_id=str(agreement_file_id) if agreement_file_id else None,
            agreement_valid_from=agreement_valid_from,agreement_valid_to=agreement_valid_to,purposes=purposes,
            target_channel=target_channel,target_digest=digest('institution-request-target',target_channel+':'+target_value) if target_value else None)
        fp=fingerprint(values);rate_limit('institution-appointment-submit',actor.user_id,20,3600)
        with transaction() as conn:
            conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':digest('institution-registry',normalized)})
            institutions=table('institutions');row=conn.execute(select(institutions).where(func.upper(func.btrim(institutions.c.registry_code))==normalized).with_for_update()).mappings().first()
            new=row is None
            if new:
                if not name or not region:raise GovernanceError('INSTITUTION_IDENTITY_REQUIRED',status_code=422)
                inst={'id':str(uuid4()),'created_at':now(),'updated_at':now(),'registry_code':normalized,'name':name,'region':region,'status':'PENDING_VERIFICATION'}
                conn.execute(institutions.insert().values(**inst))
            else:inst=dict(row)
            requests=table('institution_onboarding_requests')
            prior=conn.execute(select(requests).where(requests.c.requester_user_id==actor.user_id,requests.c.idempotency_key==idempotency_key)).mappings().first()
            if prior:
                if prior['institution_id']==inst['id']:
                    inst,case,appointment,request=locked_request(conn,prior['appointment_id'])
                account_authority(conn,actor,require_mfa=True)
                if prior['institution_id']==inst['id'] and prior['mode']=='STAFF_TEACHER':
                    institution_authority(conn,actor,inst['id'],'COORDINATOR',require_mfa=True)
                if prior['institution_id']!=inst['id'] or not hmac.compare_digest(fp,prior['request_fingerprint']):
                    raise GovernanceError('IDEMPOTENCY_CONFLICT',status_code=409)
                return self._report(conn,inst,case,appointment,request)
            # Lock all review material before user/session authority.
            ids=[str(x) for x in file_ids]
            if str(document_file_id) not in ids:raise GovernanceError('APPOINTMENT_DOCUMENT_NOT_IN_EVIDENCE',status_code=422)
            if new:
                if target_value or agreement_id or not agreement_file_id or str(agreement_file_id) not in ids:
                    raise GovernanceError('FIRST_INSTITUTION_AGREEMENT_REQUIRED',status_code=422)
                if (not isinstance(agreement_valid_from,date) or agreement_valid_from>today or
                    (agreement_valid_to is not None and agreement_valid_to<max(today,agreement_valid_from)) or
                    not isinstance(purposes,list) or not purposes or set(purposes)-{'ACADEMIC_VIEW'}):
                    raise GovernanceError('INVALID_INSTITUTION_AGREEMENT',status_code=422)
                agreement=insert_row(conn,'institution_agreements',institution_id=inst['id'],version=1,status='PENDING_REVIEW',
                    valid_from=agreement_valid_from,valid_to=agreement_valid_to,purposes=purposes,signed_file_id=str(agreement_file_id))
                mode='FIRST_COORDINATOR';target_id=actor.user_id
                if valid_from>today:raise GovernanceError('FIRST_COORDINATOR_MUST_BE_CURRENT',status_code=422)
            else:
                if not agreement_id or not target_value or name is not None or region is not None or agreement_file_id is not None:
                    raise GovernanceError('EXISTING_INSTITUTION_REQUIRES_STAFF_REQUEST',status_code=422)
                agreements=table('institution_agreements')
                scoped=conn.execute(select(agreements).where(agreements.c.id==str(agreement_id),agreements.c.institution_id==inst['id']).with_for_update()).mappings().first()
                agreement=dict(scoped) if scoped else None
                target_id=None;mode='STAFF_TEACHER'
            files=table('files');material_ids=set(ids)
            if agreement and agreement.get('signed_file_id'):material_ids.add(agreement['signed_file_id'])
            material_rows=list(conn.execute(select(files).where(files.c.id.in_(sorted(material_ids))).order_by(files.c.id).with_for_update()).mappings())
            account_authority(conn,actor,require_mfa=True)
            authority=None if new else institution_authority(conn,actor,inst['id'],'COORDINATOR',require_mfa=True)
            evidence_files(conn,actor.user_id,ids)
            if agreement is None:raise GovernanceError('INSTITUTION_AGREEMENT_NOT_FOUND',status_code=404)
            self._agreement_current(agreement,inst['id'],allow_pending=new)
            material_map={row['id']:row for row in material_rows}
            signed=material_map.get(agreement['signed_file_id'])
            if not signed or signed['scan_status']!='CLEAN' or signed['deleted_at'] or signed['mime_type']!='application/pdf':
                raise GovernanceError('INSTITUTION_AGREEMENT_FILE_NOT_CURRENT',status_code=409)
            own,own_binding=pin_contact(conn,actor.user_id,str(contact_id))
            if new:recipient,recipient_binding=own,own_binding
            else:
                # Contact existence is private. Resolve a named recipient only
                # after current coordinator, material and own-contact eligibility.
                target=contact_row(conn,target_channel,target_value)
                if not target:raise GovernanceError('INSTITUTION_TARGET_UNAVAILABLE',status_code=403)
                target_id=target['user_id']
                if target_id==actor.user_id:raise GovernanceError('SELF_APPOINTMENT_FORBIDDEN',status_code=403)
                recipient,recipient_binding=pin_contact(conn,target_id,target['id'])
            target_user=pin_user(conn,target_id);requester=get_row(conn,'users',actor.user_id)
            role=conn.execute(select(table('role_catalog')).where(table('role_catalog').c.scope_kind=='INSTITUTION',
                table('role_catalog').c.code==('COORDINATOR' if new else 'TEACHER'))).mappings().one()
            appointment=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=target_id,document_file_id=str(document_file_id),
                status='PENDING_REVIEW',valid_from=valid_from,valid_to=valid_to)
            case=insert_row(conn,'verification_cases',requester_id=actor.user_id,appointment_id=appointment['id'],kind=KIND,status='PENDING',current_revision=1,due_at=response_due())
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment['id']).values(verification_case_id=case['id']))
            request=proof_insert(conn,'institution_onboarding_requests',case_id=case['id'],institution_id=inst['id'],appointment_id=appointment['id'],
                requester_user_id=actor.user_id,target_user_id=target_id,mode=mode,role_id=role['id'],idempotency_key=idempotency_key,request_fingerprint=fp)
            proof_insert(conn,'institution_onboarding_submissions',case_id=case['id'],revision=1,submitted_by_id=actor.user_id,session_id=actor.session_id,
                auth_version=requester['auth_version'],requester_grant_id=authority['_authority_grant_id'] if authority else None,
                requester_contact_id=own['id'],requester_contact_digest=own_binding,requester_contact_verified_at=own['verified_at'],
                target_contact_id=recipient['id'],target_contact_digest=recipient_binding,target_contact_verified_at=recipient['verified_at'],
                target_auth_version=target_user['auth_version'],document_file_id=str(document_file_id),agreement_id=agreement['id'],legal_basis=legal_basis.strip(),
                valid_from=valid_from,valid_to=valid_to,payload=safe_json({'evidence_file_ids':ids,'evidence_note':evidence_note.strip(),
                    'institution_fields':{'name':inst['name'],'region':inst['region']},'agreement_snapshot':agreement_snapshot(agreement),
                    'file_snapshots':{fid:file_snapshot(material_map[fid]) for fid in material_ids}}))
            for file_id in ids:insert_row(conn,'verification_evidence',case_id=case['id'],revision=1,file_id=file_id)
            insert_row(conn,'verification_evidence',case_id=case['id'],revision=1,note=evidence_note.strip())
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_REQUESTED',entity_type='institution_appointment',entity_id=appointment['id'],metadata={'case_id':case['id'],'revision':1,'mode':mode})
            # Fetch defaults absent from the insertion helper before returning status.
            return self._report(conn,inst,get_row(conn,'verification_cases',case['id']),get_row(conn,'institution_appointments',appointment['id']),request)

    def _agreement_current(self,agreement,institution_id,*,allow_pending=False):
        today=now().astimezone(TASHKENT).date()
        purposes=agreement['purposes']
        allowed=('ACADEMIC_VIEW' in purposes) if isinstance(purposes,list) else (isinstance(purposes,dict) and purposes.get('ACADEMIC_VIEW') is True)
        if (agreement['institution_id']!=institution_id or agreement['status'] not in (('ACTIVE','PENDING_REVIEW') if allow_pending else ('ACTIVE',))
            or agreement['valid_from']>today or (agreement.get('valid_to') is not None and agreement['valid_to']<today)
            or not allowed or not agreement.get('signed_file_id')):
            raise GovernanceError('INSTITUTION_AGREEMENT_NOT_CURRENT',status_code=403)

    def _lock_materials(self,conn,case,request):
        revision=submission(conn,case)
        agreement=get_row(conn,'institution_agreements',revision['agreement_id'],True)
        ids=set(revision['payload']['evidence_file_ids'])
        if agreement['signed_file_id']:ids.add(agreement['signed_file_id'])
        files=table('files');rows=list(conn.execute(select(files).where(files.c.id.in_(sorted(ids))).order_by(files.c.id).with_for_update()).mappings())
        members=table('institution_memberships')
        member=conn.execute(select(members).where(members.c.institution_id==request['institution_id'],
            members.c.user_id==request['target_user_id'],members.c.status=='ACTIVE',members.c.revoked_at.is_(None)).with_for_update()).mappings().first()
        return dict(revision=revision,agreement=agreement,files={r['id']:dict(r) for r in rows},member=dict(member) if member else None)

    def _pending_current(self,conn,inst,case,appointment,request,materials):
        revision=materials['revision'];agreement=materials['agreement'];files=materials['files'];today=now().astimezone(TASHKENT).date()
        first=request['mode']=='FIRST_COORDINATOR'
        if {'name':inst['name'],'region':inst['region']}!=revision['payload']['institution_fields']:
            raise GovernanceError('INSTITUTION_IDENTITY_CHANGED',status_code=409)
        if (appointment['status']=='REVOKED' or appointment['valid_from']!=revision['valid_from'] or appointment['valid_to']!=revision['valid_to']
            or appointment['document_file_id']!=revision['document_file_id'] or (revision['valid_to'] is not None and revision['valid_to']<today)
            or (first and revision['valid_from']>today)):
            raise GovernanceError('INSTITUTION_APPOINTMENT_STALE',status_code=409)
        if (first and inst['status']!='PENDING_VERIFICATION') or (not first and inst['status']!='VERIFIED'):
            raise GovernanceError('INSTITUTION_STATE_CONFLICT',status_code=409)
        self._agreement_current(agreement,inst['id'],allow_pending=first)
        if agreement_snapshot(agreement)!=revision['payload']['agreement_snapshot']:
            raise GovernanceError('INSTITUTION_AGREEMENT_CHANGED',status_code=409)
        for file_id in set(revision['payload']['evidence_file_ids'])|{agreement['signed_file_id']}:
            file=files.get(file_id)
            if not file or file['scan_status']!='CLEAN' or file['deleted_at'] or file['mime_type']!='application/pdf':
                raise GovernanceError('INSTITUTION_EVIDENCE_NOT_CURRENT',status_code=409)
            if file_id in revision['payload']['evidence_file_ids'] and file['owner_user_id']!=request['requester_user_id']:
                raise GovernanceError('INSTITUTION_EVIDENCE_SCOPE_MISMATCH',status_code=403)
            if file_snapshot(file)!=revision['payload']['file_snapshots'].get(file_id):
                raise GovernanceError('INSTITUTION_EVIDENCE_CHANGED',status_code=409)
        requester=pin_user(conn,request['requester_user_id']);target=pin_user(conn,request['target_user_id'])
        if requester['auth_version']!=revision['auth_version'] or target['auth_version']!=revision['target_auth_version']:
            raise GovernanceError('INSTITUTION_SECURITY_CHANGED',status_code=409)
        for uid,field in ((requester['id'],'requester'),(target['id'],'target')):
            contact,binding=pin_contact(conn,uid,revision[field+'_contact_id'])
            if contact['verified_at']!=revision[field+'_contact_verified_at'] or not hmac.compare_digest(binding,revision[field+'_contact_digest']):
                raise GovernanceError('INSTITUTION_CONTACT_CHANGED',status_code=409)
        if not first:
            query=institution_scope_query(requester['id'],inst['id'],('COORDINATOR',),lock=True,nowait=True).where(
                table('institution_role_grants').c.id==revision['requester_grant_id'])
            try:authority=conn.execute(query).mappings().first()
            except OperationalError as exc:
                if getattr(exc.orig,'sqlstate',None)=='55P03':raise busy() from exc
                raise
            if not authority:raise GovernanceError('INSTITUTION_REQUESTER_AUTHORITY_STALE',status_code=409)
        return revision

    def _activate(self,conn,actor,inst,case,appointment,request,materials):
        if activated_grant(conn,appointment['id']) or case['status']!='APPROVED':return False
        consent=latest_consent(conn,case['id'])
        if not consent or consent['revision']!=case['current_revision'] or consent['decision']!='ACCEPT' or consent['expires_at']<=now():return False
        revision=self._pending_current(conn,inst,case,appointment,request,materials)
        if (consent['auth_version']!=revision['target_auth_version'] or consent['contact_id']!=revision['target_contact_id']
            or consent['contact_verified_at']!=revision['target_contact_verified_at']
            or not hmac.compare_digest(consent['contact_digest'],revision['target_contact_digest'])):
            raise GovernanceError('INSTITUTION_CONSENT_STALE',status_code=409)
        member=materials['member']
        if member is None:
            member=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=request['target_user_id'],status='ACTIVE',accepted_at=consent['created_at'])
        elif member['accepted_at'] is None:
            conn.execute(table('institution_memberships').update().where(table('institution_memberships').c.id==member['id']).values(accepted_at=consent['created_at'],updated_at=now()))
        elif member['accepted_at']>now():raise GovernanceError('INSTITUTION_MEMBERSHIP_STATE_CONFLICT',status_code=409)
        conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment['id']).values(status='ACTIVE',accepted_at=consent['created_at'],updated_at=now()))
        grant=insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=request['role_id'],appointment_id=appointment['id'])
        if request['mode']=='FIRST_COORDINATOR':
            conn.execute(table('institutions').update().where(table('institutions').c.id==inst['id']).values(status='VERIFIED',updated_at=now()))
            conn.execute(table('institution_agreements').update().where(table('institution_agreements').c.id==revision['agreement_id']).values(status='ACTIVE',updated_at=now()))
        self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_ACTIVATED',entity_type='institution_appointment',entity_id=appointment['id'],
            metadata={'case_id':case['id'],'revision':case['current_revision'],'grant_id':grant['id'],'membership_id':member['id']})
        return True

    def consent(self,actor,appointment_id,*,expected_revision,decision,contact_id=None):
        if decision not in ('ACCEPT','DECLINE'):raise GovernanceError('INVALID_CONSENT_DECISION',status_code=422)
        with transaction() as conn:
            inst,case,appointment,request=locked_request(conn,appointment_id)
            historical=activated_grant(conn,appointment_id)
            materials=self._lock_materials(conn,case,request) if decision=='ACCEPT' and not historical else None
            account_authority(conn,actor,require_mfa=request['mode']=='FIRST_COORDINATOR')
            if actor.user_id!=request['target_user_id']:raise GovernanceError('INSTITUTION_NAMED_TARGET_REQUIRED',status_code=403)
            if expected_revision!=case['current_revision']:raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT',status_code=409)
            if historical:
                if decision=='DECLINE':raise GovernanceError('ACTIVATED_APPOINTMENT_USE_REVOCATION',status_code=409)
                return self._report(conn,inst,case,appointment,request)
            previous=latest_consent(conn,case['id'])
            if decision=='ACCEPT':
                revision=self._pending_current(conn,inst,case,appointment,request,materials)
                if not contact_id or str(contact_id)!=revision['target_contact_id']:
                    raise GovernanceError('INSTITUTION_CONTACT_CHANGED',status_code=403)
                if case['status'] not in ('PENDING','IN_REVIEW','APPROVED'):raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT',status_code=409)
                contact,binding=pin_contact(conn,actor.user_id,str(contact_id));user=pin_user(conn,actor.user_id)
                if (previous and previous['decision']=='ACCEPT' and previous['revision']==expected_revision
                    and previous['expires_at']>now() and previous['auth_version']==user['auth_version']
                    and previous['contact_id']==contact['id'] and hmac.compare_digest(previous['contact_digest'],binding)):
                    return self._report(conn,inst,case,appointment,request)
                proof=dict(contact_id=contact['id'],contact_digest=binding,contact_verified_at=contact['verified_at'],expires_at=now()+CONSENT_LIFETIME)
            else:
                if contact_id is not None:raise GovernanceError('DECLINE_HAS_NO_CONTACT_PROOF',status_code=422)
                if case['status']=='CANCELLED' and previous and previous['decision']=='DECLINE':return self._report(conn,inst,case,appointment,request)
                proof=dict(contact_id=None,contact_digest=None,contact_verified_at=None,expires_at=None);user=pin_user(conn,actor.user_id)
            event=proof_insert(conn,'institution_onboarding_consents',case_id=case['id'],revision=expected_revision,event_no=(previous['event_no']+1 if previous else 1),
                actor_id=actor.user_id,session_id=actor.session_id,auth_version=user['auth_version'],decision=decision,**proof)
            if decision=='DECLINE':
                conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(status='CANCELLED',updated_at=now()))
                conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment_id).values(status='REVOKED',updated_at=now()))
            else:self._activate(conn,actor,inst,case,appointment,request,materials)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_'+decision,entity_type='institution_appointment',entity_id=appointment_id,metadata={'revision':expected_revision,'consent_id':event['id']})
            return self._report(conn,get_row(conn,'institutions',inst['id']),get_row(conn,'verification_cases',case['id']),get_row(conn,'institution_appointments',appointment_id),request)

    def inbox(self,actor,limit=50):
        with transaction() as conn:
            account_authority(conn,actor)
            requests,cases,appointments=(table(n) for n in ('institution_onboarding_requests','verification_cases','institution_appointments'))
            rows=conn.execute(select(appointments.c.id,appointments.c.institution_id,appointments.c.status,cases.c.status.label('case_status'),cases.c.current_revision)
                .join(requests,requests.c.appointment_id==appointments.c.id).join(cases,cases.c.id==requests.c.case_id)
                .where(requests.c.target_user_id==actor.user_id).order_by(requests.c.created_at.desc(),appointments.c.id).limit(limit)).mappings()
            return [dict(row) for row in rows]

    def download_own(self,actor,appointment_id,file_id):
        from app.adapters import storage
        with transaction() as conn:
            inst,case,appointment,request=locked_request(conn,appointment_id);revision=submission(conn,case)
            # A named appointee sees the appointment and agreement, not unrelated
            # requester evidence. Requesters can also view their own submissions.
            permitted={revision['document_file_id'],revision['payload']['agreement_snapshot']['signed_file_id']}
            if actor.user_id==request['requester_user_id']:permitted.update(revision['payload']['evidence_file_ids'])
            file=get_row(conn,'files',file_id,True) if file_id in permitted else None
            account_authority(conn,actor)
            if actor.user_id not in (request['requester_user_id'],request['target_user_id']):
                raise GovernanceError('INSTITUTION_APPOINTMENT_FORBIDDEN',status_code=403)
            if actor.user_id==request['target_user_id']:
                contact,binding=pin_contact(conn,actor.user_id,revision['target_contact_id'])
                if contact['verified_at']!=revision['target_contact_verified_at'] or not hmac.compare_digest(binding,revision['target_contact_digest']):
                    raise GovernanceError('INSTITUTION_CONTACT_CHANGED',status_code=403)
            if not file:raise GovernanceError('EVIDENCE_ACCESS_DENIED',status_code=403)
            if file['scan_status']!='CLEAN' or file['deleted_at']:raise GovernanceError('INSTITUTION_EVIDENCE_NOT_CURRENT',status_code=409)
            if file_snapshot(file)!=revision['payload']['file_snapshots'].get(file_id):
                raise GovernanceError('INSTITUTION_EVIDENCE_CHANGED',status_code=409)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_FILE_AUTHORIZED',entity_type='institution_appointment',entity_id=appointment_id,metadata={'file_id':file_id,'revision':case['current_revision']})
            return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(file['storage_key'],reference=storage.file_reference(file))}

    def revoke(self,actor,appointment_id,*,reason):
        if not isinstance(reason,str) or not 15<=len(reason.strip())<=4000:raise GovernanceError('INSTITUTION_REVOCATION_REASON_REQUIRED',status_code=422)
        with transaction() as conn:
            inst,case,appointment,request=locked_request(conn,appointment_id)
            grants=table('institution_role_grants')
            rows=list(conn.execute(select(grants).where(grants.c.appointment_id==appointment_id).order_by(grants.c.id).with_for_update()).mappings())
            account_authority(conn,actor,require_mfa=actor.user_id==request['target_user_id'] and request['mode']=='FIRST_COORDINATOR')
            if actor.user_id!=request['target_user_id']:
                institution_authority(conn,actor,inst['id'],'COORDINATOR',require_mfa=True)
            if appointment['status']=='REVOKED' and not any(row['revoked_at'] is None for row in rows):
                return self._report(conn,inst,case,appointment,request)
            stamp=now()
            conn.execute(grants.update().where(grants.c.appointment_id==appointment_id,grants.c.revoked_at.is_(None)).values(revoked_at=stamp,updated_at=stamp))
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment_id).values(status='REVOKED',updated_at=stamp))
            if not rows:
                conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(status='CANCELLED',updated_at=stamp))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_REVOKED',entity_type='institution_appointment',entity_id=appointment_id,metadata={'reason':reason.strip(),'grant_ids':[row['id'] for row in rows]})
            return self._report(conn,inst,get_row(conn,'verification_cases',case['id']),get_row(conn,'institution_appointments',appointment_id),request)

    def resubmit(self,actor,appointment_id,*,expected_revision,**fields):
        canonical={**fields,'registry_code':registry_identity(fields['registry_code']),
            'file_ids':sorted(str(value) for value in fields['file_ids'])}
        destination=canonical.pop('target_destination',None)
        canonical['target_digest']=digest('institution-request-target',fields['target_channel']+':'+normalize_contact(fields['target_channel'],destination)) if fields.get('target_channel') and destination else None
        fp=fingerprint({'expected_revision':expected_revision,**canonical})
        rate_limit('institution-appointment-resubmit',actor.user_id,20,3600)
        with transaction() as conn:
            inst,case,appointment,request=locked_request(conn,appointment_id);old=submission(conn,case)
            first=request['mode']=='FIRST_COORDINATOR'
            ids=[str(x) for x in fields['file_ids']];document_id=str(fields['document_file_id']);today=now().astimezone(TASHKENT).date()
            if registry_identity(fields['registry_code'])!=registry_identity(inst['registry_code']):raise GovernanceError('INSTITUTION_IDENTITY_IMMUTABLE',status_code=422)
            # Acquire existing material locks before actor authority; new agreement
            # versions below are proposals and roll back if any guard rejects.
            agreements=table('institution_agreements')
            selected_id=str(fields['agreement_id']) if fields.get('agreement_id') else old['agreement_id']
            selected=conn.execute(select(agreements).where(agreements.c.id==selected_id,agreements.c.institution_id==inst['id']).with_for_update()).mappings().first()
            agreement=dict(selected) if selected else None
            signed_id=str(fields['agreement_file_id']) if fields.get('agreement_file_id') else (agreement['signed_file_id'] if agreement else None)
            material_ids=set(ids)
            if signed_id:material_ids.add(signed_id)
            files=table('files');material_map={row['id']:dict(row) for row in conn.execute(select(files).where(files.c.id.in_(sorted(material_ids))).order_by(files.c.id).with_for_update()).mappings()}
            account_authority(conn,actor,require_mfa=True)
            if actor.user_id!=request['requester_user_id']:raise GovernanceError('INSTITUTION_REQUESTER_REQUIRED',status_code=403)
            authority=None if first else institution_authority(conn,actor,inst['id'],'COORDINATOR',require_mfa=True)
            if agreement is None:raise GovernanceError('INSTITUTION_AGREEMENT_NOT_FOUND',status_code=404)
            if expected_revision+1==case['current_revision'] and old['payload'].get('resubmission_fingerprint')==fp:
                return self._report(conn,inst,case,appointment,request)
            if expected_revision!=case['current_revision'] or case['status'] not in ('NEEDS_INFO','REJECTED','CANCELLED','APPROVED'):
                raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT',status_code=409)
            if activated_grant(conn,appointment_id):raise GovernanceError('ACTIVATED_APPOINTMENT_REQUIRES_NEW_REQUEST',status_code=409)
            if (first and inst['status']!='PENDING_VERIFICATION') or (not first and inst['status']!='VERIFIED'):
                raise GovernanceError('INSTITUTION_STATE_CONFLICT',status_code=409)
            valid_from=fields['valid_from'];valid_to=fields['valid_to'] if 'valid_to' in fields else old['valid_to']
            if (not isinstance(valid_from,date) or (valid_to is not None and valid_to<max(today,valid_from)) or (first and valid_from>today)):
                raise GovernanceError('INVALID_APPOINTMENT_DATES',status_code=422)
            legal_basis=fields['legal_basis'].strip();note=fields['evidence_note'].strip()
            if not 15<=len(legal_basis)<=4000 or not 15<=len(note)<=4000:raise GovernanceError('INSTITUTION_EVIDENCE_NOTE_REQUIRED',status_code=422)
            if document_id not in ids:raise GovernanceError('APPOINTMENT_DOCUMENT_NOT_IN_EVIDENCE',status_code=422)
            evidence_files(conn,actor.user_id,ids)
            if first:
                if fields.get('target_channel') or fields.get('target_destination') or fields.get('agreement_id') or signed_id not in ids:
                    raise GovernanceError('FIRST_INSTITUTION_AGREEMENT_REQUIRED',status_code=422)
                start=fields.get('agreement_valid_from') or agreement['valid_from']
                end=fields['agreement_valid_to'] if 'agreement_valid_to' in fields else agreement.get('valid_to')
                purposes=fields.get('purposes') or agreement['purposes']
                if start>today or (end is not None and end<max(today,start)) or not isinstance(purposes,list) or not purposes or set(purposes)-{'ACADEMIC_VIEW'}:
                    raise GovernanceError('INVALID_INSTITUTION_AGREEMENT',status_code=422)
                agreements=table('institution_agreements');version=conn.execute(select(func.max(agreements.c.version)).where(agreements.c.institution_id==inst['id'])).scalar_one()+1
                agreement=insert_row(conn,'institution_agreements',institution_id=inst['id'],version=version,status='PENDING_REVIEW',valid_from=start,valid_to=end,purposes=purposes,signed_file_id=signed_id)
                changes={key:fields[key] for key in ('name','region') if fields.get(key) is not None}
                if changes:
                    conn.execute(table('institutions').update().where(table('institutions').c.id==inst['id']).values(**changes,updated_at=now()));inst={**inst,**changes}
            else:
                if fields.get('name') is not None or fields.get('region') is not None or fields.get('agreement_file_id') is not None:
                    raise GovernanceError('EXISTING_INSTITUTION_IDENTITY_IMMUTABLE',status_code=422)
            self._agreement_current(agreement,inst['id'],allow_pending=first)
            signed=material_map.get(agreement['signed_file_id'])
            if not signed or signed['scan_status']!='CLEAN' or signed['deleted_at'] or signed['mime_type']!='application/pdf':
                raise GovernanceError('INSTITUTION_AGREEMENT_FILE_NOT_CURRENT',status_code=409)
            own,own_binding=pin_contact(conn,actor.user_id,str(fields['contact_id']))
            if first:recipient,recipient_binding=own,own_binding
            else:
                if bool(fields.get('target_channel'))!=bool(fields.get('target_destination')):raise GovernanceError('INSTITUTION_TARGET_REQUIRED',status_code=422)
                if fields.get('target_channel'):
                    value=normalize_contact(fields['target_channel'],fields['target_destination']);target=contact_row(conn,fields['target_channel'],value)
                    if not target or target['user_id']!=request['target_user_id']:raise GovernanceError('INSTITUTION_NAMED_TARGET_IMMUTABLE',status_code=403)
                    target_contact_id=target['id']
                else:target_contact_id=old['target_contact_id']
                recipient,recipient_binding=pin_contact(conn,request['target_user_id'],target_contact_id)
            target_user=pin_user(conn,request['target_user_id']);requester=pin_user(conn,actor.user_id)
            new_revision=case['current_revision']+1;new_status='IN_REVIEW' if case['assigned_reviewer_id'] else 'PENDING'
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(current_revision=new_revision,status=new_status,decision_reason=None,decided_at=None,updated_at=now()))
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment_id).values(status='PENDING_REVIEW',accepted_at=None,
                document_file_id=document_id,valid_from=valid_from,valid_to=valid_to,updated_at=now()))
            proof_insert(conn,'institution_onboarding_submissions',case_id=case['id'],revision=new_revision,submitted_by_id=actor.user_id,session_id=actor.session_id,
                auth_version=requester['auth_version'],requester_grant_id=authority['_authority_grant_id'] if authority else None,
                requester_contact_id=own['id'],requester_contact_digest=own_binding,requester_contact_verified_at=own['verified_at'],
                target_contact_id=recipient['id'],target_contact_digest=recipient_binding,target_contact_verified_at=recipient['verified_at'],target_auth_version=target_user['auth_version'],
                document_file_id=document_id,agreement_id=agreement['id'],legal_basis=legal_basis,valid_from=valid_from,valid_to=valid_to,
                payload=safe_json({'evidence_file_ids':ids,'evidence_note':note,'institution_fields':{'name':inst['name'],'region':inst['region']},
                    'agreement_snapshot':agreement_snapshot(agreement),'resubmission_fingerprint':fp,
                    'file_snapshots':{fid:file_snapshot(material_map[fid]) for fid in material_ids}}))
            for file_id in ids:insert_row(conn,'verification_evidence',case_id=case['id'],revision=new_revision,file_id=file_id)
            insert_row(conn,'verification_evidence',case_id=case['id'],revision=new_revision,note=note)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_APPOINTMENT_RESUBMITTED',entity_type='institution_appointment',entity_id=appointment_id,metadata={'case_id':case['id'],'revision':new_revision})
            return self._report(conn,inst,get_row(conn,'verification_cases',case['id']),get_row(conn,'institution_appointments',appointment_id),request)

    def _independent(self,conn,actor,request):
        members=table('institution_memberships')
        if actor.user_id in (request['requester_user_id'],request['target_user_id']) or conn.execute(select(members.c.id).where(
            members.c.institution_id==request['institution_id'],members.c.user_id==actor.user_id).limit(1)).first():
            raise GovernanceError('SELF_REVIEW_FORBIDDEN',status_code=403)

    def _operator_request(self,conn,case_id):
        t=table('institution_onboarding_requests');request=conn.execute(select(t).where(t.c.case_id==case_id)).mappings().first()
        if not request:raise GovernanceError('UNSUPPORTED_INSTITUTION_CASE',status_code=422)
        return locked_request(conn,request['appointment_id'])

    def claim(self,actor,case_id):
        with transaction() as conn:
            inst,case,appointment,request=self._operator_request(conn,case_id)
            moderator_authority(conn,actor);self._independent(conn,actor,request)
            if case['assigned_reviewer_id']==actor.user_id:
                return {'id':case_id,'status':case['status'],'revision':case['current_revision']}
            if case['status'] not in ('PENDING','IN_REVIEW','NEEDS_INFO'):raise GovernanceError('CASE_ALREADY_DECIDED',status_code=409)
            if case['assigned_reviewer_id'] not in (None,actor.user_id):raise GovernanceError('CASE_ASSIGNED_TO_OTHER',status_code=403)
            status='NEEDS_INFO' if case['status']=='NEEDS_INFO' else 'IN_REVIEW'
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id).values(assigned_reviewer_id=actor.user_id,status=status,updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_REVIEW_CLAIMED',entity_type='verification_case',entity_id=case_id)
            return {'id':case_id,'status':status,'revision':case['current_revision']}

    def queue(self,actor,unassigned=False,limit=50):
        with transaction() as conn:
            moderator_authority(conn,actor)
            cases,requests,members=(table(n) for n in ('verification_cases','institution_onboarding_requests','institution_memberships'))
            query=select(cases.c.id,cases.c.kind,cases.c.status,cases.c.current_revision,cases.c.due_at,
                cases.c.appointment_id,requests.c.institution_id).join(requests,requests.c.case_id==cases.c.id).where(
                cases.c.kind==KIND,cases.c.status.in_(('PENDING','IN_REVIEW','NEEDS_INFO')),
                requests.c.requester_user_id!=actor.user_id,requests.c.target_user_id!=actor.user_id,
                ~select(members.c.id).where(members.c.institution_id==requests.c.institution_id,members.c.user_id==actor.user_id).exists())
            query=query.where(cases.c.assigned_reviewer_id.is_(None)) if unassigned else query.where(cases.c.assigned_reviewer_id==actor.user_id)
            return [dict(row) for row in conn.execute(query.order_by(cases.c.due_at,cases.c.id).limit(limit)).mappings()]

    def case_detail(self,actor,case_id):
        with transaction() as conn:
            inst,case,appointment,request=self._operator_request(conn,case_id)
            moderator_authority(conn,actor);self._independent(conn,actor,request)
            if case['assigned_reviewer_id']!=actor.user_id or case['status']!='IN_REVIEW':
                raise GovernanceError('ASSIGNED_REVIEW_REQUIRED',status_code=403)
            revisions=table('institution_onboarding_submissions');evidence=table('verification_evidence')
            return {'case':case,'institution':{key:inst[key] for key in ('id','registry_code','name','region','status')},
                'appointment':appointment,'request':request,
                'submissions':[dict(row) for row in conn.execute(select(revisions).where(revisions.c.case_id==case_id).order_by(revisions.c.revision)).mappings()],
                'evidence':[dict(row) for row in conn.execute(select(evidence).where(evidence.c.case_id==case_id).order_by(evidence.c.revision,evidence.c.created_at)).mappings()]}

    def download_evidence(self,actor,case_id,file_id):
        from app.adapters import storage
        with transaction() as conn:
            inst,case,appointment,request=self._operator_request(conn,case_id)
            revisions=table('institution_onboarding_submissions')
            snapshots=[row for row in conn.execute(select(revisions.c.payload).where(revisions.c.case_id==case_id)).scalars()]
            linked=any(file_id in row['file_snapshots'] for row in snapshots)
            file=get_row(conn,'files',file_id,True) if linked else None
            moderator_authority(conn,actor);self._independent(conn,actor,request)
            if case['assigned_reviewer_id']!=actor.user_id or case['status']!='IN_REVIEW':raise GovernanceError('ASSIGNED_REVIEW_REQUIRED',status_code=403)
            if not linked:raise GovernanceError('EVIDENCE_ACCESS_DENIED',status_code=403)
            if file['scan_status']!='CLEAN' or file['deleted_at']:raise GovernanceError('INSTITUTION_EVIDENCE_NOT_CURRENT',status_code=409)
            current=file_snapshot(file)
            if not any(row['file_snapshots'].get(file_id)==current for row in snapshots):raise GovernanceError('INSTITUTION_EVIDENCE_CHANGED',status_code=409)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_REVIEW_FILE_AUTHORIZED',entity_type='verification_case',entity_id=case_id,metadata={'file_id':file_id})
            return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(file['storage_key'],reference=storage.file_reference(file))}

    def decide(self,actor,case_id,*,expected_revision,decision,reason):
        if decision not in ('APPROVE','REJECT','NEEDS_INFO') or not 15<=len(reason.strip())<=4000:
            raise GovernanceError('INVALID_INSTITUTION_REVIEW_DECISION',status_code=422)
        with transaction() as conn:
            inst,case,appointment,request=self._operator_request(conn,case_id)
            decisions=table('institution_onboarding_decisions')
            prior=conn.execute(select(decisions).where(decisions.c.case_id==case_id,decisions.c.revision==expected_revision)).mappings().first()
            materials=self._lock_materials(conn,case,request) if decision=='APPROVE' and not prior else None
            moderator_authority(conn,actor);self._independent(conn,actor,request)
            if case['assigned_reviewer_id']!=actor.user_id:raise GovernanceError('ASSIGNED_REVIEW_REQUIRED',status_code=403)
            if expected_revision!=case['current_revision']:raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT',status_code=409)
            if prior:
                if prior['actor_id']==actor.user_id and prior['decision']==decision and prior['reason']==reason.strip():
                    return self._report(conn,inst,case,appointment,request)
                raise GovernanceError('CASE_ALREADY_DECIDED',status_code=409)
            if case['status']!='IN_REVIEW':raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT',status_code=409)
            if decision=='APPROVE':self._pending_current(conn,inst,case,appointment,request,materials)
            grants,roles=table('platform_role_grants'),table('role_catalog')
            grant_id=conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(grants.c.user_id==actor.user_id,
                grants.c.revoked_at.is_(None),grants.c.expires_at>now(),roles.c.scope_kind=='PLATFORM',roles.c.code=='MODERATOR')
                .order_by(grants.c.id).with_for_update(read=True,of=(grants,roles))).scalar()
            user=get_row(conn,'users',actor.user_id)
            proof_insert(conn,'institution_onboarding_decisions',case_id=case_id,revision=expected_revision,actor_id=actor.user_id,
                session_id=actor.session_id,auth_version=user['auth_version'],platform_grant_id=grant_id,decision=decision,reason=reason.strip())
            status={'APPROVE':'APPROVED','REJECT':'REJECTED','NEEDS_INFO':'NEEDS_INFO'}[decision]
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case_id).values(status=status,
                decision_reason=reason.strip(),decided_at=now() if decision!='NEEDS_INFO' else None,updated_at=now()))
            appointment_status={'APPROVE':'APPROVED_PENDING_ACCEPT','REJECT':'REJECTED','NEEDS_INFO':'NEEDS_INFO'}[decision]
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment['id']).values(status=appointment_status,updated_at=now()))
            if decision=='APPROVE':self._activate(conn,actor,inst,{**case,'status':'APPROVED'},appointment,request,materials)
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='INSTITUTION_REVIEW_'+status,entity_type='verification_case',entity_id=case_id,metadata={'revision':expected_revision,'reason':reason.strip()})
            return self._report(conn,get_row(conn,'institutions',inst['id']),get_row(conn,'verification_cases',case_id),get_row(conn,'institution_appointments',appointment['id']),request)


institution_onboarding_service=InstitutionOnboardingService()
