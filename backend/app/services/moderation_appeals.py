"""Authenticated, pinned opportunity rejection appeals; no caller-supplied identities."""
from dataclasses import dataclass,field
from datetime import timedelta
from sqlalchemy import select,or_,and_,exists,text,func,cast,literal,Text
from sqlalchemy.dialects.postgresql import JSONB
from app.api.dependencies import require_org,require_platform
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import rate_limit
from app.db.storage import table,transaction,now
from app.services.governance import GovernanceError
from app.services.organizations import require_mfa
from app.services.placements import get_row,insert_row
from app.services.authority import mfa_authority,moderator_authority


def justification(value):
    if not isinstance(value,str) or not 15<=len(value.strip())<=4000:
        raise GovernanceError('APPEAL_REASON_REQUIRED',status_code=422)
    return value.strip()


def independent(conn,actor,request,opportunity):
    original=get_row(conn,'moderation_actions',request['original_action_id'])
    revision=get_row(conn,'opportunity_revisions',request['revision_id'])
    members=table('org_memberships')
    related=conn.execute(select(members.c.id).where(members.c.organization_id==opportunity['organization_id'],
        members.c.user_id==actor.user_id).limit(1)).first()
    if actor.user_id in (original['actor_id'],request['appellant_id'],revision['author_id']) or related:
        raise GovernanceError('APPEAL_REVIEWER_CONFLICT',status_code=403)


def locked_request(conn,case_id):
    requests=table('moderation_appeal_requests')
    request=conn.execute(select(requests).where(requests.c.case_id==case_id)).mappings().first()
    if not request:raise GovernanceError('APPEAL_NOT_FOUND',status_code=404)
    opportunity=get_row(conn,'opportunities',request['opportunity_id'])
    get_row(conn,'organizations',opportunity['organization_id'],True)
    opportunity=get_row(conn,'opportunities',request['opportunity_id'],True)
    request=dict(conn.execute(select(requests).where(requests.c.case_id==case_id).with_for_update()).mappings().one())
    case=get_row(conn,'moderation_cases',case_id,True)
    return request,opportunity,case


def latest_decision(conn,opportunity_id):
    actions,cases=table('moderation_actions'),table('moderation_cases')
    return conn.execute(select(actions.c.id).join(cases,cases.c.id==actions.c.case_id).where(
        cases.c.opportunity_id==opportunity_id,actions.c.action.in_(('APPROVE','REJECT')))
        .order_by(actions.c.occurred_at.desc(),actions.c.created_at.desc(),actions.c.id.desc()).limit(1)).scalar_one_or_none()


def revision_evidence(conn,revision_id):
    return conn.execute(text('SELECT flexbridge.moderation_revision_snapshot(CAST(:id AS uuid))'),{'id':revision_id}).scalar_one()


def decision_evidence(conn,action_id):
    return conn.execute(text('SELECT flexbridge.moderation_decision_snapshot(CAST(:id AS uuid))'),{'id':action_id}).scalar_one()


