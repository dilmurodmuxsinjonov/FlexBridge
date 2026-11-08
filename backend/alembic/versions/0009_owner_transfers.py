"""Reviewed OWNER departure to an existing owner; preserve prior addition proof."""
from alembic import op

revision='0009_owner_transfers'
down_revision='0008_owner_additions'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.owner_transfer_requests (
      case_id uuid PRIMARY KEY REFERENCES flexbridge.verification_cases(id),
      created_at timestamptz NOT NULL,
      organization_id uuid NOT NULL REFERENCES flexbridge.organizations(id),
      requester_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      requester_membership_id uuid NOT NULL,
      requester_grant_id uuid NOT NULL REFERENCES flexbridge.org_role_grants(id),
      requester_auth_version integer NOT NULL,
      requester_session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      target_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      target_membership_id uuid NOT NULL,
      target_grant_id uuid NOT NULL REFERENCES flexbridge.org_role_grants(id),
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL,
      CHECK(requester_user_id<>target_user_id AND requester_membership_id<>target_membership_id),
      FOREIGN KEY(requester_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id),
      FOREIGN KEY(target_membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id),
      UNIQUE(requester_user_id,idempotency_key));
    CREATE INDEX ix_owner_transfer_target ON flexbridge.owner_transfer_requests(target_user_id,case_id);
    CREATE TABLE flexbridge.owner_transfer_consents (
      id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES flexbridge.owner_transfer_requests(case_id),
      created_at timestamptz NOT NULL, revision integer NOT NULL CHECK(revision>0),
      event_no integer NOT NULL CHECK(event_no>0),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id), auth_version integer NOT NULL,
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      decision text NOT NULL CHECK(decision IN ('ACCEPT','DECLINE')),
      target_owner_grant_id uuid REFERENCES flexbridge.org_role_grants(id),
      contact_id uuid REFERENCES flexbridge.user_contacts(id), contact_digest text,
      contact_verified_at timestamptz, expires_at timestamptz,
      CHECK((decision='ACCEPT' AND target_owner_grant_id IS NOT NULL AND contact_id IS NOT NULL AND contact_digest IS NOT NULL
        AND contact_verified_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at>created_at
        AND expires_at<=created_at+interval '24 hours')
        OR (decision='DECLINE' AND target_owner_grant_id IS NULL AND contact_id IS NULL AND contact_digest IS NULL
        AND contact_verified_at IS NULL AND expires_at IS NULL)),
      UNIQUE(case_id,event_no));
    CREATE TRIGGER immutable_owner_transfer_requests BEFORE UPDATE OR DELETE ON flexbridge.owner_transfer_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_owner_transfer_consents BEFORE UPDATE OR DELETE ON flexbridge.owner_transfer_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE FUNCTION flexbridge.guard_owner_transfer_proposal() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN org_memberships r ON r.id=NEW.requester_membership_id
        JOIN org_memberships t ON t.id=NEW.target_membership_id JOIN users u ON u.id=r.user_id
        JOIN users target ON target.id=t.user_id JOIN sessions session ON session.id=NEW.requester_session_id
        WHERE c.id=NEW.case_id AND c.kind='ORG_OWNER_TRANSFER' AND c.organization_id=NEW.organization_id
          AND c.requester_id=NEW.requester_user_id AND r.user_id=NEW.requester_user_id
          AND t.user_id=NEW.target_user_id AND r.organization_id=NEW.organization_id AND t.organization_id=NEW.organization_id
          AND r.status='ACTIVE' AND r.revoked_at IS NULL AND t.status='ACTIVE' AND t.revoked_at IS NULL
          AND u.status='ACTIVE' AND u.auth_version=NEW.requester_auth_version AND target.status='ACTIVE'
          AND session.user_id=u.id AND session.auth_version=u.auth_version AND session.assurance='MFA'
          AND session.revoked_at IS NULL AND session.expires_at>clock_timestamp()
          AND EXISTS(SELECT 1 FROM org_role_grants g JOIN role_catalog rc ON rc.id=g.role_id
            WHERE g.id=NEW.requester_grant_id AND g.membership_id=r.id AND g.revoked_at IS NULL AND rc.code='OWNER' AND rc.scope_kind='ORG')
          AND EXISTS(SELECT 1 FROM org_role_grants g JOIN role_catalog rc ON rc.id=g.role_id
            WHERE g.id=NEW.target_grant_id AND g.membership_id=t.id AND g.revoked_at IS NULL AND rc.code='OWNER'
              AND rc.scope_kind='ORG')) THEN
        RAISE EXCEPTION 'Owner proposal scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_owner_transfer_proposal BEFORE INSERT ON flexbridge.owner_transfer_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_owner_transfer_proposal();
    CREATE FUNCTION flexbridge.guard_owner_transfer_consent() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM owner_transfer_requests p JOIN verification_cases c ON c.id=p.case_id
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
      IF NEW.decision='ACCEPT' AND NOT EXISTS(SELECT 1 FROM owner_transfer_requests p
        JOIN org_role_grants g ON g.id=NEW.target_owner_grant_id AND g.membership_id=p.target_membership_id
        JOIN role_catalog r ON r.id=g.role_id WHERE p.case_id=NEW.case_id AND g.revoked_at IS NULL
          AND r.scope_kind='ORG' AND r.code='OWNER' AND g.id=p.target_grant_id) THEN
        RAISE EXCEPTION 'Owner consent staff grant mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_owner_transfer_consent BEFORE INSERT ON flexbridge.owner_transfer_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_owner_transfer_consent();
    -- Events with a previous membership are transfers, never initial/addition grants.
    -- Preserve the existing guard function and restrict its trigger to its event shape.
    DROP TRIGGER guard_owner_event_proof ON flexbridge.org_ownership_events;
    CREATE CONSTRAINT TRIGGER guard_owner_event_proof AFTER INSERT ON flexbridge.org_ownership_events
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.previous_membership_id IS NULL)
      EXECUTE FUNCTION flexbridge.guard_owner_event_proof();
    CREATE FUNCTION flexbridge.guard_owner_transfer_event_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM owner_transfer_requests p
        JOIN verification_cases c ON c.id=p.case_id
        JOIN organizations o ON o.id=p.organization_id
        JOIN org_memberships previous ON previous.id=p.requester_membership_id
        JOIN org_memberships target_member ON target_member.id=p.target_membership_id
        JOIN users requester ON requester.id=p.requester_user_id
        JOIN users target ON target.id=p.target_user_id
        JOIN org_role_grants departing ON departing.id=p.requester_grant_id
        JOIN role_catalog departing_role ON departing_role.id=departing.role_id
        JOIN org_role_grants successor ON successor.id=p.target_grant_id
        JOIN role_catalog successor_role ON successor_role.id=successor.role_id
        WHERE c.id=NEW.verification_case_id AND c.kind='ORG_OWNER_TRANSFER' AND c.status='APPROVED'
          AND c.current_revision>0 AND c.assigned_reviewer_id=NEW.approved_by_id
          AND c.requester_id=p.requester_user_id AND c.organization_id=p.organization_id
          AND p.organization_id=NEW.organization_id AND o.status='VERIFIED'
          AND p.requester_membership_id=NEW.previous_membership_id AND p.target_membership_id=NEW.new_membership_id
          AND previous.user_id=p.requester_user_id AND previous.organization_id=p.organization_id
          AND target_member.user_id=p.target_user_id AND target_member.organization_id=p.organization_id
          AND previous.status='ACTIVE' AND previous.revoked_at IS NULL
          AND target_member.status='ACTIVE' AND target_member.revoked_at IS NULL
          AND requester.status='ACTIVE' AND requester.auth_version=p.requester_auth_version AND target.status='ACTIVE'
          AND departing.membership_id=previous.id AND departing.revoked_at=NEW.effective_at
          AND departing_role.code='OWNER' AND departing_role.scope_kind='ORG'
          AND successor.membership_id=target_member.id AND successor.revoked_at IS NULL
          AND successor_role.code='OWNER' AND successor_role.scope_kind='ORG'
          AND EXISTS(SELECT 1 FROM users reviewer JOIN platform_role_grants authority ON authority.user_id=reviewer.id
            JOIN role_catalog role ON role.id=authority.role_id
            WHERE reviewer.id=NEW.approved_by_id AND reviewer.status='ACTIVE'
              AND authority.revoked_at IS NULL AND authority.expires_at>clock_timestamp()
              AND role.code='MODERATOR' AND role.scope_kind='PLATFORM')
          AND NOT EXISTS(SELECT 1 FROM org_memberships reviewer
            WHERE reviewer.user_id=NEW.approved_by_id AND reviewer.organization_id=p.organization_id)
          AND EXISTS(SELECT 1 FROM owner_transfer_consents consent
            JOIN user_contacts contact ON contact.id=consent.contact_id
            WHERE consent.case_id=c.id AND consent.actor_id=target.id AND consent.decision='ACCEPT'
              AND consent.revision=c.current_revision AND consent.auth_version=target.auth_version
              AND consent.target_owner_grant_id=successor.id AND consent.expires_at>clock_timestamp()
              AND contact.user_id=target.id AND contact.verified_at=consent.contact_verified_at AND contact.revoked_at IS NULL
              AND consent.event_no=(SELECT max(latest.event_no) FROM owner_transfer_consents latest WHERE latest.case_id=c.id))) THEN
        RAISE EXCEPTION 'Owner transfer requires current successor, revoked source and independent approved proof' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER guard_owner_transfer_event_proof AFTER INSERT ON flexbridge.org_ownership_events
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.previous_membership_id IS NOT NULL)
      EXECUTE FUNCTION flexbridge.guard_owner_transfer_event_proof();
    """)


def downgrade():
    raise RuntimeError("Ownership departure history requires reviewed forward recovery")
