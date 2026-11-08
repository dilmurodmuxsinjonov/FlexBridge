"""Normalized organization identity and immutable verification submissions."""
from alembic import op

revision = '0004_org_onboarding'
down_revision = '0003_iam_flows'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    -- Conflicting legacy identifiers fail this migration; no organizations are merged/deleted.
    CREATE UNIQUE INDEX uq_org_normalized_tax_id ON flexbridge.organizations
      ((regexp_replace(tax_id, '[[:space:]-]', '', 'g')));
    ALTER TABLE flexbridge.verification_cases ADD CONSTRAINT uq_case_org UNIQUE (id,organization_id);
    CREATE TABLE flexbridge.org_verification_submissions (
      case_id uuid NOT NULL, revision integer NOT NULL CHECK (revision > 0),
      organization_id uuid NOT NULL, requester_membership_id uuid,
      proposed_fields jsonb NOT NULL CHECK (jsonb_typeof(proposed_fields) = 'object'),
      created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (case_id,revision),
      FOREIGN KEY (case_id,organization_id) REFERENCES flexbridge.verification_cases(id,organization_id),
      FOREIGN KEY (requester_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id));
    CREATE FUNCTION flexbridge.immutable_org_submission() RETURNS trigger
      LANGUAGE plpgsql SET search_path = pg_catalog,flexbridge AS $$
      BEGIN RAISE EXCEPTION 'Organization verification submissions are immutable' USING ERRCODE='23514'; END $$;
    CREATE TRIGGER org_submission_immutable BEFORE UPDATE OR DELETE ON flexbridge.org_verification_submissions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.immutable_org_submission();
    INSERT INTO flexbridge.role_catalog(id,code,scope_kind,description)
      SELECT gen_random_uuid(),code,'ORG','Organization-scoped ' || code
      FROM unnest(ARRAY['OWNER','HR','HOST_COORDINATOR','MENTOR','BILLING']) AS role(code)
      ON CONFLICT(code) DO NOTHING;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM flexbridge.role_catalog WHERE code IN
        ('OWNER','HR','HOST_COORDINATOR','MENTOR','BILLING') AND scope_kind <> 'ORG') THEN
        RAISE EXCEPTION 'Organization role scope conflict; review role catalog before upgrading';
      END IF;
    END $$;
    """)


def downgrade():
    raise RuntimeError('Organization verification history needs a reviewed forward recovery migration')
