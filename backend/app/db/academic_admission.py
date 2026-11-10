"""Typed academic admission evidence; Alembic owns DDL and validation."""
from sqlalchemy import Column, Table


def register_tables(metadata,types):
    actor={'actor_id':'uuid','session_id':'uuid','auth_version':'integer','coordinator_grant_id':'uuid',
           'idempotency_key':'text','request_fingerprint':'text','receipt':'jsonb'}
    definitions={
        'student_academic_requests':{'id':'uuid','created_at':'timestamptz','placement_id':'uuid','revision':'integer',
            'institution_id':'uuid','enrollment_id':'uuid','terms_id':'uuid','actor_id':'uuid','session_id':'uuid',
            'auth_version':'integer','idempotency_key':'text','request_fingerprint':'text','receipt':'jsonb'},
        'supervision_origins':{'supervision_id':'uuid','created_at':'timestamptz','origin':'text',
            'initial_snapshot':'jsonb',**actor},
        'placement_academic_bindings':{'placement_id':'uuid','created_at':'timestamptz','origin':'text',
            'institution_id':'uuid','enrollment_id':'uuid','supervision_id':'uuid','terms_id':'uuid',
            'initial_snapshot':'jsonb','scope_snapshot':'jsonb',**actor},
        'academic_assignment_proofs':{'assignment_id':'uuid','created_at':'timestamptz','origin':'text',
            'placement_id':'uuid','teacher_user_id':'uuid','teacher_grant_id':'uuid','teacher_appointment_id':'uuid',
            'initial_snapshot':'jsonb',**actor},
        'academic_assignment_consents':{'id':'uuid','created_at':'timestamptz','placement_id':'uuid','assignment_id':'uuid',
            'terms_id':'uuid','actor_id':'uuid','session_id':'uuid','auth_version':'integer',
            'teacher_grant_id':'uuid','teacher_appointment_id':'uuid','idempotency_key':'text','request_fingerprint':'text','receipt':'jsonb'},
        'academic_assignment_events':{'id':'uuid','created_at':'timestamptz','placement_id':'uuid','assignment_id':'uuid',
            'action':'text',**actor}}
    keys={'student_academic_requests':'id','supervision_origins':'supervision_id','placement_academic_bindings':'placement_id',
          'academic_assignment_proofs':'assignment_id','academic_assignment_consents':'id','academic_assignment_events':'id'}
    nullable={name:set(actor) for name in ('supervision_origins','placement_academic_bindings','academic_assignment_proofs')}
    nullable['placement_academic_bindings'].update(('supervision_id','terms_id'))
    nullable['academic_assignment_proofs'].update(('teacher_grant_id','teacher_appointment_id'))
    for name,fields in definitions.items():
        Table(name,metadata,*[Column(field,types[kind],primary_key=field==keys[name],nullable=field in nullable.get(name,set()))
                             for field,kind in fields.items()])
    proof_fields={'review_id':'uuid','created_at':'timestamptz','origin':'text','initial_snapshot':'jsonb',
        'terms_id':'uuid','actor_id':'uuid','session_id':'uuid','auth_version':'integer','teacher_grant_id':'uuid',
        'teacher_appointment_id':'uuid','assignment_proof_snapshot':'jsonb','revision_snapshot':'jsonb',
        'idempotency_key':'text','request_fingerprint':'text','receipt':'jsonb'}
    Table('academic_review_proofs',metadata,*[Column(field,types[kind],primary_key=field=='review_id',
        nullable=field not in ('review_id','created_at','origin','initial_snapshot')) for field,kind in proof_fields.items()])
