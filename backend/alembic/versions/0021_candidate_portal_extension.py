"""Candidate portal extension: portfolio showcase, certificates with clean file verification, and resume PDF export (API-026 / CAP-002)."""
from alembic import op

revision = '0021_candidate_portal_extension'
down_revision = '0020_placement_exports'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.candidate_portfolios (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      candidate_id uuid NOT NULL REFERENCES flexbridge.candidate_profiles(id) ON DELETE CASCADE,
      title text NOT NULL,
      description text NOT NULL,
      project_url text,
      github_url text,
      skills jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(skills) = 'array'),
      start_date date,
      end_date date,
      file_id uuid REFERENCES flexbridge.files(id),
      CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
    );

    CREATE INDEX idx_candidate_portfolios_candidate
      ON flexbridge.candidate_portfolios(candidate_id, created_at DESC);

    CREATE TABLE flexbridge.candidate_certificates (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      candidate_id uuid NOT NULL REFERENCES flexbridge.candidate_profiles(id) ON DELETE CASCADE,
      title text NOT NULL,
      issuer text NOT NULL,
      issue_date date NOT NULL,
      expiry_date date,
      credential_id text,
      credential_url text,
      file_id uuid REFERENCES flexbridge.files(id),
      verification_case_id uuid REFERENCES flexbridge.verification_cases(id),
      CHECK (expiry_date IS NULL OR expiry_date >= issue_date)
    );

    CREATE INDEX idx_candidate_certificates_candidate
      ON flexbridge.candidate_certificates(candidate_id, issue_date DESC);

    CREATE TABLE flexbridge.candidate_resume_exports (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      candidate_id uuid NOT NULL REFERENCES flexbridge.candidate_profiles(id),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      file_id uuid NOT NULL REFERENCES flexbridge.files(id),
      export_format text NOT NULL CHECK (export_format IN ('PDF', 'JSON')),
      summary_snapshot jsonb NOT NULL CHECK (jsonb_typeof(summary_snapshot) = 'object'),
      idempotency_key text NOT NULL,
      request_fingerprint text NOT NULL,
      receipt jsonb NOT NULL CHECK (jsonb_typeof(receipt) = 'object'),
      expires_at timestamptz NOT NULL
    );

    CREATE INDEX idx_candidate_resumes_candidate
      ON flexbridge.candidate_resume_exports(candidate_id, created_at DESC);

    CREATE UNIQUE INDEX uq_candidate_resumes_idempotency
      ON flexbridge.candidate_resume_exports(candidate_id, idempotency_key);
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS flexbridge.candidate_resume_exports CASCADE;
    DROP TABLE IF EXISTS flexbridge.candidate_certificates CASCADE;
    DROP TABLE IF EXISTS flexbridge.candidate_portfolios CASCADE;
    """)
