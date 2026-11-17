"""Transactional in-app mentor notices. No email/SMS/provider delivery is implied."""
from uuid import UUID, uuid4
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction, now, enqueue
from app.services.authority import account_authority
from app.services.pagination import page
from app.services.placements import get_row, PlacementScopeError

EVENT_TYPE='PLACEMENT_MENTOR_NOTICE'
SCOPES={'NOMINATED':['PLAN'],'ACCEPTED':['PLAN','WORKPLACE_DIARY_REVIEW'],'REVOKED':[]}


def queue_notice(conn, placement_id, assignment_id, kind, evidence_id):
    if kind not in SCOPES:raise ValueError('Unsupported mentor notice')
    enqueue(conn,EVENT_TYPE,placement_id,dict(placement_id=placement_id,assignment_id=assignment_id,
        kind=kind,evidence_id=evidence_id),'mentor-notice:'+kind+':'+evidence_id)


def run_notice(event):
    """Validate the local envelope; the fenced apply transaction creates the inbox row."""
    payload=event['payload']
    if event['event_type']!=EVENT_TYPE or event['schema_version']!=1 or payload['kind'] not in SCOPES:
        raise ValueError('Invalid mentor notice envelope')
    return {**{name:str(UUID(str(payload[name]))) for name in ('placement_id','assignment_id','evidence_id')},
            'kind':payload['kind']}


def notice_source(conn, payload):
    placement=get_row(conn,'placements',payload['placement_id'])
    assignment=get_row(conn,'mentor_assignments',payload['assignment_id'])
    q=table('mentor_assignment_proofs')
    proof=conn.execute(select(q).where(q.c.assignment_id==assignment['id'])).mappings().first()
    if not proof or proof['origin']!='PUBLIC' or assignment['placement_id']!=placement['id']:
        raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
    kind=payload['kind'];terms_id=None
    if kind=='NOMINATED':
        if payload['evidence_id']!=assignment['id']:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=proof['created_at']
    elif kind=='ACCEPTED':
        consent=get_row(conn,'placement_consents',payload['evidence_id'])
        if (consent['side']!='MENTOR' or consent['assignment_id']!=assignment['id'] or
            consent['placement_id']!=placement['id'] or consent['actor_id']!=proof['mentor_user_id']):
            raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=consent['created_at'];terms_id=consent['terms_id']
    else:
        event=get_row(conn,'placement_admission_events',payload['evidence_id'])
        if event['action']!='MENTOR_REVOKED' or event['assignment_id']!=assignment['id'] or event['placement_id']!=placement['id']:
            raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=event['created_at'];terms_id=event['terms_id']
    candidate=get_row(conn,'candidate_profiles',placement['candidate_id'])
    mentor=get_row(conn,'users',proof['mentor_user_id'])
    return candidate['user_id'],dict(kind=kind,placement_id=placement['id'],assignment_id=assignment['id'],
        mentor_user_id=mentor['id'],mentor_name=mentor['display_name'],terms_id=terms_id,recorded_at=recorded_at.astimezone(timezone.utc),
        scope_at_event=SCOPES[kind],historical=True,
        diary_review_requires_active_placement=True,
        link='/api/v1/placements/'+placement['id']+'/plan')


def apply_notice(conn,event,payload):
    if payload!=run_notice(event):raise ValueError('Mentor notice result mismatch')
    recipient,_=notice_source(conn,payload)
    stamp=now()
    conn.execute(insert(table('notifications')).values(id=str(uuid4()),created_at=stamp,updated_at=stamp,
        user_id=recipient,event_id=event['id'],template_code='PLACEMENT_MENTOR_'+payload['kind'],
        placement_id=payload['placement_id']).on_conflict_do_nothing(index_elements=['user_id','event_id','template_code']))


class NotificationService:
    def own(self,actor,*,limit=50,after=None,unread_only=True):
        with transaction() as conn:
            account_authority(conn,actor)
            n,e=table('notifications'),table('outbox_events')
            query=select(n.c.id,n.c.created_at,n.c.template_code,n.c.placement_id,n.c.read_at,
                n.c.opportunity_id,n.c.application_id,n.c.ticket_id,
                e.c.id.label('_notice_event_id'),e.c.payload.label('_notice_payload'),
                e.c.event_type.label('_notice_type'),e.c.schema_version.label('_notice_version'))
            query=query.outerjoin(e,e.c.id==n.c.event_id).where(n.c.user_id==actor.user_id)
            all_owned=query
            if unread_only:query=query.where(n.c.read_at.is_(None))
            result=page(conn,query,n.c.id,n.c.created_at,limit=limit,after=after,cursor_query=all_owned)
            for row in result['items']:
                for field in ('created_at','read_at'):
                    if row[field] is not None:row[field]=row[field].astimezone(timezone.utc)
                row['is_read'] = row['read_at'] is not None
                for uuid_field in ('id', 'placement_id', 'opportunity_id', 'application_id', 'ticket_id'):
                    if row.get(uuid_field) is not None:
                        row[uuid_field] = str(row[uuid_field])
                event_id = row.pop('_notice_event_id')
                event_payload = row.pop('_notice_payload')
                event_type = row.pop('_notice_type')
                event_version = row.pop('_notice_version')
                row['notice']=None
                if not event_id or not event_type:
                    continue
                event=dict(id=event_id,payload=event_payload,
                           event_type=event_type,schema_version=event_version)
                try:
                    if event['event_type']==EVENT_TYPE:
                        parse,source,prefix=run_notice,notice_source,'PLACEMENT_MENTOR_'
                    else:
                        from app.services import academic_notices,supervision_notices
                        local={academic_notices.EVENT_TYPE:(academic_notices.run_notice,academic_notices.notice_source,'PLACEMENT_ACADEMIC_'),
                            supervision_notices.EVENT_TYPE:(supervision_notices.run_notice,supervision_notices.notice_source,'SUPERVISION_COORDINATOR_')}
                        if event['event_type'] not in local:continue
                        parse,source,prefix=local[event['event_type']]
                    payload=parse(event)
                    recipient,details=source(conn,payload)
                    if recipient==actor.user_id and payload['placement_id']==row['placement_id'] and row['template_code']==prefix+payload['kind']:
                        row['notice']=details
                except (ValueError,KeyError,TypeError,PlacementScopeError):
                    # Unknown/corrupt legacy content never exposes an arbitrary event payload.
                    continue
            return result

    def read(self,actor,notification_id):
        with transaction() as conn:
            n=table('notifications')
            row=conn.execute(select(n).where(n.c.id==notification_id,n.c.user_id==actor.user_id)
                             .with_for_update()).mappings().first()
            if not row:raise PlacementScopeError('NOTIFICATION_NOT_FOUND',status_code=404)
            account_authority(conn,actor)
            stamp=row['read_at']
            if stamp is None:
                stamp=now()
                conn.execute(n.update().where(n.c.id==notification_id).values(read_at=stamp,updated_at=stamp))
                AppendOnlyAuditStore().append_audit_event(actor_id=actor.user_id,action='NOTIFICATION_READ',
                    entity_type='notification',entity_id=notification_id)
            return {'id':notification_id,'read_at':stamp.astimezone(timezone.utc)}


notification_service=NotificationService()
