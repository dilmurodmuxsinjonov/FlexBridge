"""Versioned host admission. Academic admission is deliberately a separate gate."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction, now, json_value
from app.services.authority import account_authority, org_authority
from app.services.organizations import require_capability
from app.services.placements import get_row, insert_row, PlacementScopeError, require_internship_placement
from app.services.pagination import page
from app.services.mentor_notices import queue_notice


def fingerprint(action, **values):
    return hashlib.sha256(json.dumps({'action': action, **json_value(values)}, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def evidence(conn, actor):
    return dict(actor_id=actor.user_id, session_id=actor.session_id,
                auth_version=get_row(conn, 'users', actor.user_id)['auth_version'])


def request_record(conn, name, actor, key, digest):
    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise PlacementScopeError('INVALID_IDEMPOTENCY_KEY', status_code=422)
    t = table(name)
    old = conn.execute(select(t).where(t.c.actor_id == actor.user_id, t.c.idempotency_key == key)).mappings().first()
    if old and old['request_fingerprint'] != digest:
        raise PlacementScopeError('IDEMPOTENCY_KEY_REUSED')
    return dict(old) if old else None


def nomination_result(assignment, receipt):
    # Both HTTP aliases must serialize the same UTC strings despite different response encoders.
    return {**{key:value.astimezone(timezone.utc).isoformat() if isinstance(value,datetime) else value
               for key,value in assignment.items()}, 'nomination_receipt':receipt}


class PlacementAdmissionService:
    audit = AppendOnlyAuditStore()

    def _locked(self, conn, placement_id):
        hint = get_row(conn, 'placements', placement_id)
        bindings=table('placement_academic_bindings')
        institution=conn.execute(select(bindings.c.institution_id).where(bindings.c.placement_id==placement_id)).scalar_one_or_none()
        if institution:get_row(conn,'institutions',institution,True)
        get_row(conn, 'organizations', hint['organization_id'], True)
        placement = get_row(conn, 'placements', placement_id, True)
        actual=conn.execute(select(bindings.c.institution_id).where(bindings.c.placement_id==placement_id)).scalar_one_or_none()
        if actual!=institution:raise PlacementScopeError('ACADEMIC_SCOPE_CHANGED_RETRY')
        require_internship_placement(conn, placement)
        terms = get_row(conn, 'placement_terms', placement['current_terms_id'], True)
        if terms['placement_id'] != placement_id:
            raise PlacementScopeError('TERMS_SCOPE_MISMATCH')
        return placement, terms

    def _host(self, conn, actor, placement, *, capability=True):
        account_authority(conn, actor)
        authority = org_authority(conn, actor.user_id, placement['organization_id'], 'OWNER', 'HOST_COORDINATOR')
        candidate = get_row(conn, 'candidate_profiles', placement['candidate_id'])
        if candidate['user_id'] == actor.user_id:
            raise PlacementScopeError('INDEPENDENT_HOST_REQUIRED', status_code=403)
        if capability:
            require_capability(conn, placement['organization_id'], 'INTERNSHIP_HOST')
        return authority

    def _candidate(self, conn, actor, placement):
        profile = get_row(conn, 'candidate_profiles', placement['candidate_id'])
        if profile['user_id'] != actor.user_id:
            raise PlacementScopeError('PLACEMENT_NOT_FOUND', status_code=404)
        account_authority(conn, actor)

    def _terms(self, placement, terms, terms_id, version):
        if placement['current_terms_id'] != terms_id or terms['version'] != version:
            raise PlacementScopeError('STALE_PLAN_VERSION')

    def _replay(self, conn, name, actor, key, digest):
        old = request_record(conn, name, actor, key, digest)
        if old:return dict(old['receipt'])

    def _consent(self, conn, actor, placement, terms, side, key, digest, *, grant=None, assignment=None):
        stamp, consent_id = now(), str(uuid4())
        receipt = dict(
            consent_id=consent_id,
            placement_id=placement['id'],
            terms_id=terms['id'],
            version=terms['version'],
            side=side,
            assignment_id=assignment,
            recorded_at=stamp.isoformat(),
            **({'contract_id': 'API-048'} if side == 'CANDIDATE' else {}),
        )
        conn.execute(table('placement_consents').insert().values(
            id=consent_id, created_at=stamp, placement_id=placement['id'], terms_id=terms['id'], side=side,
            **evidence(conn, actor), org_grant_id=grant, assignment_id=assignment,
            idempotency_key=key, request_fingerprint=digest, receipt=receipt))
        if side=='MENTOR':queue_notice(conn,placement['id'],assignment,'ACCEPTED',consent_id)
        self.audit.append_audit_event(actor_id=actor.user_id, action='PLACEMENT_'+side+'_ACCEPTED',
                                     entity_type='placement_consent', entity_id=consent_id)
        return receipt, stamp

    def _event(self, conn, actor, placement, terms, action, key, digest, grant, *, assignment=None):
        event_id, stamp = str(uuid4()), now()
        receipt = dict(event_id=event_id, placement_id=placement['id'], terms_id=terms['id'],
                       version=terms['version'], action=action, assignment_id=assignment, recorded_at=stamp.isoformat())
        if action in ('ACTIVATE', 'CANCEL'):
            receipt['status_at_decision'] = 'ACTIVE' if action == 'ACTIVATE' else 'CANCELLED'
        conn.execute(table('placement_admission_events').insert().values(
            id=event_id, created_at=stamp, placement_id=placement['id'], terms_id=terms['id'], action=action,
            **evidence(conn, actor), org_grant_id=grant, assignment_id=assignment,
            idempotency_key=key, request_fingerprint=digest, receipt=receipt))
        self.audit.append_audit_event(actor_id=actor.user_id, action='PLACEMENT_'+action,
                                     entity_type='placement_admission_event', entity_id=event_id)
        return receipt, stamp

    def accept_candidate(self, *, actor, placement_id, terms_id, version, idempotency_key):
        digest = fingerprint('CANDIDATE_ACCEPT', placement_id=placement_id, terms_id=terms_id, version=version)
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            self._candidate(conn, actor, placement)
            replay = self._replay(conn, 'placement_consents', actor, idempotency_key, digest)
            if replay:return replay
            self._terms(placement, terms, terms_id, version)
            if placement['status'] not in ('PLANNED', 'PENDING_START_CONFIRMATION'):
                raise PlacementScopeError('PLACEMENT_NOT_PLANNED')
            receipt, stamp = self._consent(conn, actor, placement, terms, 'CANDIDATE', idempotency_key, digest)
            conn.execute(table('placement_terms').update().where(table('placement_terms').c.id == terms_id)
                         .values(candidate_accepted_at=stamp, updated_at=stamp))
            return receipt

    def nominate_mentor(self, *, actor, placement_id, organization_id, mentor_id, idempotency_key):
        digest = fingerprint('MENTOR_NOMINATED', placement_id=placement_id, organization_id=organization_id, mentor_id=mentor_id)
        with transaction() as conn:
            placement, _ = self._locked(conn, placement_id)
            if organization_id != placement['organization_id']:
                raise PlacementScopeError('MENTOR_ORG_MISMATCH')
            authority = self._host(conn, actor, placement)
            replay = request_record(conn, 'mentor_assignment_proofs', actor, idempotency_key, digest)
            if replay:
                return nomination_result(get_row(conn,'mentor_assignments',replay['assignment_id']),replay['receipt'])
            if placement['status'] not in ('PLANNED', 'PENDING_START_CONFIRMATION', 'ACTIVE'):
                raise PlacementScopeError('PLACEMENT_NOT_ASSIGNABLE')
            try:membership = org_authority(conn, mentor_id, organization_id, 'MENTOR', nowait=True)
            except OperationalError as exc:
                if getattr(exc.orig, 'sqlstate', None) == '55P03':
                    raise PlacementScopeError('MENTOR_BUSY_RETRY') from exc
                raise
            if get_row(conn, 'candidate_profiles', placement['candidate_id'])['user_id'] == mentor_id:
                raise PlacementScopeError('SELF_MENTOR_FORBIDDEN', status_code=403)
            assignment = insert_row(conn, 'mentor_assignments', placement_id=placement_id,
                organization_id=organization_id, membership_id=membership['id'], assigned_by_id=actor.user_id, assigned_at=now())
            assignment = get_row(conn, 'mentor_assignments', assignment['id'])
            snapshot = conn.execute(text('SELECT to_jsonb(a) FROM flexbridge.mentor_assignments a WHERE a.id=:id'),
                                    {'id': assignment['id']}).scalar_one()
            receipt = dict(assignment_id=assignment['id'], placement_id=placement_id, mentor_user_id=mentor_id,
                           state_at_nomination='NOMINATED', recorded_at=assignment['assigned_at'].isoformat())
            conn.execute(table('mentor_assignment_proofs').insert().values(
                assignment_id=assignment['id'], placement_id=placement_id, origin='PUBLIC', created_at=now(),
                mentor_user_id=mentor_id, mentor_grant_id=membership['_authority_grant_id'],
                **evidence(conn, actor), host_grant_id=authority['_authority_grant_id'], initial_snapshot=snapshot,
                idempotency_key=idempotency_key, request_fingerprint=digest, receipt=receipt))
            queue_notice(conn,placement_id,assignment['id'],'NOMINATED',assignment['id'])
            self.audit.append_audit_event(actor_id=actor.user_id, action='MENTOR_ASSIGNMENT_NOMINATED',
                                         entity_type='mentor_assignment', entity_id=assignment['id'])
            return nomination_result(assignment,receipt)

    def _mentor(self, conn, actor, placement, assignment):
        q = table('mentor_assignment_proofs')
        proof = conn.execute(select(q).where(q.c.assignment_id == assignment['id'])).mappings().first()
        if (not proof or assignment['placement_id'] != placement['id'] or assignment['revoked_at']
            or proof['mentor_user_id'] != actor.user_id):
            raise PlacementScopeError('MENTOR_ASSIGNMENT_NOT_FOUND', status_code=404)
        account_authority(conn, actor)
        authority = org_authority(conn, actor.user_id, placement['organization_id'], 'MENTOR')
        if authority['id'] != assignment['membership_id'] or authority['_authority_grant_id'] != proof['mentor_grant_id']:
            raise PlacementScopeError('ORIGINAL_MENTOR_GRANT_REQUIRED', status_code=403)
        return authority

    def accept_mentor(self, *, actor, placement_id, assignment_id, terms_id, version, idempotency_key):
        digest = fingerprint('MENTOR_ACCEPT', placement_id=placement_id, assignment_id=assignment_id, terms_id=terms_id, version=version)
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            assignments = table('mentor_assignments')
            # Serialize competing personally accepted nominations under the placement lock.
            rows = [dict(r) for r in conn.execute(select(assignments).where(
                assignments.c.placement_id == placement_id).order_by(assignments.c.id).with_for_update()).mappings()]
            assignment = next((r for r in rows if r['id'] == assignment_id), None)
            if not assignment:raise PlacementScopeError('MENTOR_ASSIGNMENT_NOT_FOUND', status_code=404)
            authority = self._mentor(conn, actor, placement, assignment)
            replay = self._replay(conn, 'placement_consents', actor, idempotency_key, digest)
            if replay:return replay
            self._terms(placement, terms, terms_id, version)
            if placement['status'] not in ('PLANNED', 'PENDING_START_CONFIRMATION', 'ACTIVE'):
                raise PlacementScopeError('PLACEMENT_NOT_ASSIGNABLE')
            if any(r['accepted_at'] and not r['revoked_at'] and r['id'] != assignment_id for r in rows):
                raise PlacementScopeError('CURRENT_MENTOR_EXISTS')
            receipt, stamp = self._consent(conn, actor, placement, terms, 'MENTOR', idempotency_key, digest,
                                           grant=authority['_authority_grant_id'], assignment=assignment_id)
            if not assignment['accepted_at']:
                conn.execute(assignments.update().where(assignments.c.id == assignment_id).values(accepted_at=stamp, updated_at=stamp))
            return receipt

    def host_decision(self, *, actor, placement_id, terms_id, version, idempotency_key, action):
        if action not in ('ACTIVATE', 'CANCEL'):
            raise PlacementScopeError('HOST_DECISION_NOT_IMPLEMENTED', status_code=501)
        digest = fingerprint(action, placement_id=placement_id, terms_id=terms_id, version=version)
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            assignments = table('mentor_assignments')
            rows = [dict(r) for r in conn.execute(select(assignments).where(
                assignments.c.placement_id == placement_id).order_by(assignments.c.id).with_for_update()).mappings()]
            school_material=None
            if action=='ACTIVATE' and placement['academic_track']:
                from app.services.academic_admission import academic_service
                school_material=academic_service.start_material(conn,placement)
            authority = self._host(conn, actor, placement)
            replay = self._replay(conn, 'placement_admission_events', actor, idempotency_key, digest)
            if replay:return replay
            self._terms(placement, terms, terms_id, version)
            if placement['status'] not in (('PLANNED', 'PENDING_START_CONFIRMATION') if action == 'ACTIVATE'
                                            else ('PLANNED', 'PENDING_START_CONFIRMATION', 'ACTIVE')):
                raise PlacementScopeError('PLACEMENT_NOT_CONFIRMABLE')
            if action == 'ACTIVATE':
                intake = table('placement_intakes')
                academic = conn.execute(select(intake.c.academic_required).where(intake.c.placement_id == placement_id)).scalar_one()
                if academic:
                    from app.services.academic_admission import academic_service
                    academic_service.pin_start_authority(conn,placement,terms,school_material)
                # Pin the original current mentor grant through commit, after business rows.
                found = False
                consents, proofs = table('placement_consents'), table('mentor_assignment_proofs')
                for assignment in rows:
                    if assignment['revoked_at'] or not assignment['accepted_at']:continue
                    proof = conn.execute(select(proofs).where(proofs.c.assignment_id == assignment['id'])).mappings().first()
                    consent = conn.execute(select(consents.c.id).where(consents.c.assignment_id == assignment['id'],
                        consents.c.terms_id == terms_id, consents.c.side == 'MENTOR')).first()
                    if not proof or not consent:continue
                    try:
                        mentor = org_authority(conn, proof['mentor_user_id'], placement['organization_id'], 'MENTOR', nowait=True)
                    except OperationalError as exc:
                        if getattr(exc.orig, 'sqlstate', None) == '55P03':raise PlacementScopeError('MENTOR_BUSY_RETRY') from exc
                        raise
                    if mentor['_authority_grant_id'] == proof['mentor_grant_id']:
                        found = True
                        break
                if not found:raise PlacementScopeError('PERSONAL_MENTOR_ACCEPTANCE_REQUIRED')
                ready = conn.execute(text('SELECT flexbridge.placement_ready_for_start(:p,:t)'), {'p': placement_id, 't': terms_id}).scalar_one()
                if not ready:raise PlacementScopeError('CANDIDATE_PLAN_ACCEPTANCE_REQUIRED')
                _, accepted = self._consent(conn, actor, placement, terms, 'HOST', idempotency_key, digest,
                                             grant=authority['_authority_grant_id'])
                conn.execute(table('placement_terms').update().where(table('placement_terms').c.id == terms_id)
                             .values(host_accepted_at=accepted, updated_at=accepted))
            receipt, stamp = self._event(conn, actor, placement, terms, action, idempotency_key, digest, authority['_authority_grant_id'])
            conn.execute(table('placements').update().where(table('placements').c.id == placement_id)
                         .values(status='ACTIVE' if action == 'ACTIVATE' else 'CANCELLED', updated_at=stamp, version=placement['version']+1))
            insert_row(conn, 'placement_decisions', placement_id=placement_id, actor_id=actor.user_id,
                       side='HOST', decision=action, terms_id=terms_id, decided_at=stamp)
            return receipt

    def publish_plan(self, *, actor, placement_id, terms_id, version, idempotency_key,
                     title, objectives, daily_limit_minutes, weekly_limit_minutes, required_minutes, tasks):
        content = dict(title=title, objectives=objectives, daily_limit_minutes=daily_limit_minutes,
                       weekly_limit_minutes=weekly_limit_minutes, required_minutes=required_minutes, tasks=tasks)
        digest = fingerprint('PLAN_PUBLISHED', placement_id=placement_id, terms_id=terms_id, version=version, content=content)
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            authority = self._host(conn, actor, placement)
            replay = self._replay(conn, 'placement_admission_events', actor, idempotency_key, digest)
            if replay:return replay
            self._terms(placement, terms, terms_id, version)
            if placement['status'] not in ('PLANNED', 'PENDING_START_CONFIRMATION'):
                raise PlacementScopeError('ACTIVE_PLAN_AMENDMENT_REQUIRED')
            if (not title.strip() or not objectives.strip() or not 1 <= daily_limit_minutes <= 1440
                or not daily_limit_minutes <= weekly_limit_minutes <= 10080 or required_minutes < 0
                or not 1 <= len(tasks) <= 100 or len({t['code'] for t in tasks}) != len(tasks)):
                raise PlacementScopeError('INVALID_PLAN', status_code=422)
            _, _, revision = require_internship_placement(conn, placement)
            new_terms = insert_row(conn, 'placement_terms', placement_id=placement_id, version=terms['version']+1,
                schema_version=1, terms_snapshot={'source_revision_id': revision['id'], 'title': title, 'objectives': objectives,
                    **({'academic_scope':terms['terms_snapshot']['academic_scope']} if 'academic_scope' in terms['terms_snapshot'] else {})},
                daily_limit_minutes=daily_limit_minutes, weekly_limit_minutes=weekly_limit_minutes, required_minutes=required_minutes)
            conn.execute(table('placements').update().where(table('placements').c.id == placement_id)
                .values(current_terms_id=new_terms['id'], updated_at=now(), version=placement['version']+1))
            for task in tasks:
                insert_row(conn, 'plan_tasks', terms_id=new_terms['id'], **task)
            placement = {**placement, 'current_terms_id': new_terms['id']}
            receipt, _ = self._event(conn, actor, placement, new_terms, 'PLAN_PUBLISHED', idempotency_key, digest, authority['_authority_grant_id'])
            return receipt

    def revoke_mentor(self, *, actor, placement_id, assignment_id, terms_id, version, idempotency_key):
        digest = fingerprint('MENTOR_REVOKED', placement_id=placement_id, assignment_id=assignment_id, terms_id=terms_id, version=version)
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            assignment = get_row(conn, 'mentor_assignments', assignment_id, True)
            if assignment['placement_id'] != placement_id:
                raise PlacementScopeError('MENTOR_ASSIGNMENT_NOT_FOUND', status_code=404)
            authority = self._host(conn, actor, placement)
            replay = self._replay(conn, 'placement_admission_events', actor, idempotency_key, digest)
            if replay:return replay
            self._terms(placement, terms, terms_id, version)
            if assignment['revoked_at']:
                raise PlacementScopeError('MENTOR_ALREADY_REVOKED')
            receipt, stamp = self._event(conn, actor, placement, terms, 'MENTOR_REVOKED', idempotency_key, digest,
                                          authority['_authority_grant_id'], assignment=assignment_id)
            conn.execute(table('mentor_assignments').update().where(table('mentor_assignments').c.id == assignment_id)
                .values(revoked_at=stamp, updated_at=stamp))
            queue_notice(conn,placement_id,assignment_id,'REVOKED',receipt['event_id'])
            return receipt

    def plan(self, *, actor, placement_id):
        from app.services.governance import GovernanceError
        with transaction() as conn:
            placement, terms = self._locked(conn, placement_id)
            assignments = table('mentor_assignments')
            nominated = [dict(r) for r in conn.execute(select(assignments).where(
                assignments.c.placement_id == placement_id).order_by(assignments.c.id).with_for_update()).mappings()]
            school_material=None
            if placement['academic_track']:
                from app.services.academic_admission import academic_service
                school_material=academic_service.start_material(conn,placement)
            account_authority(conn, actor)
            if get_row(conn, 'candidate_profiles', placement['candidate_id'])['user_id'] != actor.user_id:
                try:org_authority(conn, actor.user_id, placement['organization_id'], 'OWNER', 'HOST_COORDINATOR')
                except GovernanceError:
                    allowed = False
                    for assignment in nominated:
                        try:
                            self._mentor(conn, actor, placement, assignment)
                            allowed = True
                            break
                        except (PlacementScopeError, GovernanceError):continue
                    if not allowed and school_material:
                        for assignment in school_material[1]:
                            try:
                                academic_service.teacher(conn,actor,placement,assignment)
                                if conn.execute(text('SELECT flexbridge.academic_supervision_current(:s,:c)'),
                                    {'s':assignment['supervision_id'],'c':placement['candidate_id']}).scalar_one():
                                    allowed=True;break
                            except (PlacementScopeError,GovernanceError):continue
                    if not allowed:raise PlacementScopeError('PLACEMENT_NOT_FOUND', status_code=404)
            t = table('plan_tasks')
            tasks = [dict(r) for r in conn.execute(select(t.c.code, t.c.title, t.c.expected_result, t.c.required,
                t.c.target_minutes).where(t.c.terms_id == terms['id']).order_by(t.c.code)).mappings()]
            # The original revision/offer can contain payroll details. Plan readers get this projection only.
            return dict(placement_id=placement_id, status=placement['status'], terms_id=terms['id'], version=terms['version'],
                start_date=placement['start_date'], end_date=placement['end_date'],
                academic_required=bool(conn.execute(select(table('placement_intakes').c.academic_required)
                    .where(table('placement_intakes').c.placement_id==placement_id)).scalar_one()),
                academic_scope={k:v for k,v in terms['terms_snapshot'].get('academic_scope',{}).items() if k in ('institution_id','purpose')},
                title=terms['terms_snapshot'].get('title'), objectives=terms['terms_snapshot'].get('objectives'),
                daily_limit_minutes=terms['daily_limit_minutes'], weekly_limit_minutes=terms['weekly_limit_minutes'],
                required_minutes=terms['required_minutes'], tasks=tasks)

    def own_placements(self, actor, *, limit=50, after=None):
        with transaction() as conn:
            account_authority(conn, actor)
            p, c = table('placements'), table('candidate_profiles')
            query=select(p.c.id, p.c.organization_id, p.c.status,
                p.c.start_date, p.c.end_date, p.c.current_terms_id).join(c, c.c.id == p.c.candidate_id)
            query=query.where(c.c.user_id == actor.user_id)
            return page(conn,query,p.c.id,p.c.created_at,limit=limit,after=after)

    def host_placements(self, actor, organization_id, *, limit=50, after=None):
        with transaction() as conn:
            get_row(conn, 'organizations', organization_id, True)
            account_authority(conn, actor)
            org_authority(conn, actor.user_id, organization_id, 'OWNER', 'HOST_COORDINATOR')
            p = table('placements')
            query=select(p.c.id,p.c.candidate_id,p.c.status,p.c.start_date,p.c.end_date,p.c.current_terms_id)
            query=query.where(p.c.organization_id==organization_id)
            return page(conn,query,p.c.id,p.c.created_at,limit=limit,after=after)

    def own_mentor_assignments(self, actor, *, limit=50, after=None):
        with transaction() as conn:
            account_authority(conn, actor)
            a, q, m, g, r = (table(n) for n in ('mentor_assignments', 'mentor_assignment_proofs',
                                               'org_memberships', 'org_role_grants', 'role_catalog'))
            query=select(a.c.id, a.c.placement_id, a.c.organization_id,
                a.c.assigned_at, a.c.accepted_at).join(q, q.c.assignment_id == a.c.id).join(m, m.c.id == a.c.membership_id)
            query=query.join(g,g.c.id==q.c.mentor_grant_id).join(r,r.c.id==g.c.role_id).where(
                    q.c.mentor_user_id == actor.user_id, m.c.user_id == actor.user_id,
                    g.c.membership_id == m.c.id, m.c.status == 'ACTIVE', m.c.revoked_at.is_(None),
                    g.c.revoked_at.is_(None), r.c.code == 'MENTOR', r.c.scope_kind == 'ORG', a.c.revoked_at.is_(None))
            return page(conn,query,a.c.id,a.c.assigned_at,limit=limit,after=after)


admission_service = PlacementAdmissionService()
