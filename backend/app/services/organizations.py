"""Organization authority is granted only after scoped, independent review."""
from datetime import timedelta
import re
from sqlalchemy import select, text, func

from app.api.dependencies import ActorContext, require_org, require_platform
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import rate_limit
from app.db.storage import table, transaction, now, org_verification_submissions as submissions, save_domain_record, load_domain_record
from app.services.governance import GovernanceError
from app.services.placements import get_row, insert_row
from app.services.schedule import TASHKENT

audit = AppendOnlyAuditStore()
CAPABILITIES = ('JOB_EMPLOYER', 'INTERNSHIP_HOST')
REVIEW_KINDS = ('ORG_REPRESENTATIVE', 'ORG_PROFILE_CHANGE', *CAPABILITIES)
OPEN_STATES = ('PENDING', 'IN_REVIEW', 'NEEDS_INFO')


def require_mfa(actor):
    sessions, users = table('sessions'), table('users')
    with transaction() as conn:
        found = conn.execute(select(sessions.c.id).join(users, users.c.id == sessions.c.user_id).where(
            sessions.c.id == actor.session_id, sessions.c.user_id == actor.user_id,
            sessions.c.assurance == 'MFA', sessions.c.revoked_at.is_(None), sessions.c.expires_at > now(),
            sessions.c.auth_version == users.c.auth_version, users.c.status == 'ACTIVE')).first()
    if not found:
        raise GovernanceError('MFA_REQUIRED', status_code=403)


def normalized_tax_id(value):
    value = re.sub(r'[\s-]', '', value)
    if not re.fullmatch(r'[0-9]{3,32}', value):
        raise GovernanceError('INVALID_TAX_IDENTIFIER', status_code=422)
    return value


def due_date():
    day = now().astimezone(TASHKENT)
    remaining = 2
    while remaining:
        day += timedelta(days=1)
        if day.weekday() < 5:
            remaining -= 1
    return day


def owner_ids(conn, organization_id):
    members, grants, roles, users = (table(n) for n in ('org_memberships','org_role_grants','role_catalog','users'))
    return set(conn.execute(select(members.c.id).join(grants, grants.c.membership_id == members.c.id)
        .join(roles, roles.c.id == grants.c.role_id).join(users, users.c.id == members.c.user_id).where(
        members.c.organization_id == organization_id, members.c.status == 'ACTIVE', members.c.revoked_at.is_(None),
        grants.c.revoked_at.is_(None), roles.c.scope_kind == 'ORG', roles.c.code == 'OWNER',
        users.c.status == 'ACTIVE')).scalars())


def role_id(conn, code):
    roles = table('role_catalog')
    value = conn.execute(select(roles.c.id).where(roles.c.code == code, roles.c.scope_kind == 'ORG')).scalar_one_or_none()
    if not value:
        raise GovernanceError('ORG_ROLE_CONFIGURATION_REQUIRED', status_code=503)
    return value


def evidence_files(conn, user_id, ids):
    ids = [str(value) for value in ids]
    if not ids or len(ids) > 5 or len(ids) != len(set(ids)):
        raise GovernanceError('INVALID_EVIDENCE_FILES', status_code=422)
    files = table('files')
    rows = list(conn.execute(select(files).where(files.c.id.in_(ids)).order_by(files.c.id).with_for_update()).mappings())
    if len(rows) != len(ids) or any(r['owner_user_id'] != user_id for r in rows):
        raise GovernanceError('EVIDENCE_ACCESS_DENIED', status_code=403)
    if any(r['scan_status'] != 'CLEAN' or r['deleted_at'] or r['mime_type'] != 'application/pdf' for r in rows):
        raise GovernanceError('EVIDENCE_NOT_CLEAN', status_code=409)
    return ids


def require_capability(conn, organization_id, capability):
    orgs, caps, cases = (table(n) for n in ('organizations','organization_capabilities','verification_cases'))
    found = conn.execute(select(caps.c.id).join(orgs, orgs.c.id == caps.c.organization_id)
        .join(cases, cases.c.id == caps.c.approved_case_id).where(
        orgs.c.id == organization_id, orgs.c.status == 'VERIFIED', caps.c.capability == capability,
        caps.c.status == 'ACTIVE', cases.c.organization_id == organization_id,
        cases.c.kind == capability, cases.c.status == 'APPROVED',
        cases.c.assigned_reviewer_id.is_not(None), cases.c.assigned_reviewer_id != cases.c.requester_id)).first()
    if not found:
        raise GovernanceError('ORGANIZATION_CAPABILITY_REQUIRED', status_code=403)


