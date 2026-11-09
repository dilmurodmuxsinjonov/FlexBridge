"""Opaque 24-hour invitations; contact proof, explicit role and current inviter authority."""
from datetime import timedelta
import hmac
import secrets
from fastapi import HTTPException
from sqlalchemy import select, or_, func, text
from sqlalchemy.exc import OperationalError

from app.api.dependencies import ActorContext, require_org
from app.core.iam_security import digest, normalize_contact, rate_limit
from app.db.storage import table, transaction, now
from app.services.governance import GovernanceError
from app.services.organizations import require_mfa, role_id, audit
from app.services.placements import get_row, insert_row
from app.services.identity import contact_row
from app.services.authority import mfa_authority, org_authority

ALLOWED_ROLES = ('HR','HOST_COORDINATOR','MENTOR','BILLING')


def unavailable():
    return GovernanceError('INVITATION_NOT_AVAILABLE', status_code=404)


def contact_digest(channel, value):
    return digest('org-invite-contact', channel + ':' + value)


def busy():
    return GovernanceError('INVITATION_BUSY_RETRY',status_code=409)


def lock_contact(conn,value):
    # Contact rebinding holds this lock before rotating the old owner's security.
    # Never wait for it while holding user authority; abort the whole UOW for retry.
    acquired=conn.execute(text('SELECT pg_try_advisory_xact_lock(hashtextextended(:key,0))'),
        {'key':digest('contact-lock',value)}).scalar_one()
    if not acquired:raise busy()


def lock_target_user(conn,user_id):
    users=table('users')
    try:
        conn.execute(select(users.c.id).where(users.c.id==user_id).with_for_update(read=True,nowait=True)).first()
    except OperationalError as exc:
        if getattr(exc.orig,'sqlstate',None)=='55P03':raise busy() from exc
        raise


def revoke_pending_for_member(conn, org_id, membership):
    invites, contacts = table('org_invitations'), table('user_contacts')
    hashes = [contact_digest(r['channel'],r['normalized_value']) for r in conn.execute(select(contacts).where(
        contacts.c.user_id == membership['user_id'],contacts.c.verified_at.is_not(None),contacts.c.revoked_at.is_(None))).mappings()]
    conn.execute(invites.update().where(invites.c.organization_id == org_id, invites.c.accepted_at.is_(None),
        invites.c.revoked_at.is_(None), or_(invites.c.inviter_membership_id == membership['id'],
            invites.c.target_user_id == membership['user_id'], invites.c.contact_digest.in_(hashes)))
        .values(revoked_at=now(),updated_at=now()))