@dataclass
class ModerationAppealsService:
    audit_store:AppendOnlyAuditStore=field(default_factory=AppendOnlyAuditStore)

    def submit(self,actor,action_id,reason):
        reason=justification(reason);require_mfa(actor)
        rate_limit('moderation-appeal',actor.user_id,20,600)
        with transaction() as conn:
            original=get_row(conn,'moderation_actions',action_id)
            original_case=get_row(conn,'moderation_cases',original['case_id'])
            if original['action']!='REJECT' or not original_case['opportunity_id']:
                raise GovernanceError('UNSUPPORTED_APPEAL_TARGET',status_code=422)
            opportunity=get_row(conn,'opportunities',original_case['opportunity_id'])
            get_row(conn,'organizations',opportunity['organization_id'],True)
            opportunity=get_row(conn,'opportunities',opportunity['id'],True)
            mfa_authority(conn,actor)
            require_org(actor,opportunity['organization_id'],'OWNER','HR','HOST_COORDINATOR')
            requests=table('moderation_appeal_requests')
            existing=conn.execute(select(requests).where(requests.c.original_action_id==action_id)).mappings().first()
            if existing:
                if existing['appellant_id']!=actor.user_id or existing['reason']!=reason:
                    raise GovernanceError('APPEAL_ALREADY_SUBMITTED')
                return self._report(existing,idempotent_replay=True)
            if opportunity['status']!='REJECTED' or latest_decision(conn,opportunity['id'])!=action_id:
                raise GovernanceError('APPEAL_DECISION_STALE')
            revision=get_row(conn,'opportunity_revisions',opportunity['current_revision_id'])
            # JSON primitives pin the actual evidence, even after a later draft revision.
            snapshot=revision_evidence(conn,revision['id'])
            original_decision=decision_evidence(conn,action_id)
            for value in (snapshot,original_decision):
                size=conn.execute(select(func.octet_length(cast(literal(value,type_=JSONB),Text)))).scalar_one()
                if size>524288:raise GovernanceError('APPEAL_SNAPSHOT_TOO_LARGE',status_code=422)
            case=insert_row(conn,'moderation_cases',reporter_id=actor.user_id,opportunity_id=opportunity['id'],
                category='OPPORTUNITY_REJECTION_APPEAL',status='OPEN',severity='LOW',due_at=now()+timedelta(hours=48))
            record=dict(case_id=case['id'],created_at=now(),original_action_id=action_id,opportunity_id=opportunity['id'],
                revision_id=revision['id'],appellant_id=actor.user_id,reason=reason,revision_snapshot=snapshot,
                original_decision=original_decision,status='OPEN',
                reviewer_id=None,decision=None,decision_reason=None,resolved_at=None)
            conn.execute(requests.insert().values(**record))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='MODERATION_APPEAL_SUBMITTED',
                entity_type='moderation_case',entity_id=case['id'],metadata={'original_action_id':action_id,'revision_id':revision['id']})
            return self._report(record,idempotent_replay=False)

    def read(self,actor,case_id):
        require_mfa(actor)
        with transaction() as conn:
            requests=table('moderation_appeal_requests')
            row=conn.execute(select(requests).where(requests.c.case_id==case_id)).mappings().first()
            if not row:raise GovernanceError('APPEAL_NOT_FOUND',status_code=404)
            if actor.user_id==row['appellant_id']:
                mfa_authority(conn,actor)
            else:
                moderator_authority(conn,actor)
                independent(conn,actor,row,get_row(conn,'opportunities',row['opportunity_id']))
                if row['reviewer_id']!=actor.user_id:raise GovernanceError('APPEAL_NOT_ASSIGNED',status_code=403)
            return {**self._report(row),'revision_snapshot':row['revision_snapshot']}

    def queue(self,actor,limit=50,after=None):
        require_platform(actor,'MODERATOR');require_mfa(actor)
        if type(limit) is not int or not 1<=limit<=100:raise GovernanceError('INVALID_PAGE_LIMIT',status_code=422)
        requests,cases,actions,opps,revisions,members=(table(n) for n in (
            'moderation_appeal_requests','moderation_cases','moderation_actions','opportunities','opportunity_revisions','org_memberships'))
        with transaction() as conn:
            moderator_authority(conn,actor)
            query=select(requests.c.case_id,requests.c.created_at,requests.c.status,cases.c.due_at).select_from(
                requests.join(cases,cases.c.id==requests.c.case_id).join(actions,actions.c.id==requests.c.original_action_id)
                .join(opps,opps.c.id==requests.c.opportunity_id).join(revisions,revisions.c.id==requests.c.revision_id)).where(
                or_(requests.c.status=='OPEN',and_(requests.c.status=='ASSIGNED',requests.c.reviewer_id==actor.user_id)),
                requests.c.appellant_id!=actor.user_id,actions.c.actor_id!=actor.user_id,revisions.c.author_id!=actor.user_id,
                ~exists(select(members.c.id).where(members.c.organization_id==opps.c.organization_id,members.c.user_id==actor.user_id)))
            if after:query=query.where(requests.c.case_id>after)
            rows=[dict(r) for r in conn.execute(query.order_by(requests.c.case_id).limit(limit+1)).mappings()]
            return {'items':rows[:limit],'next_cursor':rows[limit-1]['case_id'] if len(rows)>limit else None}

    def claim(self,actor,case_id):
        require_platform(actor,'MODERATOR');require_mfa(actor)
        with transaction() as conn:
            row,opportunity,case=locked_request(conn,case_id)
            moderator_authority(conn,actor)
            independent(conn,actor,row,opportunity)
            if row['status']=='ASSIGNED' and row['reviewer_id']==actor.user_id:
                return self._report(row,idempotent_replay=True)
            if row['status']!='OPEN':raise GovernanceError('APPEAL_ALREADY_ASSIGNED')
            row={**row,'status':'ASSIGNED','reviewer_id':actor.user_id}
            conn.execute(table('moderation_appeal_requests').update().where(table('moderation_appeal_requests').c.case_id==case_id)
                .values(status='ASSIGNED',reviewer_id=actor.user_id))
            conn.execute(table('moderation_cases').update().where(table('moderation_cases').c.id==case_id)
                .values(status='IN_REVIEW',assigned_to_id=actor.user_id,updated_at=now()))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='MODERATION_APPEAL_ASSIGNED',entity_type='moderation_case',entity_id=case_id)
            return self._report(row,idempotent_replay=False)

    def decide(self,actor,case_id,decision,reason):
        require_platform(actor,'MODERATOR');require_mfa(actor);reason=justification(reason)
        if decision not in ('UPHOLD','REOPEN'):raise GovernanceError('INVALID_APPEAL_DECISION',status_code=422)
        with transaction() as conn:
            row,opportunity,case=locked_request(conn,case_id)
            moderator_authority(conn,actor)
            independent(conn,actor,row,opportunity)
            if row['reviewer_id']!=actor.user_id or case['assigned_to_id']!=actor.user_id:
                raise GovernanceError('APPEAL_NOT_ASSIGNED',status_code=403)
            if row['status']=='RESOLVED':
                if row['decision']==decision and row['decision_reason']==reason:
                    return self._report(row,idempotent_replay=True)
                raise GovernanceError('APPEAL_ALREADY_RESOLVED')
            if row['status']!='ASSIGNED' or case['status']!='IN_REVIEW':raise GovernanceError('APPEAL_STATE_CONFLICT')
            if (opportunity['status']!='REJECTED' or opportunity['current_revision_id']!=row['revision_id'] or
                latest_decision(conn,opportunity['id'])!=row['original_action_id'] or
                revision_evidence(conn,row['revision_id'])!=row['revision_snapshot'] or
                decision_evidence(conn,row['original_action_id'])!=row['original_decision']):
                raise GovernanceError('APPEAL_DECISION_STALE')
            resolved=now()
            conn.execute(table('moderation_appeal_requests').update().where(table('moderation_appeal_requests').c.case_id==case_id)
                .values(status='RESOLVED',decision=decision,decision_reason=reason,resolved_at=resolved))
            conn.execute(table('moderation_cases').update().where(table('moderation_cases').c.id==case_id)
                .values(status='RESOLVED',decision=decision,decided_at=resolved,updated_at=resolved))
            insert_row(conn,'moderation_actions',case_id=case_id,actor_id=actor.user_id,action='APPEAL_'+decision,
                reason=reason,appealed_action_id=row['original_action_id'],occurred_at=resolved)
            if decision=='REOPEN':
                conn.execute(table('opportunities').update().where(table('opportunities').c.id==opportunity['id'])
                    .values(status='DRAFT',updated_at=resolved))
            self.audit_store.append_audit_event(actor_id=actor.user_id,action='MODERATION_APPEAL_'+decision,
                entity_type='moderation_case',entity_id=case_id,metadata={'original_action_id':row['original_action_id'],'revision_id':row['revision_id']})
            return self._report({**row,'status':'RESOLVED','decision':decision,'decision_reason':reason,'resolved_at':resolved},idempotent_replay=False)

    def _report(self,row,**extra):
        return {key:row[key] for key in ('case_id','created_at','original_action_id','opportunity_id','revision_id',
            'appellant_id','reason','original_decision','status','reviewer_id','decision','decision_reason','resolved_at')}|extra
