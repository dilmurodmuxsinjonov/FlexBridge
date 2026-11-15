"""Typed candidate portal extension tables; Alembic 0021 owns DDL and validation."""
from sqlalchemy import Column, Table

PORTFOLIO_FIELDS = {
    'id': 'uuid',
    'created_at': 'timestamptz',
    'updated_at': 'timestamptz',
    'candidate_id': 'uuid',
    'title': 'text',
    'description': 'text',
    'project_url': 'text',
    'github_url': 'text',
    'skills': 'jsonb',
    'start_date': 'date',
    'end_date': 'date',
    'file_id': 'uuid',
}
PORTFOLIO_REQUIRED = {
    'id',
    'created_at',
    'updated_at',
    'candidate_id',
    'title',
    'description',
    'skills',
}

CERTIFICATE_FIELDS = {
    'id': 'uuid',
    'created_at': 'timestamptz',
    'updated_at': 'timestamptz',
    'candidate_id': 'uuid',
    'title': 'text',
    'issuer': 'text',
    'issue_date': 'date',
    'expiry_date': 'date',
    'credential_id': 'text',
    'credential_url': 'text',
    'file_id': 'uuid',
    'verification_case_id': 'uuid',
}
CERTIFICATE_REQUIRED = {
    'id',
    'created_at',
    'updated_at',
    'candidate_id',
    'title',
    'issuer',
    'issue_date',
}

RESUME_EXPORT_FIELDS = {
    'id': 'uuid',
    'created_at': 'timestamptz',
    'candidate_id': 'uuid',
    'actor_id': 'uuid',
    'file_id': 'uuid',
    'export_format': 'text',
    'summary_snapshot': 'jsonb',
    'idempotency_key': 'text',
    'request_fingerprint': 'text',
    'receipt': 'jsonb',
    'expires_at': 'timestamptz',
}
RESUME_EXPORT_REQUIRED = set(RESUME_EXPORT_FIELDS.keys())


def register_tables(metadata, types):
    if 'flexbridge.candidate_portfolios' not in metadata.tables:
        Table(
            'candidate_portfolios',
            metadata,
            *[
                Column(
                    name,
                    types[kind],
                    primary_key=name == 'id',
                    nullable=name not in PORTFOLIO_REQUIRED,
                )
                for name, kind in PORTFOLIO_FIELDS.items()
            ],
            schema='flexbridge',
        )

    if 'flexbridge.candidate_certificates' not in metadata.tables:
        Table(
            'candidate_certificates',
            metadata,
            *[
                Column(
                    name,
                    types[kind],
                    primary_key=name == 'id',
                    nullable=name not in CERTIFICATE_REQUIRED,
                )
                for name, kind in CERTIFICATE_FIELDS.items()
            ],
            schema='flexbridge',
        )

    if 'flexbridge.candidate_resume_exports' not in metadata.tables:
        Table(
            'candidate_resume_exports',
            metadata,
            *[
                Column(
                    name,
                    types[kind],
                    primary_key=name == 'id',
                    nullable=name not in RESUME_EXPORT_REQUIRED,
                )
                for name, kind in RESUME_EXPORT_FIELDS.items()
            ],
            schema='flexbridge',
        )

    return (
        metadata.tables['flexbridge.candidate_portfolios'],
        metadata.tables['flexbridge.candidate_certificates'],
        metadata.tables['flexbridge.candidate_resume_exports'],
    )
