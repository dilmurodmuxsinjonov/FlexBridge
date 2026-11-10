"""Typed access to admission evidence; migrations own the actual constraints."""
from sqlalchemy import Column, Table


def register_tables(metadata, types):
    definitions = {
        'placement_intakes': {
            'placement_id': 'uuid', 'created_at': 'timestamptz', 'origin': 'text',
            'offer_id': 'uuid', 'attempt_id': 'uuid', 'revision_id': 'uuid',
            'academic_required': 'boolean', 'actor_id': 'uuid', 'session_id': 'uuid',
            'auth_version': 'integer', 'host_grant_id': 'uuid',
            'idempotency_key': 'text', 'request_fingerprint': 'text', 'receipt': 'jsonb',
            'initial_snapshot': 'jsonb', 'source_snapshot': 'jsonb'},
        'mentor_assignment_proofs': {
            'assignment_id': 'uuid', 'created_at': 'timestamptz', 'origin': 'text',
            'placement_id': 'uuid', 'mentor_user_id': 'uuid', 'mentor_grant_id': 'uuid',
            'actor_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
            'host_grant_id': 'uuid', 'initial_snapshot': 'jsonb',
            'idempotency_key': 'text', 'request_fingerprint': 'text', 'receipt': 'jsonb'},
        'placement_consents': {
            'id': 'uuid', 'created_at': 'timestamptz', 'placement_id': 'uuid', 'terms_id': 'uuid',
            'side': 'text', 'actor_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
            'org_grant_id': 'uuid', 'assignment_id': 'uuid', 'idempotency_key': 'text',
            'request_fingerprint': 'text', 'receipt': 'jsonb'},
        'placement_admission_events': {
            'id': 'uuid', 'created_at': 'timestamptz', 'placement_id': 'uuid', 'terms_id': 'uuid',
            'action': 'text', 'actor_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
            'org_grant_id': 'uuid', 'assignment_id': 'uuid', 'idempotency_key': 'text',
            'request_fingerprint': 'text', 'receipt': 'jsonb'}}
    optional = {
        'placement_intakes': {'actor_id', 'session_id', 'auth_version', 'host_grant_id', 'idempotency_key', 'request_fingerprint', 'receipt'},
        'mentor_assignment_proofs': {'mentor_grant_id', 'actor_id', 'session_id', 'auth_version', 'host_grant_id', 'idempotency_key', 'request_fingerprint', 'receipt'},
        'placement_consents': {'org_grant_id', 'assignment_id'},
        'placement_admission_events': {'assignment_id'}}
    for name, fields in definitions.items():
        key = 'placement_id' if name == 'placement_intakes' else (
            'assignment_id' if name == 'mentor_assignment_proofs' else 'id')
        Table(name, metadata, *[Column(field, types[kind], primary_key=field == key,
              nullable=field in optional[name]) for field, kind in fields.items()])
