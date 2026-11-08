"""Explicit organization invitation role and contact binding."""
from alembic import op

revision = '0005_org_invitations'
down_revision = '0004_org_onboarding'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE flexbridge.org_invitations
      ADD COLUMN role_id uuid REFERENCES flexbridge.role_catalog(id),
      ADD COLUMN channel text CHECK (channel IN ('PHONE','EMAIL')),
      ADD COLUMN target_user_id uuid REFERENCES flexbridge.users(id),
      ADD COLUMN target_contact_id uuid REFERENCES flexbridge.user_contacts(id);
    -- Legacy tokens have no explicit role/contact contract. Preserve history, invalidate pending authority.
    UPDATE flexbridge.org_invitations SET revoked_at=now(),updated_at=now()
      WHERE accepted_at IS NULL AND revoked_at IS NULL;
    ALTER TABLE flexbridge.org_invitations ADD CONSTRAINT chk_pending_invitation_contract
      CHECK (accepted_at IS NOT NULL OR revoked_at IS NOT NULL OR (role_id IS NOT NULL AND channel IS NOT NULL));
    ALTER TABLE flexbridge.org_invitations ADD CONSTRAINT fk_invitation_inviter_scope
      FOREIGN KEY(inviter_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id);
    CREATE UNIQUE INDEX uq_org_invitation_token ON flexbridge.org_invitations(token_digest);
    CREATE INDEX ix_org_invitation_contact ON flexbridge.org_invitations(organization_id,contact_digest);
    """)


def downgrade():
    raise RuntimeError('Invitation authority/history requires a reviewed forward recovery migration')