class InvitationService:
    def create(self, actor, org_id, *, channel, destination, role_code):
        require_mfa(actor)
        if role_code not in ALLOWED_ROLES:
            raise GovernanceError('INVITATION_ROLE_FORBIDDEN', status_code=422)
        value = normalize_contact(channel,destination)
        rate_limit('org-invite-create',actor.user_id,20,3600)
        with transaction() as conn:
            org = get_row(conn,'organizations',org_id,True)
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,org_id,'OWNER')
            if org['status'] != 'VERIFIED': raise GovernanceError('ORGANIZATION_NOT_VERIFIED')
            members = table('org_memberships')
            member = conn.execute(select(members).where(members.c.organization_id == org_id,
                members.c.user_id == actor.user_id,members.c.status == 'ACTIVE',members.c.revoked_at.is_(None))).mappings().one()
            initial = contact_row(conn,channel,value)
            # Pin the FK target before taking the contact lock. A binder may hold
            # that user first, so waiting here could also complete a lock cycle.
            if initial and initial['user_id']!=actor.user_id:lock_target_user(conn,initial['user_id'])
            lock_contact(conn,channel+':'+value)
            target = contact_row(conn,channel,value)
            if ((initial['id'],initial['user_id']) if initial else None) != ((target['id'],target['user_id']) if target else None):
                raise busy()
            if target and target['user_id'] == actor.user_id:
                raise GovernanceError('SELF_INVITATION_FORBIDDEN',status_code=403)
            rid, hashed_contact = role_id(conn,role_code), contact_digest(channel,value)
            invites = table('org_invitations')
            conn.execute(invites.update().where(invites.c.organization_id == org_id,
                invites.c.contact_digest == hashed_contact, invites.c.role_id == rid,
                invites.c.accepted_at.is_(None),invites.c.revoked_at.is_(None)).values(revoked_at=now(),updated_at=now()))
            token = secrets.token_urlsafe(32)
            row = insert_row(conn,'org_invitations',organization_id=org_id,inviter_membership_id=member['id'],
                contact_digest=hashed_contact,token_digest=digest('org-invite-token',token),expires_at=now()+timedelta(hours=24),
                role_id=rid,channel=channel,target_user_id=target['user_id'] if target else None,
                target_contact_id=target['id'] if target else None)
            audit.append_audit_event(actor_id=actor.user_id,action='ORG_INVITATION_CREATED',entity_type='org_invitation',entity_id=row['id'],
                metadata={'role_code':role_code})
            return {'id':row['id'],'role_code':role_code,'expires_at':row['expires_at'],
                'token':token,'preview_path':'/api/v1/invitations/'+token}

    def _lookup(self,conn,token,lock=False):
        invitations = table('org_invitations')
        query = select(invitations).where(invitations.c.token_digest == digest('org-invite-token',token))
        row = conn.execute(query.with_for_update() if lock else query).mappings().first()
        if not row: raise unavailable()
        return dict(row)

    def _current_inviter(self,conn,invite,*,hold_authority=False):
        org = get_row(conn,'organizations',invite['organization_id'])
        inviter = get_row(conn,'org_memberships',invite['inviter_membership_id'])
        user = get_row(conn,'users',inviter['user_id'])
        if org['status'] != 'VERIFIED' or inviter['organization_id'] != org['id'] or user['status'] != 'ACTIVE':
            raise unavailable()
        try:
            if hold_authority:org_authority(conn,user['id'],org['id'],'OWNER',nowait=True)
            else:require_org(ActorContext(user['id'],'',()),org['id'],'OWNER')
        except OperationalError as exc:
            if getattr(exc.orig,'sqlstate',None)=='55P03':raise busy() from exc
            raise
        except (HTTPException,GovernanceError) as exc:
            if exc.status_code == 403: raise unavailable() from exc
            raise
        role = get_row(conn,'role_catalog',invite['role_id']) if invite['role_id'] else None
        if not role or role['scope_kind'] != 'ORG' or role['code'] not in ALLOWED_ROLES: raise unavailable()
        return org,inviter,role

    def preview(self,token):
        with transaction() as conn:
            invite = self._lookup(conn,token)
            if invite['revoked_at'] or invite['accepted_at'] or invite['expires_at'] <= now(): raise unavailable()
            org,inviter,role = self._current_inviter(conn,invite)
            return {'organization':{'id':org['id'],'public_name':org['public_name']},
                'role_code':role['code'],'expires_at':invite['expires_at'],'requires_login':True,'requires_mfa':True}

    def _contact(self,conn,actor,invite):
        contacts = table('user_contacts')
        rows = list(conn.execute(select(contacts).where(contacts.c.user_id == actor.user_id,
            contacts.c.channel == invite['channel'],contacts.c.verified_at.is_not(None),contacts.c.revoked_at.is_(None))).mappings())
        match = next((r for r in rows if hmac.compare_digest(contact_digest(r['channel'],r['normalized_value']),invite['contact_digest'])),None)
        if not match: raise GovernanceError('INVITATION_CONTACT_MISMATCH',status_code=403)
        lock_contact(conn,match['channel']+':'+match['normalized_value'])
        current = contact_row(conn,match['channel'],match['normalized_value'])
        if (not current or current['id'] != match['id'] or current['user_id'] != actor.user_id or
            (invite['target_user_id'] and invite['target_user_id'] != actor.user_id) or
            (invite['target_contact_id'] and invite['target_contact_id'] != current['id'])):
            raise GovernanceError('INVITATION_CONTACT_MISMATCH',status_code=403)

    def accept(self,actor,token):
        require_mfa(actor)
        rate_limit('org-invite-accept',actor.user_id,30,600)
        with transaction() as conn:
            first = self._lookup(conn,token)
            get_row(conn,'organizations',first['organization_id'],True)
            invite = self._lookup(conn,token,True)
            memberships,grants = table('org_memberships'),table('org_role_grants')
            member = conn.execute(select(memberships).where(memberships.c.organization_id == invite['organization_id'],
                memberships.c.user_id == actor.user_id).with_for_update()).mappings().first()
            mfa_authority(conn,actor)
            if invite['accepted_at']:
                grant = conn.execute(select(grants.c.id).where(grants.c.membership_id == member['id'],
                    grants.c.role_id == invite['role_id'],grants.c.revoked_at.is_(None))).first() if member else None
                if invite['accepted_by_id'] != actor.user_id: raise unavailable()
                if not member or member['status'] != 'ACTIVE' or member['revoked_at'] or not grant:
                    raise GovernanceError('ACCEPTED_MEMBERSHIP_NO_LONGER_ACTIVE')
                return {'membership_id':member['id'],'status':'ACTIVE','idempotent_replay':True}
            if invite['revoked_at'] or invite['expires_at'] <= now(): raise unavailable()
            org,inviter,role = self._current_inviter(conn,invite,hold_authority=True)
            if inviter['user_id'] == actor.user_id: raise GovernanceError('SELF_INVITATION_FORBIDDEN',status_code=403)
            self._contact(conn,actor,invite)
            if member and member['status'] == 'REVOKED' and not member['revoked_at']: raise unavailable()
            if member and member['revoked_at'] and invite['created_at'] <= member['revoked_at']:
                raise unavailable()
            last_revoked = conn.execute(select(func.max(grants.c.revoked_at)).where(
                grants.c.membership_id == member['id'],grants.c.role_id == invite['role_id'],
                grants.c.revoked_at.is_not(None))).scalar_one() if member else None
            if last_revoked and invite['created_at'] <= last_revoked: raise unavailable()
            grant = conn.execute(select(grants).where(grants.c.membership_id == member['id'],
                grants.c.role_id == invite['role_id'],grants.c.revoked_at.is_(None)).with_for_update()).mappings().first() if member else None
            if not member:
                member = insert_row(conn,'org_memberships',organization_id=org['id'],user_id=actor.user_id,
                    status='ACTIVE',accepted_at=now())
            else:
                if member['status'] != 'ACTIVE' or member['revoked_at']:
                    conn.execute(grants.update().where(grants.c.membership_id == member['id'],
                        grants.c.role_id != invite['role_id'],grants.c.revoked_at.is_(None))
                        .values(revoked_at=now(),updated_at=now()))
                conn.execute(memberships.update().where(memberships.c.id == member['id']).values(
                    status='ACTIVE',accepted_at=now(),revoked_at=None,updated_at=now()))
            if not grant:
                insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=role['id'],granted_by_id=inviter['user_id'])
            conn.execute(table('org_invitations').update().where(table('org_invitations').c.id == invite['id'])
                .values(accepted_by_id=actor.user_id,accepted_at=now(),updated_at=now()))
            audit.append_audit_event(actor_id=actor.user_id,action='ORG_INVITATION_ACCEPTED',entity_type='org_invitation',
                entity_id=invite['id'],metadata={'role_code':role['code']})
            return {'membership_id':member['id'],'status':'ACTIVE','role_code':role['code'],'idempotent_replay':False}

    def revoke(self,actor,org_id,invitation_id,reason):
        require_mfa(actor)
        with transaction() as conn:
            get_row(conn,'organizations',org_id,True)
            invite = get_row(conn,'org_invitations',invitation_id,True)
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,org_id,'OWNER')
            if invite['organization_id'] != org_id: raise GovernanceError('ORG_SCOPE_FORBIDDEN',status_code=403)
            if invite['accepted_at']: raise GovernanceError('INVITATION_ALREADY_ACCEPTED_USE_MEMBERSHIP_REVOKE')
            if not invite['revoked_at']:
                conn.execute(table('org_invitations').update().where(table('org_invitations').c.id == invitation_id)
                    .values(revoked_at=now(),updated_at=now()))
                audit.append_audit_event(actor_id=actor.user_id,action='ORG_INVITATION_REVOKED',entity_type='org_invitation',
                    entity_id=invitation_id,metadata={'reason':reason})
            return {'id':invitation_id,'status':'REVOKED'}


invitation_service = InvitationService()
