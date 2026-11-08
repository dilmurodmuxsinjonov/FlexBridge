"""Independent additional-owner proposals and append-only target consent/history."""
from alembic import op

revision='0008_owner_additions'
down_revision='0007_moderation_appeals'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    -- Preserve revoked grants. A future grant gets a new row and proof, not reactivation.
    ALTER TABLE flexbridge.org_role_grants DROP CONSTRAINT org_role_grants_membership_id_role_id_key;
    CREATE UNIQUE INDEX uq_org_active_role ON flexbridge.org_role_grants(membership_id,role_id) WHERE revoked_at IS NULL;
    CREATE UNIQUE INDEX uq_ownership_case_event ON flexbridge.org_ownership_events(verification_case_id);
    CREATE TRIGGER immutable_org_ownership_events BEFORE UPDATE OR DELETE ON flexbridge.org_ownership_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_verification_evidence BEFORE UPDATE OR DELETE ON flexbridge.verification_evidence
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TABLE flexbridge.owner_addition_requests (
      case_id uuid PRIMARY KEY REFERENCES flexbridge.verification_cases(id),
      created_at timestamptz NOT NULL,
      organization_id uuid NOT NULL REFERENCES flexbridge.organizations(id),
      requester_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      requester_membership_id uuid NOT NULL,
      requester_auth_version integer NOT NULL,
      requester_session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      target_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      target_membership_id uuid NOT NULL,
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL,
      CHECK(requester_user_id<>target_user_id AND requester_membership_id<>target_membership_id),
      FOREIGN KEY(requester_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id),
      FOREIGN KEY(target_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id),
      UNIQUE(requester_user_id,idempotency_key));
    CREATE INDEX ix_owner_add_target ON flexbridge.owner_addition_requests(target_user_id,case_id);
    CREATE TABLE flexbridge.owner_addition_consents (
      id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES flexbridge.owner_addition_requests(case_id),
      created_at timestamptz NOT NULL, revision integer NOT NULL CHECK(revision>0),
      event_no integer NOT NULL CHECK(event_no>0),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id), auth_version integer NOT NULL,
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      decision text NOT NULL CHECK(decision IN ('ACCEPT','DECLINE')),
      contact_id uuid REFERENCES flexbridge.user_contacts(id), contact_digest text,
      contact_verified_at timestamptz, expires_at timestamptz,
      CHECK((decision='ACCEPT' AND contact_id IS NOT NULL AND contact_digest IS NOT NULL
        AND contact_verified_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at>created_at
        AND expires_at<=created_at+interval '24 hours')
        OR (decision='DECLINE' AND contact_id IS NULL AND contact_digest IS NULL
        AND contact_verified_at IS NULL AND expires_at IS NULL)),
      UNIQUE(case_id,event_no));
    CREATE TRIGGER immutable_owner_addition_requests BEFORE UPDATE OR DELETE ON flexbridge.owner_addition_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_owner_addition_consents BEFORE UPDATE OR DELETE ON flexbridge.owner_addition_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE FUNCTION flexbridge.guard_owner_proposal() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN org_memberships r ON r.id=NEW.requester_membership_id
        JOIN org_memberships t ON t.id=NEW.target_membership_id JOIN users u ON u.id=r.user_id
        JOIN users target ON target.id=t.user_id JOIN sessions session ON session.id=NEW.requester_session_id
        WHERE c.id=NEW.case_id AND c.kind='ORG_OWNER_ADDITION' AND c.organization_id=NEW.organization_id
          AND c.requester_id=NEW.requester_user_id AND r.user_id=NEW.requester_user_id
          AND t.user_id=NEW.target_user_id AND r.organization_id=NEW.organization_id AND t.organization_id=NEW.organization_id
          AND r.status='ACTIVE' AND r.revoked_at IS NULL AND t.status='ACTIVE' AND t.revoked_at IS NULL
          AND u.status='ACTIVE' AND u.auth_version=NEW.requester_auth_version AND target.status='ACTIVE'
          AND session.user_id=u.id AND session.auth_version=u.auth_version AND session.assurance='MFA'
          AND session.revoked_at IS NULL AND session.expires_at>clock_timestamp()
          AND EXISTS(SELECT 1 FROM org_role_grants g JOIN role_catalog rc ON rc.id=g.role_id
            WHERE g.membership_id=r.id AND g.revoked_at IS NULL AND rc.code='OWNER' AND rc.scope_kind='ORG')
          AND EXISTS(SELECT 1 FROM org_role_grants g JOIN role_catalog rc ON rc.id=g.role_id
            WHERE g.membership_id=t.id AND g.revoked_at IS NULL AND rc.code IN ('HR','HOST_COORDINATOR','MENTOR','BILLING')
              AND rc.scope_kind='ORG')) THEN
        RAISE EXCEPTION 'Owner proposal scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_owner_proposal BEFORE INSERT ON flexbridge.owner_addition_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_owner_proposal();
    CREATE FUNCTION flexbridge.guard_owner_consent() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM owner_addition_requests p JOIN verification_cases c ON c.id=p.case_id
        JOIN users u ON u.id=p.target_user_id WHERE p.case_id=NEW.case_id AND p.target_user_id=NEW.actor_id
          AND c.current_revision=NEW.revision AND (c.status IN ('WAITING_CONSENT','PENDING','IN_REVIEW')
            OR (c.status='NEEDS_INFO' AND NEW.decision='DECLINE'))
          AND u.status='ACTIVE' AND u.auth_version=NEW.auth_version
          AND EXISTS(SELECT 1 FROM sessions s WHERE s.id=NEW.session_id AND s.user_id=u.id
            AND s.auth_version=u.auth_version AND s.assurance='MFA' AND s.revoked_at IS NULL
            AND s.expires_at>clock_timestamp())) THEN
        RAISE EXCEPTION 'Owner consent scope or revision mismatch' USING ERRCODE='23514';
      END IF;
      IF NEW.decision='ACCEPT' AND NOT EXISTS(SELECT 1 FROM user_contacts t WHERE t.id=NEW.contact_id
        AND t.user_id=NEW.actor_id AND t.verified_at=NEW.contact_verified_at AND t.revoked_at IS NULL) THEN
        RAISE EXCEPTION 'Owner consent contact mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_owner_consent BEFORE INSERT ON flexbridge.owner_addition_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_owner_consent();
    CREATE FUNCTION flexbridge.guard_owner_event_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN org_memberships m ON m.id=NEW.new_membership_id
        JOIN organizations o ON o.id=m.organization_id
        JOIN org_role_grants g ON g.membership_id=m.id JOIN role_catalog r ON r.id=g.role_id
        WHERE c.id=NEW.verification_case_id AND c.organization_id=NEW.organization_id AND c.status='APPROVED'
          AND c.assigned_reviewer_id=NEW.approved_by_id AND c.requester_id<>NEW.approved_by_id
          AND m.organization_id=NEW.organization_id AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND o.status='VERIFIED' AND r.code='OWNER' AND r.scope_kind='ORG' AND g.revoked_at IS NULL
          AND g.granted_by_id=NEW.approved_by_id
          AND NOT EXISTS(SELECT 1 FROM org_memberships reviewer WHERE reviewer.organization_id=NEW.organization_id
            AND reviewer.user_id=NEW.approved_by_id)
          AND ((c.kind='ORG_REPRESENTATIVE' AND m.user_id=c.requester_id)
            OR (c.kind='ORG_OWNER_ADDITION' AND EXISTS(SELECT 1 FROM owner_addition_requests p
              JOIN users requester ON requester.id=p.requester_user_id
              JOIN users target ON target.id=p.target_user_id
              JOIN org_memberships previous ON previous.id=p.requester_membership_id
              WHERE p.case_id=c.id AND p.target_membership_id=m.id AND p.requester_user_id=c.requester_id
                AND requester.status='ACTIVE' AND requester.auth_version=p.requester_auth_version
                AND target.status='ACTIVE' AND previous.status='ACTIVE' AND previous.revoked_at IS NULL
                AND EXISTS(SELECT 1 FROM org_role_grants old_grant JOIN role_catalog old_role ON old_role.id=old_grant.role_id
                  WHERE old_grant.membership_id=previous.id AND old_grant.revoked_at IS NULL
                    AND old_role.code='OWNER' AND old_role.scope_kind='ORG')
                AND EXISTS(SELECT 1 FROM owner_addition_consents consent JOIN user_contacts contact ON contact.id=consent.contact_id
                  WHERE consent.case_id=c.id AND consent.revision=c.current_revision AND consent.decision='ACCEPT'
                    AND consent.actor_id=target.id AND consent.auth_version=target.auth_version
                    AND consent.expires_at>clock_timestamp() AND contact.user_id=target.id AND contact.revoked_at IS NULL
                    AND contact.verified_at=consent.contact_verified_at
                    AND consent.event_no=(SELECT max(latest.event_no) FROM owner_addition_consents latest WHERE latest.case_id=c.id)))))) THEN
        RAISE EXCEPTION 'Owner event requires approved independent case and matching grant' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER guard_owner_event_proof AFTER INSERT ON flexbridge.org_ownership_events
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_owner_event_proof();
    """)


def downgrade():
    raise RuntimeError('Ownership consent and grant history require reviewed forward recovery')
