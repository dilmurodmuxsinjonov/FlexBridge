"""Transactional academic viewer notices derived from exact immutable local evidence."""
from datetime import timezone
from uuid import UUID,uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.storage import table,enqueue,now
from app.services.placements import get_row,PlacementScopeError


EVENT_TYPE='PLACEMENT_ACADEMIC_NOTICE'
SCOPES={'NOMINATED':['PLAN'],'ACCEPTED':['PLAN','ACADEMIC_DIARY_REVIEW'],'REVOKED':[]}


def queue_notice(conn,placement_id,assignment_id,kind,evidence_id):
    if kind not in SCOPES:raise ValueError('Unsupported academic notice')
    enqueue(conn,EVENT_TYPE,placement_id,dict(placement_id=placement_id,assignment_id=assignment_id,kind=kind,evidence_id=evidence_id),
        'academic-notice:'+kind+':'+evidence_id)


def run_notice(event):
    payload=event['payload']
    if event['event_type']!=EVENT_TYPE or event['schema_version']!=1 or payload['kind'] not in SCOPES:
        raise ValueError('Invalid academic notice envelope')
    return {**{name:str(UUID(str(payload[name]))) for name in ('placement_id','assignment_id','evidence_id')},'kind':payload['kind']}


def notice_source(conn,payload):
    placement=get_row(conn,'placements',payload['placement_id'])
    assignment=get_row(conn,'academic_assignments',payload['assignment_id'])
    if assignment['placement_id']!=placement['id']:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
    kind=payload['kind'];terms_id=None
    q=table('academic_assignment_proofs')
    proof=conn.execute(select(q).where(q.c.assignment_id==assignment['id'])).mappings().first()
    if kind=='NOMINATED':
        # Imported history is not a new nomination intent.
        if not proof or proof['origin']!='PUBLIC':raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        if payload['evidence_id']!=assignment['id']:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=proof['created_at'];terms_id=proof['receipt']['terms_id']
        teacher_id=proof['teacher_user_id']
    elif kind=='ACCEPTED':
        # A retained assignment can acquire a new personal exact-plan consent.
        # Deliver that committed action, never a notice inferred from old accepted_at.
        if not proof:raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        consent=get_row(conn,'academic_assignment_consents',payload['evidence_id'])
        if (consent['assignment_id']!=assignment['id'] or consent['placement_id']!=placement['id']
            or consent['actor_id']!=proof['teacher_user_id'] or consent['teacher_grant_id']!=proof['teacher_grant_id']
            or consent['teacher_appointment_id']!=proof['teacher_appointment_id']):
            raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=consent['created_at'];terms_id=consent['terms_id'];teacher_id=proof['teacher_user_id']
    else:
        event=get_row(conn,'academic_assignment_events',payload['evidence_id'])
        if event['action']!='REVOKE' or event['assignment_id']!=assignment['id'] or event['placement_id']!=placement['id']:
            raise PlacementScopeError('NOTICE_SOURCE_MISMATCH')
        recorded_at=event['created_at']
        # Cleanup of invalid/imported nominations still has canonical immutable identity.
        teacher_id=get_row(conn,'institution_memberships',assignment['teacher_membership_id'])['user_id']
    teacher=get_row(conn,'users',teacher_id)
    recipient=get_row(conn,'candidate_profiles',placement['candidate_id'])['user_id']
    return recipient,dict(kind=kind,assignment_kind='TEACHER',placement_id=placement['id'],assignment_id=assignment['id'],
        institution_id=assignment['institution_id'],teacher_user_id=teacher_id,teacher_name=teacher['display_name'],
        terms_id=terms_id,recorded_at=recorded_at.astimezone(timezone.utc),scope_at_event=SCOPES[kind],historical=True,
        diary_review_requires_active_placement=True,current_authority_required=True,link='/api/v1/placements/'+placement['id']+'/plan')


def apply_notice(conn,event,payload):
    if payload!=run_notice(event):raise ValueError('Academic notice result mismatch')
    recipient,_=notice_source(conn,payload);stamp=now()
    conn.execute(insert(table('notifications')).values(id=str(uuid4()),created_at=stamp,updated_at=stamp,user_id=recipient,
        event_id=event['id'],template_code='PLACEMENT_ACADEMIC_'+payload['kind'],placement_id=payload['placement_id'])
        .on_conflict_do_nothing(index_elements=['user_id','event_id','template_code']))
