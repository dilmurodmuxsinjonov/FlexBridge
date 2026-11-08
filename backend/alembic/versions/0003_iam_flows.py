"""Purpose-bound IAM continuations, OTP delivery and shared rate limits."""
from alembic import op

revision = '0003_iam_flows'
down_revision = '0002_security_runtime'
branch_labels = depends_on = None

def upgrade():
    op.execute("""
    ALTER TABLE flexbridge.users ADD COLUMN auth_version integer NOT NULL DEFAULT 1 CHECK (auth_version > 0);
    ALTER TABLE flexbridge.sessions ADD COLUMN auth_version integer NOT NULL DEFAULT 1 CHECK (auth_version > 0);
    -- Older releases could leave a pre-MFA PASSWORD session active after enrollment.
    UPDATE flexbridge.sessions s SET revoked_at=now(),updated_at=now()
      WHERE s.revoked_at IS NULL AND s.assurance <> 'MFA' AND EXISTS
        (SELECT 1 FROM flexbridge.mfa_credentials m WHERE m.user_id=s.user_id
         AND m.kind IN ('TOTP','PASSKEY') AND m.verified_at IS NOT NULL AND m.revoked_at IS NULL);
    ALTER TABLE flexbridge.auth_challenges ADD COLUMN destination_encrypted text;
    ALTER TABLE flexbridge.auth_challenges ADD COLUMN delivery_encrypted text;
    ALTER TABLE flexbridge.auth_challenges ADD COLUMN delivery_status text NOT NULL DEFAULT 'PENDING'
      CHECK (delivery_status IN ('PENDING','SENT','EXPIRED','SUPERSEDED','CONSUMED'));
    ALTER TABLE flexbridge.auth_challenges ADD COLUMN sent_at timestamptz;
    CREATE INDEX ix_auth_challenge_destination ON flexbridge.auth_challenges(destination_digest,purpose,created_at);
    CREATE INDEX ix_auth_challenge_expiry ON flexbridge.auth_challenges(expires_at);
    CREATE INDEX ix_auth_challenge_created ON flexbridge.auth_challenges(created_at);
    CREATE TABLE flexbridge.auth_continuations (
      digest text PRIMARY KEY, kind text NOT NULL,
      user_id uuid REFERENCES flexbridge.users(id), challenge_id uuid REFERENCES flexbridge.auth_challenges(id),
      payload_encrypted text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz NOT NULL, consumed_at timestamptz, attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5));
    CREATE INDEX ix_auth_continuation_expiry ON flexbridge.auth_continuations(expires_at);
    CREATE TABLE flexbridge.auth_rate_limits (
      bucket_key text PRIMARY KEY, window_started_at timestamptz NOT NULL, count integer NOT NULL CHECK (count > 0));
    CREATE INDEX ix_auth_rate_expiry ON flexbridge.auth_rate_limits(window_started_at);
    """)

def downgrade():
    raise RuntimeError('IAM state requires a reviewed forward recovery migration')