class OrganizationService:
    def _membership(self, conn, org_id, user_id):
        members = table('org_memberships')
        row = conn.execute(select(members).where(members.c.organization_id == org_id, members.c.user_id == user_id)).mappings().first()
        return dict(row) if row else None

    def _submission(self, conn, case, membership_id, fields, file_ids, note):
        ids = evidence_files(conn, case['requester_id'], file_ids)
        conn.execute(submissions.insert().values(case_id=case['id'], revision=case['current_revision'],
            organization_id=case['organization_id'], requester_membership_id=membership_id,
            proposed_fields=fields, created_at=now()))
        for file_id in ids:
            insert_row(conn, 'verification_evidence', case_id=case['id'], revision=case['current_revision'], file_id=file_id)
        insert_row(conn, 'verification_evidence', case_id=case['id'], revision=case['current_revision'], note=note)

    def _new_case(self, conn, actor, org_id, kind, membership_id, fields, file_ids, note):
        case = insert_row(conn, 'verification_cases', organization_id=org_id, requester_id=actor.user_id,
            kind=kind, status='PENDING', current_revision=1, due_at=due_date())
        self._submission(conn, case, membership_id, fields, file_ids, note)
        audit.append_audit_event(actor_id=actor.user_id, action='ORG_VERIFICATION_SUBMITTED',
            entity_type='verification_case', entity_id=case['id'], metadata={'kind': kind, 'revision': 1})
        return case

    def register(self, actor, *, tax_id, legal_name, public_name, region, description, website,
                 file_ids, evidence_note, membership_role='HR'):
        require_mfa(actor)
        tax_id = normalized_tax_id(tax_id)
        rate_limit('org-onboarding', actor.user_id, 10, 3600)
        with transaction() as conn:
            conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'), {'key': 'org-tax:' + tax_id})
            orgs = table('organizations')
            row = conn.execute(select(orgs).where(func.regexp_replace(orgs.c.tax_id, '[[:space:]-]', '', 'g') == tax_id)
                .with_for_update()).mappings().first()
            created = row is None
            org = insert_row(conn, 'organizations', tax_id=tax_id, legal_name=legal_name,
                public_name=public_name, region=region, description=description, website=website, status='PENDING_VERIFICATION') if created else dict(row)
            if org['status'] not in ('PENDING_VERIFICATION', 'VERIFIED'):
                raise GovernanceError('ORGANIZATION_NOT_AVAILABLE')
            member = self._membership(conn, org['id'], actor.user_id)
            if member:
                if member['revoked_at'] or member['status'] in ('REVOKED','REJECTED'):
                    raise GovernanceError('MEMBERSHIP_REVIEW_REQUIRED')
                cases = table('verification_cases')
                case_id = conn.execute(select(cases.c.id).where(cases.c.organization_id == org['id'],
                    cases.c.requester_id == actor.user_id, cases.c.kind == 'ORG_REPRESENTATIVE').order_by(cases.c.created_at.desc()).limit(1)).scalar_one_or_none()
                return {'organization_id': org['id'], 'membership_id': member['id'], 'membership_status': member['status'],
                        'case_id': case_id, 'created': False}
            # A verified organization never reopens bootstrap after an owner's suspension.
            has_owner = org['status'] == 'VERIFIED' or bool(owner_ids(conn, org['id']))
            member = insert_row(conn, 'org_memberships', organization_id=org['id'], user_id=actor.user_id,
                status='PENDING_APPROVAL' if has_owner else 'PENDING_VERIFICATION')
            if has_owner:
                ids = evidence_files(conn, actor.user_id, file_ids)
                save_domain_record('membership_requests', member['id'], {'created_by': actor.user_id,
                    'role_id': role_id(conn, membership_role), 'origin': 'SELF_JOIN',
                    'evidence_file_ids': ids, 'evidence_note': evidence_note})
                case = None
                audit.append_audit_event(actor_id=actor.user_id, action='ORG_JOIN_REQUESTED', entity_type='membership', entity_id=member['id'])
            else:
                fields = {key: org[key] for key in ('tax_id','legal_name','public_name','region','description','website')}
                case = self._new_case(conn, actor, org['id'], 'ORG_REPRESENTATIVE', member['id'], fields, file_ids, evidence_note)
            return {'organization_id': org['id'], 'membership_id': member['id'], 'membership_status': member['status'],
                    'case_id': case['id'] if case else None, 'created': created}

    def _read_access(self, conn, actor, org_id):
        member = self._membership(conn, org_id, actor.user_id)
        if not member or member['revoked_at'] or member['status'] in ('REVOKED','REJECTED'):
            raise GovernanceError('ORG_SCOPE_FORBIDDEN', status_code=403)
        return member

    def status(self, actor, org_id):
        with transaction() as conn:
            member = self._read_access(conn, actor, org_id)
            cases = table('verification_cases')
            rows = list(conn.execute(select(cases).where(cases.c.organization_id == org_id,
                cases.c.requester_id == actor.user_id, cases.c.kind.in_(REVIEW_KINDS)).order_by(cases.c.created_at.desc()).limit(50)).mappings())
            return {'organization_id': org_id, 'membership_id': member['id'], 'membership_status': member['status'],
                    'cases': [dict(r) for r in rows], 'capabilities': self.capabilities(actor, org_id)}

    def capabilities(self, actor, org_id):
        with transaction() as conn:
            self._read_access(conn, actor, org_id)
            caps = table('organization_capabilities')
            rows = {r['capability']: r['status'] for r in conn.execute(select(caps).where(caps.c.organization_id == org_id)).mappings()}
            return [{'capability': code, 'status': rows.get(code, 'NOT_REQUESTED')} for code in CAPABILITIES]

    def public(self, org_id):
        with transaction() as conn:
            org = get_row(conn, 'organizations', org_id)
            if org['status'] != 'VERIFIED':
                raise GovernanceError('ORGANIZATION_NOT_FOUND', status_code=404)
            badges = []
            for code in CAPABILITIES:
                try:
                    require_capability(conn, org_id, code)
                except GovernanceError:
                    continue
                badges.append(code)
            return {key: org[key] for key in ('id','public_name','region','description','website')} | {'capabilities': badges}

    def submit(self, actor, org_id, *, kind, file_ids, evidence_note, case_id=None, proposed_fields=None):
        require_mfa(actor)
        rate_limit('org-submission', actor.user_id, 20, 3600)
        with transaction() as conn:
            org = get_row(conn, 'organizations', org_id, True)
            member = self._read_access(conn, actor, org_id)
            fields = proposed_fields or {}
            cases = table('verification_cases')
            if case_id:
                case = get_row(conn, 'verification_cases', case_id, True)
                if case['organization_id'] != org_id or case['requester_id'] != actor.user_id or case['kind'] != kind:
                    raise GovernanceError('CASE_SCOPE_FORBIDDEN', status_code=403)
                if case['status'] != 'NEEDS_INFO':
                    raise GovernanceError('CASE_NOT_RESUBMITTABLE')
                stored = conn.execute(select(submissions).where(submissions.c.case_id == case_id,
                    submissions.c.revision == case['current_revision'])).mappings().one()
                if kind == 'ORG_PROFILE_CHANGE':
                    # Resubmission adds evidence to the same proposal, never changes the proposal under review.
                    fields = stored['proposed_fields']
                case = {**case, 'current_revision': case['current_revision'] + 1, 'status': 'IN_REVIEW' if case['assigned_reviewer_id'] else 'PENDING'}
                conn.execute(cases.update().where(cases.c.id == case_id).values(current_revision=case['current_revision'],
                    status=case['status'], due_at=due_date(), updated_at=now()))
            else:
                if kind not in CAPABILITIES and kind != 'ORG_PROFILE_CHANGE':
                    raise GovernanceError('CASE_ID_REQUIRED', status_code=422)
                require_org(actor, org_id, 'OWNER', 'HOST_COORDINATOR')
                if org['status'] != 'VERIFIED':
                    raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
                pending = conn.execute(select(cases.c.id).where(cases.c.organization_id == org_id,
                    cases.c.kind == kind, cases.c.status.in_(OPEN_STATES))).first()
                if pending:
                    raise GovernanceError('VERIFICATION_ALREADY_PENDING')
                if kind in CAPABILITIES:
                    cap = table('organization_capabilities')
                    current = conn.execute(select(cap).where(cap.c.organization_id == org_id, cap.c.capability == kind)).mappings().first()
                    if current and current['status'] == 'ACTIVE':
                        raise GovernanceError('CAPABILITY_ALREADY_ACTIVE')
                    if current:
                        conn.execute(cap.update().where(cap.c.id == current['id']).values(status='PENDING', updated_at=now()))
                    else:
                        insert_row(conn, 'organization_capabilities', organization_id=org_id, capability=kind, status='PENDING')
                return self._new_case(conn, actor, org_id, kind, member['id'], fields, file_ids, evidence_note)
            if kind == 'ORG_REPRESENTATIVE':
                if member['status'] != 'PENDING_VERIFICATION' or owner_ids(conn, org_id):
                    raise GovernanceError('INITIAL_OWNER_REVIEW_CLOSED')
            else:
                require_org(actor, org_id, 'OWNER', 'HOST_COORDINATOR')
            self._submission(conn, case, member['id'], fields, file_ids, evidence_note)
            audit.append_audit_event(actor_id=actor.user_id, action='ORG_VERIFICATION_RESUBMITTED',
                entity_type='verification_case', entity_id=case['id'], metadata={'revision': case['current_revision']})
            return case

    def patch(self, actor, org_id, changes, file_ids, evidence_note):
        require_mfa(actor)
        with transaction() as conn:
            org = get_row(conn, 'organizations', org_id, True)
            require_org(actor, org_id, 'OWNER')
            if org['status'] != 'VERIFIED':
                raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            changes = {key: value for key, value in changes.items() if org[key] != value}
            if not changes:
                return {'organization_id': org_id, 'changed': False, 'case_id': None}
            # Every edit is held for review; stored public/verified data stays unchanged until approval.
            case = self.submit(actor, org_id, kind='ORG_PROFILE_CHANGE', file_ids=file_ids,
                evidence_note=evidence_note, proposed_fields=changes)
            return {'organization_id': org_id, 'changed': False, 'case_id': case['id'], 'status': case['status']}

    def _independent(self, conn, actor, case):
        if case['requester_id'] == actor.user_id or self._membership(conn, case['organization_id'], actor.user_id):
            raise GovernanceError('SELF_REVIEW_FORBIDDEN', status_code=403)

    def _operator_case(self, conn, actor, case_id):
        require_platform(actor, 'MODERATOR')
        require_mfa(actor)
        case = get_row(conn, 'verification_cases', case_id)
        if case['organization_id'] is None or case['kind'] not in REVIEW_KINDS:
            raise GovernanceError('UNSUPPORTED_VERIFICATION_CASE', status_code=422)
        org = get_row(conn, 'organizations', case['organization_id'], True)
        case = get_row(conn, 'verification_cases', case_id, True)
        self._independent(conn, actor, case)
        return org, case

    def claim(self, actor, case_id):
        with transaction() as conn:
            org, case = self._operator_case(conn, actor, case_id)
            if case['status'] not in ('PENDING','IN_REVIEW','NEEDS_INFO'):
                raise GovernanceError('CASE_ALREADY_DECIDED')
            if case['assigned_reviewer_id'] not in (None, actor.user_id):
                raise GovernanceError('CASE_ASSIGNED_TO_OTHER', status_code=403)
            status = 'NEEDS_INFO' if case['status'] == 'NEEDS_INFO' else 'IN_REVIEW'
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id == case_id)
                .values(assigned_reviewer_id=actor.user_id, status=status, updated_at=now()))
            audit.append_audit_event(actor_id=actor.user_id, action='ORG_VERIFICATION_CLAIMED', entity_type='verification_case', entity_id=case_id)
            return {'id': case_id, 'status': status, 'revision': case['current_revision']}

    def queue(self, actor, unassigned=False, limit=50):
        require_platform(actor, 'MODERATOR'); require_mfa(actor)
        cases = table('verification_cases')
        query = select(cases.c.id, cases.c.organization_id, cases.c.kind, cases.c.status, cases.c.current_revision, cases.c.due_at).where(
            cases.c.organization_id.is_not(None), cases.c.kind.in_(REVIEW_KINDS), cases.c.status.in_(OPEN_STATES))
        query = query.where(cases.c.assigned_reviewer_id.is_(None), cases.c.requester_id != actor.user_id) if unassigned else query.where(cases.c.assigned_reviewer_id == actor.user_id)
        with transaction() as conn:
            return [dict(r) for r in conn.execute(query.order_by(cases.c.due_at, cases.c.id).limit(limit)).mappings()]

    def case_detail(self, actor, case_id):
        with transaction() as conn:
            org, case = self._operator_case(conn, actor, case_id)
            if case['assigned_reviewer_id'] != actor.user_id or case['status'] != 'IN_REVIEW':
                raise GovernanceError('ASSIGNED_REVIEW_REQUIRED', status_code=403)
            evidence = table('verification_evidence')
            rows = list(conn.execute(select(evidence).where(evidence.c.case_id == case_id).order_by(evidence.c.revision, evidence.c.created_at)).mappings())
            revisions = list(conn.execute(select(submissions).where(submissions.c.case_id == case_id).order_by(submissions.c.revision)).mappings())
            return {'case': case, 'organization': {key: org[key] for key in
                ('id','tax_id','legal_name','public_name','region','description','website')},
                'submissions': [dict(r) for r in revisions], 'evidence': [dict(r) for r in rows]}

    def download_evidence(self, actor, case_id, file_id):
        from app.adapters import storage
        with transaction() as conn:
            detail = self.case_detail(actor, case_id)
            case = detail['case']
            if not any(e['file_id'] == file_id for e in detail['evidence']):
                raise GovernanceError('EVIDENCE_ACCESS_DENIED', status_code=403)
            evidence_files(conn, case['requester_id'], [file_id])
            file = get_row(conn, 'files', file_id)
            audit.append_audit_event(actor_id=actor.user_id, action='ORG_EVIDENCE_DOWNLOAD_AUTHORIZED', entity_type='verification_case', entity_id=case_id)
            return {'file_id': file_id, 'expires_in_seconds': 60, 'signed_url': storage.presign_get(file['storage_key'])}

    def decide(self, actor, case_id, *, decision, expected_revision, reason):
        with transaction() as conn:
            org, case = self._operator_case(conn, actor, case_id)
            if case['assigned_reviewer_id'] != actor.user_id:
                raise GovernanceError('ASSIGNED_REVIEW_REQUIRED', status_code=403)
            if case['status'] != 'IN_REVIEW' or case['current_revision'] != expected_revision:
                raise GovernanceError('CASE_STATE_OR_REVISION_CONFLICT')
            submission = conn.execute(select(submissions).where(submissions.c.case_id == case_id,
                submissions.c.revision == expected_revision)).mappings().one()
            member = get_row(conn, 'org_memberships', submission['requester_membership_id'], True)
            requester = get_row(conn, 'users', case['requester_id'])
            if (requester['status'] != 'ACTIVE' or member['user_id'] != case['requester_id'] or
                member['organization_id'] != org['id'] or member['revoked_at']):
                raise GovernanceError('REQUESTER_NO_LONGER_AUTHORIZED')
            if case['kind'] != 'ORG_REPRESENTATIVE':
                allowed = ('OWNER',) if case['kind'] == 'ORG_PROFILE_CHANGE' else ('OWNER','HOST_COORDINATOR')
                require_org(ActorContext(case['requester_id'], '', ()), org['id'], *allowed)
                if org['status'] != 'VERIFIED':
                    raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            if decision == 'APPROVE':
                evidence = table('verification_evidence')
                ids = list(conn.execute(select(evidence.c.file_id).where(evidence.c.case_id == case_id,
                    evidence.c.revision == expected_revision, evidence.c.file_id.is_not(None))).scalars())
                evidence_files(conn, case['requester_id'], ids)
                if case['kind'] == 'ORG_REPRESENTATIVE':
                    if org['status'] != 'PENDING_VERIFICATION' or owner_ids(conn, org['id']) or member['status'] != 'PENDING_VERIFICATION':
                        raise GovernanceError('INITIAL_OWNER_ALREADY_ASSIGNED')
                    conn.execute(table('org_memberships').update().where(table('org_memberships').c.id == member['id'])
                        .values(status='ACTIVE', accepted_at=now(), updated_at=now()))
                    insert_row(conn, 'org_role_grants', membership_id=member['id'], role_id=role_id(conn,'OWNER'), granted_by_id=actor.user_id)
                    insert_row(conn, 'org_ownership_events', organization_id=org['id'], new_membership_id=member['id'],
                        verification_case_id=case_id, approved_by_id=actor.user_id, effective_at=now())
                    conn.execute(table('organizations').update().where(table('organizations').c.id == org['id']).values(status='VERIFIED', updated_at=now()))
                elif case['kind'] == 'ORG_PROFILE_CHANGE':
                    conn.execute(table('organizations').update().where(table('organizations').c.id == org['id'])
                        .values(**submission['proposed_fields'], updated_at=now()))
                else:
                    conn.execute(table('organization_capabilities').update().where(
                        table('organization_capabilities').c.organization_id == org['id'],
                        table('organization_capabilities').c.capability == case['kind'])
                        .values(status='ACTIVE', approved_case_id=case_id, updated_at=now()))
            elif decision == 'REJECT' and case['kind'] in CAPABILITIES:
                conn.execute(table('organization_capabilities').update().where(
                    table('organization_capabilities').c.organization_id == org['id'],
                    table('organization_capabilities').c.capability == case['kind']).values(status='REJECTED', updated_at=now()))
            status = {'APPROVE':'APPROVED', 'REJECT':'REJECTED', 'NEEDS_INFO':'NEEDS_INFO'}[decision]
            conn.execute(table('verification_cases').update().where(table('verification_cases').c.id == case_id)
                .values(status=status, decision_reason=reason, decided_at=now() if decision != 'NEEDS_INFO' else None, updated_at=now()))
            audit.append_audit_event(actor_id=actor.user_id, action='ORG_VERIFICATION_' + status,
                entity_type='verification_case', entity_id=case_id,
                metadata={'revision': expected_revision, 'decision_reason': reason})
            return {'id': case_id, 'status': status, 'revision': expected_revision}

    def revoke(self, actor, org_id, membership_id, reason):
        require_mfa(actor)
        with transaction() as conn:
            get_row(conn, 'organizations', org_id, True)
            require_org(actor, org_id, 'OWNER')
            member = get_row(conn, 'org_memberships', membership_id, True)
            if member['organization_id'] != org_id:
                raise GovernanceError('ORG_SCOPE_FORBIDDEN', status_code=403)
            owners = owner_ids(conn, org_id)
            if membership_id in owners and len(owners) <= 1:
                raise GovernanceError('LAST_OWNER_PROTECTED')
            if not member['revoked_at']:
                conn.execute(table('org_memberships').update().where(table('org_memberships').c.id == membership_id)
                    .values(status='REVOKED', revoked_at=now(), updated_at=now()))
                conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id == membership_id,
                    table('org_role_grants').c.revoked_at.is_(None)).values(revoked_at=now(), updated_at=now()))
                from app.services.invitations import revoke_pending_for_member
                revoke_pending_for_member(conn,org_id,member)
                audit.append_audit_event(actor_id=actor.user_id, action='ORG_MEMBERSHIP_REVOKED', entity_type='membership',
                    entity_id=membership_id, metadata={'reason': reason})
            return {'membership_id': membership_id, 'status': 'REVOKED'}

    def join_detail(self, actor, org_id, membership_id):
        require_mfa(actor)
        with transaction() as conn:
            get_row(conn, 'organizations', org_id, True)
            require_org(actor, org_id, 'OWNER')
            member = get_row(conn, 'org_memberships', membership_id, True)
            request = load_domain_record('membership_requests', membership_id)
            if (member['organization_id'] != org_id or member['status'] != 'PENDING_APPROVAL' or
                not request or request.get('origin') != 'SELF_JOIN'):
                raise GovernanceError('JOIN_REQUEST_NOT_AVAILABLE', status_code=403)
            return {'membership_id': membership_id, 'user_id': member['user_id'],
                    'file_ids': request['evidence_file_ids'], 'evidence_note': request['evidence_note']}

    def join_download(self, actor, org_id, membership_id, file_id):
        from app.adapters import storage
        with transaction() as conn:
            request = self.join_detail(actor, org_id, membership_id)
            if file_id not in request['file_ids']:
                raise GovernanceError('EVIDENCE_ACCESS_DENIED', status_code=403)
            evidence_files(conn, request['user_id'], [file_id])
            file = get_row(conn, 'files', file_id)
            audit.append_audit_event(actor_id=actor.user_id, action='ORG_JOIN_EVIDENCE_DOWNLOAD_AUTHORIZED',
                entity_type='membership', entity_id=membership_id)
            return {'file_id': file_id, 'expires_in_seconds': 60, 'signed_url': storage.presign_get(file['storage_key'])}


organization_service = OrganizationService()
