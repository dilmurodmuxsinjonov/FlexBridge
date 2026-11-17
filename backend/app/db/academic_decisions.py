"""Typed placement-wide academic decision proof table; Alembic 0018 owns DDL and validation."""
from sqlalchemy import Column, Table

PROOF_FIELDS = {
    'decision_id': 'uuid',
    'created_at': 'timestamptz',
    'origin': 'text',
    'initial_snapshot': 'jsonb',
    'placement_id': 'uuid',
    'assignment_id': 'uuid',
    'terms_id': 'uuid',
    'terms_version': 'integer',
    'actor_id': 'uuid',
    'session_id': 'uuid',
    'auth_version': 'integer',
    'teacher_grant_id': 'uuid',
    'teacher_appointment_id': 'uuid',
    'teacher_consent_id': 'uuid',
    'consent_snapshot': 'jsonb',
    'assignment_proof_snapshot': 'jsonb',
    'basis_snapshot': 'jsonb',
    'basis_digest': 'text',
    'audit_event_id': 'uuid',
    'idempotency_key': 'text',
    'request_fingerprint': 'text',
    'receipt': 'jsonb',
}
REQUIRED_FIELDS = {'decision_id', 'created_at', 'origin', 'initial_snapshot'}


def register_tables(metadata, types):
    if 'flexbridge.academic_decision_proofs' in metadata.tables:
        return metadata.tables['flexbridge.academic_decision_proofs']
    return Table(
        'academic_decision_proofs',
        metadata,
        *[
            Column(
                name,
                types[kind],
                primary_key=name == 'decision_id',
                nullable=name not in REQUIRED_FIELDS,
            )
            for name, kind in PROOF_FIELDS.items()
        ],
    )
