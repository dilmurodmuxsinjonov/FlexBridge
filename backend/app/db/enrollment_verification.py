"""Typed, append-only provenance for the enrollment lifecycle."""
from sqlalchemy import Column, Table


def register_tables(metadata, types):
    definitions = {
        'enrollment_origins': {
            'enrollment_id': 'uuid', 'created_at': 'timestamptz', 'origin': 'text',
            'candidate_id': 'uuid', 'institution_id': 'uuid', 'actor_user_id': 'uuid',
            'case_id': 'uuid', 'initial_snapshot': 'jsonb', 'idempotency_key': 'text',
            'request_fingerprint': 'text'},
        'enrollment_submissions': {
            'case_id': 'uuid', 'revision': 'integer', 'created_at': 'timestamptz',
            'submitted_by_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
            'program': 'text', 'start_date': 'date', 'end_date': 'date',
            'student_ref_digest': 'text', 'evidence_note': 'text', 'file_ids': 'jsonb',
            'file_snapshots': 'jsonb'},
        'enrollment_events': {
            'id': 'uuid', 'created_at': 'timestamptz', 'enrollment_id': 'uuid',
            'case_id': 'uuid', 'revision': 'integer', 'action': 'text',
            'actor_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
            'platform_grant_id': 'uuid', 'reason': 'text', 'idempotency_key': 'text',
            'request_fingerprint': 'text', 'receipt': 'jsonb'}}
    optional = {
        'enrollment_origins': {'case_id', 'idempotency_key', 'request_fingerprint'},
        'enrollment_submissions': {'end_date', 'student_ref_digest'},
        'enrollment_events': {'case_id', 'revision', 'platform_grant_id', 'idempotency_key', 'request_fingerprint'}}
    for name, fields in definitions.items():
        keys = {'enrollment_id'} if name.endswith('origins') else (
            {'case_id', 'revision'} if name.endswith('submissions') else {'id'})
        Table(name, metadata, *[
            Column(key, types[kind], primary_key=key in keys, nullable=key in optional[name])
            for key, kind in fields.items()])
