"""Fixed-revision staff continuity with two independent immutable review stages."""
from alembic import op

revision='0010_owner_continuity'
down_revision='0009_owner_transfers'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.owner_continuity_requests (
      case_id uuid PRIMARY KEY REFERENCES flexbridge.verification_cases(id),
      recovery_id uuid NOT NULL UNIQUE REFERENCES flexbridge.recovery_requests(id),
      organization_id uuid NOT NULL REFERENCES flexbridge.organizations(id),
      applicant_id uuid NOT NULL REFERENCES flexbridge.users(id),
      membership_id uuid NOT NULL,
      staff_grant_id uuid NOT NULL REFERENCES flexbridge.org_role_grants(id),
      auth_version integer NOT NULL,
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      contact_id uuid NOT NULL REFERENCES flexbridge.user_contacts(id),
      contact_digest text NOT NULL,
      contact_verified_at timestamptz NOT NULL,
      created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
      owner_roster jsonb NOT NULL,
      evidence_file_ids jsonb NOT NULL,
      evidence_note text NOT NULL CHECK(length(evidence_note) BETWEEN 15 AND 4000),
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL,
      FOREIGN KEY(membership_id,organization_id) REFERENCES flexbridge.org_memberships(id,organization_id),
      UNIQUE(applicant_id,idempotency_key),
      CHECK(expires_at>created_at AND expires_at<=created_at+interval '24 hours'),
      CHECK(CASE WHEN jsonb_typeof(owner_roster)='array' THEN jsonb_array_length(owner_roster) BETWEEN 1 AND 256 ELSE false END),
      CHECK(octet_length(owner_roster::text)<=131072),
      CHECK(CASE WHEN jsonb_typeof(evidence_file_ids)='array' THEN jsonb_array_length(evidence_file_ids) BETWEEN 1 AND 5 ELSE false END));
    CREATE INDEX ix_continuity_applicant ON flexbridge.owner_continuity_requests(applicant_id,case_id);
    CREATE TABLE flexbridge.owner_continuity_events (
      id uuid PRIMARY KEY,
      case_id uuid NOT NULL REFERENCES flexbridge.owner_continuity_requests(case_id),
      stage text NOT NULL CHECK(stage IN ('MODERATOR','COMPLIANCE')),
      action text NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      authority_grant_id uuid NOT NULL REFERENCES flexbridge.platform_role_grants(id),
      auth_version integer NOT NULL,
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      created_at timestamptz NOT NULL,
      claim_id uuid REFERENCES flexbridge.owner_continuity_events(id),
      reason text,
      result_owner_grant_id uuid UNIQUE REFERENCES flexbridge.org_role_grants(id),
      ownership_event_id uuid UNIQUE REFERENCES flexbridge.org_ownership_events(id) DEFERRABLE INITIALLY DEFERRED,
      CHECK((stage='MODERATOR' AND action IN ('CLAIM','RECOMMEND','REJECT','NEEDS_INFO'))
        OR (stage='COMPLIANCE' AND action IN ('CLAIM','APPROVE','REJECT','NEEDS_INFO'))),
      CHECK((action='CLAIM' AND claim_id IS NULL AND reason IS NULL)
        OR (action<>'CLAIM' AND claim_id IS NOT NULL AND reason IS NOT NULL AND length(reason) BETWEEN 15 AND 2000)),
      CHECK((action='APPROVE' AND result_owner_grant_id IS NOT NULL AND ownership_event_id IS NOT NULL)
        OR (action<>'APPROVE' AND result_owner_grant_id IS NULL AND ownership_event_id IS NULL)));
    CREATE UNIQUE INDEX uq_continuity_claim ON flexbridge.owner_continuity_events(case_id,stage) WHERE action='CLAIM';
    CREATE UNIQUE INDEX uq_continuity_decision ON flexbridge.owner_continuity_events(case_id,stage) WHERE action<>'CLAIM';
    CREATE UNIQUE INDEX uq_open_owner_continuity ON flexbridge.verification_cases(organization_id)
      WHERE kind='ORG_OWNER_CONTINUITY' AND status IN ('WAITING_MODERATOR','WAITING_COMPLIANCE');
    CREATE TRIGGER immutable_owner_continuity_requests BEFORE UPDATE OR DELETE ON flexbridge.owner_continuity_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_owner_continuity_events BEFORE UPDATE OR DELETE ON flexbridge.owner_continuity_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    CREATE FUNCTION flexbridge.continuity_owner_roster(org uuid, excluded_member uuid DEFAULT NULL) RETURNS jsonb
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT coalesce(jsonb_agg(jsonb_build_object('user_id',u.id,'membership_id',m.id,
        'grant_id',g.id,'auth_version',u.auth_version) ORDER BY g.id),'[]'::jsonb)
      FROM org_memberships m JOIN users u ON u.id=m.user_id
      JOIN org_role_grants g ON g.membership_id=m.id JOIN role_catalog r ON r.id=g.role_id
      WHERE m.organization_id=org AND m.status='ACTIVE' AND m.revoked_at IS NULL
        AND u.status='ACTIVE' AND g.revoked_at IS NULL AND r.scope_kind='ORG' AND r.code='OWNER'
        AND (excluded_member IS NULL OR m.id<>excluded_member)
    $$;
    CREATE FUNCTION flexbridge.continuity_intent_valid(case_uuid uuid, include_result boolean DEFAULT false) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM owner_continuity_requests p
        JOIN users u ON u.id=p.applicant_id JOIN org_memberships m ON m.id=p.membership_id
        JOIN organizations o ON o.id=p.organization_id
        JOIN org_role_grants g ON g.id=p.staff_grant_id JOIN role_catalog r ON r.id=g.role_id
        JOIN user_contacts contact ON contact.id=p.contact_id
        WHERE p.case_id=case_uuid AND u.status='ACTIVE' AND u.auth_version=p.auth_version
          AND m.user_id=u.id AND m.organization_id=p.organization_id AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND o.status='VERIFIED' AND g.membership_id=m.id AND g.revoked_at IS NULL
          AND r.scope_kind='ORG' AND r.code IN ('HR','HOST_COORDINATOR','MENTOR','BILLING')
          AND contact.user_id=u.id AND contact.verified_at=p.contact_verified_at AND contact.revoked_at IS NULL
          AND p.expires_at>clock_timestamp()
          AND p.owner_roster=continuity_owner_roster(p.organization_id,CASE WHEN include_result THEN m.id ELSE NULL END)
          AND (include_result OR NOT EXISTS(SELECT 1 FROM org_role_grants own JOIN role_catalog role ON role.id=own.role_id
            WHERE own.membership_id=m.id AND own.revoked_at IS NULL AND role.scope_kind='ORG' AND role.code='OWNER'))
          AND (SELECT count(*) FROM files f JOIN jsonb_array_elements_text(p.evidence_file_ids) AS ids(value) ON ids.value=f.id::text
            WHERE f.owner_user_id=u.id AND f.scan_status='CLEAN' AND f.mime_type='application/pdf' AND f.deleted_at IS NULL)
            =jsonb_array_length(p.evidence_file_ids)
          AND (SELECT jsonb_agg(DISTINCT e.file_id::text ORDER BY e.file_id::text) FROM verification_evidence e
            WHERE e.case_id=p.case_id AND e.revision=1 AND e.file_id IS NOT NULL)=p.evidence_file_ids
          AND (SELECT count(*) FROM verification_evidence e WHERE e.case_id=p.case_id AND e.revision=1
            AND e.file_id IS NULL AND e.note=p.evidence_note)=1)
    $$;
    CREATE FUNCTION flexbridge.guard_continuity_request() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN recovery_requests recovery ON recovery.id=NEW.recovery_id
        JOIN sessions s ON s.id=NEW.session_id
        WHERE c.id=NEW.case_id AND c.kind='ORG_OWNER_CONTINUITY' AND c.status='WAITING_MODERATOR'
          AND c.current_revision=1 AND c.requester_id=NEW.applicant_id AND c.organization_id=NEW.organization_id
          AND recovery.kind='ORG_OWNER_CONTINUITY' AND recovery.status=c.status AND recovery.user_id=NEW.applicant_id
          AND recovery.reviewer_id IS NULL AND recovery.requester_contact_digest=NEW.contact_digest
          AND recovery.evidence_file_id::text=(NEW.evidence_file_ids->>0)
          AND s.user_id=NEW.applicant_id AND s.auth_version=NEW.auth_version AND s.assurance='MFA'
          AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()) OR NOT continuity_intent_valid(NEW.case_id,false) THEN
        RAISE EXCEPTION 'Invalid continuity self-request proof' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_continuity_request AFTER INSERT ON flexbridge.owner_continuity_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_continuity_request();

    CREATE FUNCTION flexbridge.guard_continuity_review() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE claim flexbridge.owner_continuity_events%ROWTYPE; BEGIN
      IF NOT EXISTS(SELECT 1 FROM owner_continuity_requests p JOIN verification_cases c ON c.id=p.case_id
        JOIN users u ON u.id=NEW.actor_id JOIN sessions s ON s.id=NEW.session_id
        JOIN platform_role_grants g ON g.id=NEW.authority_grant_id JOIN role_catalog r ON r.id=g.role_id
        WHERE p.case_id=NEW.case_id AND c.current_revision=1
          AND c.status=CASE WHEN NEW.stage='MODERATOR' THEN 'WAITING_MODERATOR' ELSE 'WAITING_COMPLIANCE' END
          AND NEW.actor_id<>p.applicant_id AND u.status='ACTIVE' AND u.auth_version=NEW.auth_version
          AND g.user_id=u.id AND g.revoked_at IS NULL AND g.expires_at>clock_timestamp()
          AND r.scope_kind='PLATFORM' AND r.code=NEW.stage
          AND s.user_id=u.id AND s.auth_version=u.auth_version AND s.assurance='MFA'
          AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
          AND NOT EXISTS(SELECT 1 FROM org_memberships related WHERE related.organization_id=p.organization_id AND related.user_id=u.id)
          AND NOT EXISTS(SELECT 1 FROM owner_continuity_events other WHERE other.case_id=p.case_id
            AND other.action='CLAIM' AND other.stage<>NEW.stage AND other.actor_id=u.id)) THEN
        RAISE EXCEPTION 'Invalid continuity reviewer scope or authority' USING ERRCODE='23514';
      END IF;
      IF NEW.action<>'CLAIM' THEN
        SELECT * INTO claim FROM owner_continuity_events WHERE id=NEW.claim_id;
        IF NOT FOUND OR claim.action<>'CLAIM' OR claim.case_id<>NEW.case_id OR claim.stage<>NEW.stage
          OR claim.actor_id<>NEW.actor_id OR claim.authority_grant_id<>NEW.authority_grant_id OR claim.auth_version<>NEW.auth_version THEN
          RAISE EXCEPTION 'Continuity decision requires its original stage claim' USING ERRCODE='23514';
        END IF;
      END IF;
      IF NEW.action IN ('RECOMMEND','APPROVE') AND NOT continuity_intent_valid(NEW.case_id,NEW.action='APPROVE') THEN
        RAISE EXCEPTION 'Stale continuity consent or roster' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_continuity_review BEFORE INSERT ON flexbridge.owner_continuity_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_continuity_review();

    CREATE FUNCTION flexbridge.continuity_event_valid(event_uuid uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM org_ownership_events history
        JOIN owner_continuity_requests p ON p.case_id=history.verification_case_id
        JOIN verification_cases c ON c.id=p.case_id JOIN recovery_requests recovery ON recovery.id=p.recovery_id
        JOIN owner_continuity_events final ON final.ownership_event_id=history.id AND final.case_id=p.case_id
          AND final.stage='COMPLIANCE' AND final.action='APPROVE'
        JOIN owner_continuity_events compliance_claim ON compliance_claim.id=final.claim_id
          AND compliance_claim.case_id=p.case_id AND compliance_claim.stage='COMPLIANCE' AND compliance_claim.action='CLAIM'
        JOIN owner_continuity_events recommendation ON recommendation.case_id=p.case_id
          AND recommendation.stage='MODERATOR' AND recommendation.action='RECOMMEND'
        JOIN owner_continuity_events moderator_claim ON moderator_claim.id=recommendation.claim_id
          AND moderator_claim.case_id=p.case_id AND moderator_claim.stage='MODERATOR' AND moderator_claim.action='CLAIM'
        JOIN users moderator ON moderator.id=recommendation.actor_id
        JOIN users authorizer ON authorizer.id=final.actor_id
        JOIN platform_role_grants moderator_grant ON moderator_grant.id=moderator_claim.authority_grant_id
        JOIN platform_role_grants compliance_grant ON compliance_grant.id=compliance_claim.authority_grant_id
        JOIN role_catalog moderator_role ON moderator_role.id=moderator_grant.role_id
        JOIN role_catalog compliance_role ON compliance_role.id=compliance_grant.role_id
        JOIN sessions final_session ON final_session.id=final.session_id
        JOIN org_role_grants result ON result.id=final.result_owner_grant_id
        JOIN role_catalog owner_role ON owner_role.id=result.role_id
        WHERE history.id=event_uuid AND history.previous_membership_id IS NULL
          AND history.organization_id=p.organization_id AND history.new_membership_id=p.membership_id
          AND c.kind='ORG_OWNER_CONTINUITY' AND c.organization_id=p.organization_id
          AND c.requester_id=p.applicant_id AND c.current_revision=1 AND c.status='APPROVED'
          AND c.assigned_reviewer_id=moderator.id
          AND recovery.kind='ORG_OWNER_CONTINUITY' AND recovery.status='COMPLETED'
          AND recovery.user_id=p.applicant_id AND recovery.reviewer_id IS NULL
          AND recommendation.actor_id=moderator_claim.actor_id AND final.actor_id=compliance_claim.actor_id
          AND recommendation.authority_grant_id=moderator_claim.authority_grant_id
          AND final.authority_grant_id=compliance_claim.authority_grant_id
          AND recommendation.auth_version=moderator_claim.auth_version AND final.auth_version=compliance_claim.auth_version
          AND moderator.id<>authorizer.id AND moderator.id<>p.applicant_id AND authorizer.id<>p.applicant_id
          AND moderator.status='ACTIVE' AND moderator.auth_version=recommendation.auth_version
          AND authorizer.status='ACTIVE' AND authorizer.auth_version=final.auth_version
          AND moderator_grant.user_id=moderator.id AND moderator_grant.revoked_at IS NULL
          AND moderator_grant.expires_at>clock_timestamp() AND moderator_role.code='MODERATOR' AND moderator_role.scope_kind='PLATFORM'
          AND compliance_grant.user_id=authorizer.id AND compliance_grant.revoked_at IS NULL
          AND compliance_grant.expires_at>clock_timestamp() AND compliance_role.code='COMPLIANCE' AND compliance_role.scope_kind='PLATFORM'
          AND final_session.user_id=authorizer.id AND final_session.auth_version=authorizer.auth_version
          AND final_session.assurance='MFA' AND final_session.revoked_at IS NULL AND final_session.expires_at>clock_timestamp()
          AND NOT EXISTS(SELECT 1 FROM org_memberships related WHERE related.organization_id=p.organization_id
            AND related.user_id IN (moderator.id,authorizer.id))
          AND result.membership_id=p.membership_id AND result.revoked_at IS NULL
          AND owner_role.scope_kind='ORG' AND owner_role.code='OWNER'
          AND result.granted_by_id=authorizer.id AND history.approved_by_id=authorizer.id
          AND history.effective_at=result.created_at AND continuity_intent_valid(p.case_id,true))
    $$;

    CREATE FUNCTION flexbridge.guard_continuity_case() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.kind='ORG_OWNER_CONTINUITY' AND (NEW.current_revision<>1 OR NEW.status<>'WAITING_MODERATOR'
          OR NEW.organization_id IS NULL OR NEW.assigned_reviewer_id IS NOT NULL OR NEW.decided_at IS NOT NULL) THEN
          RAISE EXCEPTION 'Continuity starts at fixed revision1' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.kind<>'ORG_OWNER_CONTINUITY' AND NEW.kind<>'ORG_OWNER_CONTINUITY' THEN RETURN NEW; END IF;
      IF OLD.kind<>NEW.kind OR NEW.current_revision<>1 OR OLD.current_revision<>NEW.current_revision
        OR OLD.organization_id IS DISTINCT FROM NEW.organization_id OR OLD.requester_id<>NEW.requester_id THEN
        RAISE EXCEPTION 'Continuity case identity and revision are fixed' USING ERRCODE='23514';
      END IF;
      IF OLD.status NOT IN ('WAITING_MODERATOR','WAITING_COMPLIANCE') AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'Continuity terminal result is immutable' USING ERRCODE='23514';
      END IF;
      IF NEW.status<>OLD.status AND NOT ((OLD.status='WAITING_MODERATOR'
          AND NEW.status IN ('WAITING_COMPLIANCE','REJECTED','NEEDS_INFO','CANCELLED','EXPIRED'))
        OR (OLD.status='WAITING_COMPLIANCE' AND NEW.status IN ('APPROVED','REJECTED','NEEDS_INFO','CANCELLED','EXPIRED'))) THEN
        RAISE EXCEPTION 'Invalid continuity transition' USING ERRCODE='23514';
      END IF;
      IF NEW.assigned_reviewer_id IS DISTINCT FROM OLD.assigned_reviewer_id AND (OLD.assigned_reviewer_id IS NOT NULL
        OR NOT EXISTS(SELECT 1 FROM owner_continuity_events e WHERE e.case_id=NEW.id AND e.stage='MODERATOR'
          AND e.action='CLAIM' AND e.actor_id=NEW.assigned_reviewer_id)) THEN
        RAISE EXCEPTION 'Continuity moderator assignment requires its immutable claim' USING ERRCODE='23514';
      END IF;
      IF NEW.status IN ('REJECTED','NEEDS_INFO') AND NEW.status<>OLD.status AND NOT EXISTS(
        SELECT 1 FROM owner_continuity_events e WHERE e.case_id=NEW.id
          AND e.stage=CASE WHEN OLD.status='WAITING_MODERATOR' THEN 'MODERATOR' ELSE 'COMPLIANCE' END
          AND e.action=CASE WHEN NEW.status='REJECTED' THEN 'REJECT' ELSE 'NEEDS_INFO' END) THEN
        RAISE EXCEPTION 'Continuity closure requires the assigned stage decision' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_continuity_case BEFORE INSERT OR UPDATE ON flexbridge.verification_cases
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_continuity_case();
    CREATE TRIGGER immutable_continuity_case_delete BEFORE DELETE ON flexbridge.verification_cases
      FOR EACH ROW WHEN (OLD.kind='ORG_OWNER_CONTINUITY') EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    ALTER TABLE flexbridge.recovery_requests ADD CONSTRAINT chk_continuity_tracking CHECK(
      kind<>'ORG_OWNER_CONTINUITY' OR (user_id IS NOT NULL AND reviewer_id IS NULL AND evidence_file_id IS NOT NULL
        AND status IN ('WAITING_MODERATOR','WAITING_COMPLIANCE','COMPLETED','REJECTED','NEEDS_INFO','CANCELLED','EXPIRED')));
    CREATE FUNCTION flexbridge.guard_continuity_tracking_identity() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF OLD.kind='ORG_OWNER_CONTINUITY' OR NEW.kind='ORG_OWNER_CONTINUITY' THEN
        IF OLD.kind<>NEW.kind OR OLD.user_id IS DISTINCT FROM NEW.user_id
          OR OLD.requester_contact_digest<>NEW.requester_contact_digest
          OR OLD.evidence_file_id IS DISTINCT FROM NEW.evidence_file_id OR NEW.reviewer_id IS NOT NULL THEN
          RAISE EXCEPTION 'Continuity tracking identity is immutable' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_continuity_tracking_identity BEFORE UPDATE ON flexbridge.recovery_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_continuity_tracking_identity();
    CREATE TRIGGER immutable_continuity_tracking_delete BEFORE DELETE ON flexbridge.recovery_requests
      FOR EACH ROW WHEN (OLD.kind='ORG_OWNER_CONTINUITY') EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    CREATE FUNCTION flexbridge.check_continuity_state(case_uuid uuid) RETURNS void
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE current_case flexbridge.verification_cases%ROWTYPE; BEGIN
      SELECT * INTO current_case FROM verification_cases WHERE id=case_uuid;
      IF NOT FOUND OR NOT EXISTS(SELECT 1 FROM owner_continuity_requests p JOIN recovery_requests r ON r.id=p.recovery_id
        WHERE p.case_id=case_uuid AND current_case.kind='ORG_OWNER_CONTINUITY' AND current_case.current_revision=1
          AND current_case.organization_id=p.organization_id AND current_case.requester_id=p.applicant_id
          AND r.kind='ORG_OWNER_CONTINUITY' AND r.user_id=p.applicant_id AND r.reviewer_id IS NULL
          AND r.requester_contact_digest=p.contact_digest AND r.evidence_file_id::text=(p.evidence_file_ids->>0)
          AND r.status=CASE WHEN current_case.status='APPROVED' THEN 'COMPLETED' ELSE current_case.status END
          AND ((current_case.status IN ('WAITING_MODERATOR','WAITING_COMPLIANCE') AND current_case.decided_at IS NULL AND r.resolved_at IS NULL)
            OR (current_case.status NOT IN ('WAITING_MODERATOR','WAITING_COMPLIANCE') AND current_case.decided_at IS NOT NULL AND r.resolved_at IS NOT NULL))) THEN
        RAISE EXCEPTION 'Continuity case and recovery tracking must agree' USING ERRCODE='23514';
      END IF;
      IF current_case.status IN ('WAITING_COMPLIANCE','APPROVED') AND NOT EXISTS(SELECT 1 FROM owner_continuity_events e
        WHERE e.case_id=case_uuid AND e.stage='MODERATOR' AND e.action='RECOMMEND'
          AND e.actor_id=current_case.assigned_reviewer_id) THEN
        RAISE EXCEPTION 'Continuity requires the moderator recommendation' USING ERRCODE='23514';
      END IF;
      IF current_case.status='APPROVED' AND NOT EXISTS(SELECT 1 FROM org_ownership_events e
        WHERE e.verification_case_id=case_uuid AND continuity_event_valid(e.id)) THEN
        RAISE EXCEPTION 'Continuity requires complete final grant proof' USING ERRCODE='23514';
      END IF;
    END $$;
    CREATE FUNCTION flexbridge.guard_continuity_state() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE case_uuid uuid; BEGIN
      IF TG_TABLE_NAME='verification_cases' THEN case_uuid:=NEW.id;
      ELSE SELECT p.case_id INTO case_uuid FROM owner_continuity_requests p WHERE p.recovery_id=NEW.id; END IF;
      IF case_uuid IS NULL THEN RAISE EXCEPTION 'Unlinked continuity tracking' USING ERRCODE='23514'; END IF;
      PERFORM check_continuity_state(case_uuid);
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER guard_continuity_case_state AFTER INSERT OR UPDATE ON flexbridge.verification_cases
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.kind='ORG_OWNER_CONTINUITY')
      EXECUTE FUNCTION flexbridge.guard_continuity_state();
    CREATE CONSTRAINT TRIGGER guard_continuity_tracking_state AFTER INSERT OR UPDATE ON flexbridge.recovery_requests
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.kind='ORG_OWNER_CONTINUITY')
      EXECUTE FUNCTION flexbridge.guard_continuity_state();
    CREATE OR REPLACE FUNCTION flexbridge.guard_owner_event_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF EXISTS(SELECT 1 FROM verification_cases c WHERE c.id=NEW.verification_case_id AND c.kind='ORG_OWNER_CONTINUITY') THEN
        IF NOT continuity_event_valid(NEW.id) THEN
          RAISE EXCEPTION 'Continuity ownership requires both independent stage proofs' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
      END IF;
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN org_memberships m ON m.id=NEW.new_membership_id
        JOIN organizations o ON o.id=m.organization_id
        JOIN org_role_grants g ON g.membership_id=m.id JOIN role_catalog r ON r.id=g.role_id
        WHERE c.id=NEW.verification_case_id AND c.organization_id=NEW.organization_id AND c.status='APPROVED'
          AND c.assigned_reviewer_id=NEW.approved_by_id AND c.requester_id<>NEW.approved_by_id
          AND m.organization_id=NEW.organization_id AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND o.status='VERIFIED' AND r.code='OWNER' AND r.scope_kind='ORG' AND g.revoked_at IS NULL
          AND g.granted_by_id=NEW.approved_by_id
          AND EXISTS(SELECT 1 FROM users reviewer JOIN platform_role_grants authority ON authority.user_id=reviewer.id
            JOIN role_catalog platform_role ON platform_role.id=authority.role_id
            WHERE reviewer.id=NEW.approved_by_id AND reviewer.status='ACTIVE'
              AND authority.revoked_at IS NULL AND authority.expires_at>clock_timestamp()
              AND platform_role.code='MODERATOR' AND platform_role.scope_kind='PLATFORM')
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
                  WHERE old_grant.id=p.requester_grant_id AND old_grant.membership_id=previous.id AND old_grant.revoked_at IS NULL
                    AND old_role.code='OWNER' AND old_role.scope_kind='ORG')
                AND EXISTS(SELECT 1 FROM owner_addition_consents consent JOIN user_contacts contact ON contact.id=consent.contact_id
                  JOIN org_role_grants staff_grant ON staff_grant.id=consent.target_staff_grant_id
                  JOIN role_catalog staff_role ON staff_role.id=staff_grant.role_id
                  WHERE consent.case_id=c.id AND consent.revision=c.current_revision AND consent.decision='ACCEPT'
                    AND consent.actor_id=target.id AND consent.auth_version=target.auth_version
                    AND consent.expires_at>clock_timestamp() AND contact.user_id=target.id AND contact.revoked_at IS NULL
                    AND staff_grant.membership_id=p.target_membership_id AND staff_grant.revoked_at IS NULL
                    AND staff_role.scope_kind='ORG' AND staff_role.code IN ('HR','HOST_COORDINATOR','MENTOR','BILLING')
                    AND contact.verified_at=consent.contact_verified_at
                    AND consent.event_no=(SELECT max(latest.event_no) FROM owner_addition_consents latest WHERE latest.case_id=c.id)))))) THEN
        RAISE EXCEPTION 'Owner event requires approved independent case and matching grant' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    """)


def downgrade():
    raise RuntimeError('Continuity consent and review history require reviewed forward recovery')
