"""Local historical coordinator notices from immutable responsibility/binding proof."""
from datetime import timezone
from uuid import UUID,uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.storage import table,enqueue,now
from app.services.placements import get_row,PlacementScopeError


EVENT_TYPE='SUPERVISION_COORDINATOR_NOTICE'


def queue_notice(conn,supervision_id,placement_id=None):
    kind='PLACEMENT_BOUND' if placement_id else 'SUPERVISION_CREATED'
    enqueue(conn,EVENT_TYPE,placement_id or supervision_id,dict(supervision_id=supervision_id,placement_id=placement_id,kind=kind),
        'coordinator-notice:'+kind+':'+(placement_id or supervision_id))


def run_notice(event):
    payload=event['payload'];kind=payload['kind']
    if event['event_type']!=EVENT_TYPE or event['schema_version']!=1 or kind not in ('PLACEMENT_BOUND','SUPERVISION_CREATED'):
        raise ValueError('Invalid coordinator notice envelope')
    placement=payload.get('placement_id')
    if (kind=='PLACEMENT_BOUND')!=(placement is not None):raise ValueError('Invalid coordinator notice scope')
    return dict(kind=kind,supervision_id=str(UUID(str(payload['supervision_id']))),placement_id=str(UUID(str(placement))) if placement else None)


def notice_source(conn,payload):
    if payload['kind']=='SUPERVISION_CREATED':
        t=table('supervision_origins')
        proof=conn.execute(select(t).where(t.c.supervision_id==payload['supervision_id'],t.c.origin=='PUBLIC')).mappings().first()
        if not proof:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        original=proof['initial_snapshot']
        enrollment_id=original['enrollment_id'];institution_id=original['institution_id'];purpose=original['purpose']
        coordinator_id=proof['actor_id'];recorded_at=proof['created_at']
        if original['id']!=payload['supervision_id']:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
    else:
        t=table('placement_academic_bindings')
        proof=conn.execute(select(t).where(t.c.placement_id==payload['placement_id'],t.c.origin=='PUBLIC')).mappings().first()
        if not proof or proof['supervision_id']!=payload['supervision_id']:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        enrollment_id=proof['enrollment_id'];institution_id=proof['institution_id'];purpose=proof['scope_snapshot']['purpose']
        coordinator_id=proof['actor_id'];recorded_at=proof['created_at']
    enrollment=get_row(conn,'enrollments',enrollment_id)
    candidate=get_row(conn,'candidate_profiles',enrollment['candidate_id'])
    if enrollment['institution_id']!=institution_id:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
    if payload['placement_id'] and get_row(conn,'placements',payload['placement_id'])['candidate_id']!=candidate['id']:
        raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
    coordinator=get_row(conn,'users',coordinator_id)
    return candidate['user_id'],dict(kind=payload['kind'],supervision_id=payload['supervision_id'],placement_id=payload['placement_id'],
        institution_id=institution_id,enrollment_id=enrollment_id,purpose=purpose,coordinator_user_id=coordinator_id,
        coordinator_name=coordinator['display_name'],recorded_at=recorded_at.astimezone(timezone.utc),historical=True,
        diary_read_requires_active_bound_current_scope=True,link='/api/v1/me/enrollments/'+enrollment_id)


def apply_notice(conn,event,payload):
    if payload!=run_notice(event):raise ValueError('Coordinator notice result mismatch')
    recipient,_=notice_source(conn,payload);stamp=now()
    conn.execute(insert(table('notifications')).values(id=str(uuid4()),created_at=stamp,updated_at=stamp,user_id=recipient,
        event_id=event['id'],template_code='SUPERVISION_COORDINATOR_'+payload['kind'],placement_id=payload['placement_id'])
        .on_conflict_do_nothing(index_elements=['user_id','event_id','template_code']))
