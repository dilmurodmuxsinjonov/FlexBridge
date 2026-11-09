"""Revision-bound institution appointment review and personal acceptance.

The canonical baseline remains historical; these are forward runtime extensions.
"""
from alembic import op

revision='0011_institution_onboarding'
down_revision='0010_owner_continuity'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM flexbridge.institutions
        GROUP BY upper(btrim(registry_code)) HAVING count(*)>1) THEN
        RAISE EXCEPTION 'Institution registry normalization collision; reconcile explicitly before upgrade';
      END IF;
    END $$;
    CREATE UNIQUE INDEX uq_institution_registry_normalized ON flexbridge.institutions(upper(btrim(registry_code)));
    ALTER TABLE flexbridge.institution_memberships DROP CONSTRAINT institution_memberships_institution_id_user_id_key;
    CREATE UNIQUE INDEX uq_institution_active_member ON flexbridge.institution_memberships(institution_id,user_id)
      WHERE status='ACTIVE' AND revoked_at IS NULL;
    INSERT INTO flexbridge.role_catalog(id,created_at,updated_at,code,scope_kind,description)
      SELECT gen_random_uuid(),now(),now(),role.code,'INSTITUTION',role.code
      FROM unnest(ARRAY['COORDINATOR','TEACHER']) AS role(code)
      WHERE NOT EXISTS(SELECT 1 FROM flexbridge.role_catalog r WHERE r.code=role.code AND r.scope_kind='INSTITUTION');

    -- Invalid historical links are retained, with their effective grants closed.
    -- No fabricated case, acceptance, identity or document review is backfilled.
    WITH invalid AS (
      SELECT g.id FROM flexbridge.institution_role_grants g
      JOIN flexbridge.institution_memberships m ON m.id=g.membership_id
      JOIN flexbridge.institution_appointments a ON a.id=g.appointment_id
      JOIN flexbridge.role_catalog r ON r.id=g.role_id
      WHERE g.revoked_at IS NULL AND (m.user_id<>a.user_id OR m.institution_id<>a.institution_id
        OR r.scope_kind<>'INSTITUTION' OR r.code NOT IN ('COORDINATOR','TEACHER'))
    ), closed AS (
      UPDATE flexbridge.institution_role_grants g SET revoked_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM invalid i WHERE g.id=i.id RETURNING g.id
    )
    INSERT INTO flexbridge.audit_events(id,created_at,updated_at,actor_id,action,object_type,object_key,scope_snapshot,request_id,occurred_at)
      SELECT gen_random_uuid(),now(),now(),NULL,'INSTITUTION_LEGACY_SCOPE_CLOSED','institution_role_grant',id::text,
        '{"migration":"0011_institution_onboarding","reason":"structural_scope_mismatch"}'::jsonb,gen_random_uuid(),now() FROM closed;

    CREATE TABLE flexbridge.institution_onboarding_requests (
      case_id uuid PRIMARY KEY REFERENCES flexbridge.verification_cases(id),
      created_at timestamptz NOT NULL,
      institution_id uuid NOT NULL REFERENCES flexbridge.institutions(id),
      appointment_id uuid NOT NULL UNIQUE REFERENCES flexbridge.institution_appointments(id),
      requester_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      target_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      mode text NOT NULL CHECK(mode IN ('FIRST_COORDINATOR','STAFF_TEACHER')),
      role_id uuid NOT NULL REFERENCES flexbridge.role_catalog(id),
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL,
      UNIQUE(requester_user_id,idempotency_key),
      CHECK((mode='FIRST_COORDINATOR' AND requester_user_id=target_user_id) OR
        (mode='STAFF_TEACHER' AND requester_user_id<>target_user_id)));
    CREATE INDEX ix_institution_request_target ON flexbridge.institution_onboarding_requests(target_user_id,case_id);
    CREATE INDEX ix_institution_request_institution ON flexbridge.institution_onboarding_requests(institution_id,case_id);
    CREATE TABLE flexbridge.institution_onboarding_submissions (
      case_id uuid NOT NULL REFERENCES flexbridge.institution_onboarding_requests(case_id),
      revision integer NOT NULL CHECK(revision>0),created_at timestamptz NOT NULL,
      submitted_by_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      requester_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),
      requester_contact_id uuid NOT NULL REFERENCES flexbridge.user_contacts(id),
      requester_contact_digest text NOT NULL,requester_contact_verified_at timestamptz NOT NULL,
      target_contact_id uuid NOT NULL REFERENCES flexbridge.user_contacts(id),
      target_contact_digest text NOT NULL,target_contact_verified_at timestamptz NOT NULL,
      target_auth_version integer NOT NULL,
      document_file_id uuid NOT NULL REFERENCES flexbridge.files(id),
      agreement_id uuid NOT NULL REFERENCES flexbridge.institution_agreements(id),
      legal_basis text NOT NULL CHECK(length(btrim(legal_basis)) BETWEEN 15 AND 4000),
      valid_from date NOT NULL,valid_to date,
      payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
      PRIMARY KEY(case_id,revision),CHECK(valid_to IS NULL OR valid_to>=valid_from));
    CREATE TABLE flexbridge.institution_onboarding_consents (
      id uuid PRIMARY KEY,case_id uuid NOT NULL,revision integer NOT NULL,
      event_no integer NOT NULL CHECK(event_no>0),created_at timestamptz NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      decision text NOT NULL CHECK(decision IN ('ACCEPT','DECLINE')),
      contact_id uuid REFERENCES flexbridge.user_contacts(id),contact_digest text,
      contact_verified_at timestamptz,expires_at timestamptz,
      FOREIGN KEY(case_id,revision) REFERENCES flexbridge.institution_onboarding_submissions(case_id,revision),
      UNIQUE(case_id,event_no),
      CHECK((decision='ACCEPT' AND contact_id IS NOT NULL AND contact_digest IS NOT NULL
        AND contact_verified_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at>created_at
        AND expires_at<=created_at+interval '24 hours') OR
        (decision='DECLINE' AND contact_id IS NULL AND contact_digest IS NULL AND contact_verified_at IS NULL AND expires_at IS NULL)));
    CREATE TABLE flexbridge.institution_onboarding_decisions (
      case_id uuid NOT NULL,revision integer NOT NULL,created_at timestamptz NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      platform_grant_id uuid NOT NULL REFERENCES flexbridge.platform_role_grants(id),
      decision text NOT NULL CHECK(decision IN ('APPROVE','REJECT','NEEDS_INFO')),
      reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 15 AND 4000),
      PRIMARY KEY(case_id,revision),
      FOREIGN KEY(case_id,revision) REFERENCES flexbridge.institution_onboarding_submissions(case_id,revision));
    CREATE TRIGGER immutable_institution_requests BEFORE UPDATE OR DELETE ON flexbridge.institution_onboarding_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_institution_submissions BEFORE UPDATE OR DELETE ON flexbridge.institution_onboarding_submissions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_institution_consents BEFORE UPDATE OR DELETE ON flexbridge.institution_onboarding_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_institution_decisions BEFORE UPDATE OR DELETE ON flexbridge.institution_onboarding_decisions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    CREATE FUNCTION flexbridge.guard_institution_grant() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='UPDATE' THEN
        IF (NEW.membership_id,NEW.role_id,NEW.appointment_id) IS DISTINCT FROM
           (OLD.membership_id,OLD.role_id,OLD.appointment_id) OR
           (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN
          RAISE EXCEPTION 'Institution grant history is immutable' USING ERRCODE='23514';
        END IF;
        IF NEW.revoked_at IS NOT NULL THEN RETURN NEW; END IF;
      END IF;
      IF NOT EXISTS(SELECT 1 FROM institution_memberships m
        JOIN institution_appointments a ON a.id=NEW.appointment_id
        JOIN role_catalog r ON r.id=NEW.role_id
        WHERE m.id=NEW.membership_id AND m.user_id=a.user_id AND m.institution_id=a.institution_id
          AND r.scope_kind='INSTITUTION' AND r.code IN ('COORDINATOR','TEACHER')) THEN
        RAISE EXCEPTION 'Institution grant scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_grant BEFORE INSERT OR UPDATE ON flexbridge.institution_role_grants
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_grant();
    CREATE TRIGGER immutable_institution_grant_delete BEFORE DELETE ON flexbridge.institution_role_grants
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE FUNCTION flexbridge.guard_institution_parent_identity() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF (NEW.user_id,NEW.institution_id) IS NOT DISTINCT FROM (OLD.user_id,OLD.institution_id) THEN RETURN NEW; END IF;
      IF TG_TABLE_NAME='institution_memberships' THEN
        IF EXISTS(SELECT 1 FROM institution_role_grants g JOIN institution_appointments a ON a.id=g.appointment_id
          WHERE g.membership_id=OLD.id
            AND (NEW.user_id<>a.user_id OR NEW.institution_id<>a.institution_id)) THEN
          RAISE EXCEPTION 'Institution membership identity is bound to active grants' USING ERRCODE='23514';
        END IF;
      ELSE
        IF EXISTS(SELECT 1 FROM institution_role_grants g JOIN institution_memberships m ON m.id=g.membership_id
          WHERE g.appointment_id=OLD.id
            AND (NEW.user_id<>m.user_id OR NEW.institution_id<>m.institution_id)) THEN
          RAISE EXCEPTION 'Institution appointment identity is bound to active grants' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_member_identity BEFORE UPDATE OF user_id,institution_id ON flexbridge.institution_memberships
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_parent_identity();
    CREATE TRIGGER guard_institution_appointment_identity BEFORE UPDATE OF user_id,institution_id ON flexbridge.institution_appointments
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_parent_identity();
    CREATE FUNCTION flexbridge.guard_institution_request() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN institution_appointments a ON a.id=NEW.appointment_id
        JOIN role_catalog r ON r.id=NEW.role_id WHERE c.id=NEW.case_id AND c.appointment_id=a.id
          AND c.kind='INSTITUTION_APPOINTMENT' AND c.requester_id=NEW.requester_user_id
          AND a.verification_case_id=c.id AND a.institution_id=NEW.institution_id AND a.user_id=NEW.target_user_id
          AND r.scope_kind='INSTITUTION' AND ((NEW.mode='FIRST_COORDINATOR' AND r.code='COORDINATOR')
            OR (NEW.mode='STAFF_TEACHER' AND r.code='TEACHER'))) THEN
        RAISE EXCEPTION 'Institution request scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_request BEFORE INSERT ON flexbridge.institution_onboarding_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_request();

    CREATE FUNCTION flexbridge.guard_institution_submission() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM institution_onboarding_requests q
        JOIN verification_cases c ON c.id=q.case_id
        JOIN users u ON u.id=q.requester_user_id JOIN users target ON target.id=q.target_user_id
        JOIN sessions s ON s.id=NEW.session_id
        JOIN user_contacts own ON own.id=NEW.requester_contact_id
        JOIN user_contacts recipient ON recipient.id=NEW.target_contact_id
        JOIN files f ON f.id=NEW.document_file_id
        JOIN institution_agreements agreement ON agreement.id=NEW.agreement_id
        WHERE q.case_id=NEW.case_id AND c.current_revision=NEW.revision AND c.status IN ('PENDING','IN_REVIEW')
          AND NEW.submitted_by_id=u.id AND u.status='ACTIVE' AND u.auth_version=NEW.auth_version
          AND target.status='ACTIVE' AND target.auth_version=NEW.target_auth_version
          AND s.user_id=u.id AND s.auth_version=u.auth_version AND s.assurance='MFA'
          AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
          AND own.user_id=u.id AND own.revoked_at IS NULL AND own.verified_at=NEW.requester_contact_verified_at
          AND own.verified_at<=clock_timestamp()
          AND recipient.user_id=target.id AND recipient.revoked_at IS NULL AND recipient.verified_at=NEW.target_contact_verified_at
          AND recipient.verified_at<=clock_timestamp()
          AND f.owner_user_id=u.id AND f.scan_status='CLEAN' AND f.deleted_at IS NULL AND f.mime_type='application/pdf'
          AND agreement.institution_id=q.institution_id
          AND ((q.mode='FIRST_COORDINATOR' AND NEW.requester_grant_id IS NULL) OR
            (q.mode='STAFF_TEACHER' AND EXISTS(
              SELECT 1 FROM institution_role_grants g JOIN institution_memberships m ON m.id=g.membership_id
              JOIN institution_appointments a ON a.id=g.appointment_id JOIN role_catalog r ON r.id=g.role_id
              JOIN institutions i ON i.id=m.institution_id
              WHERE g.id=NEW.requester_grant_id AND g.revoked_at IS NULL AND m.user_id=u.id
                AND m.institution_id=q.institution_id AND m.status='ACTIVE' AND m.revoked_at IS NULL
                AND m.accepted_at<=clock_timestamp() AND i.status='VERIFIED'
                AND a.user_id=m.user_id AND a.institution_id=m.institution_id AND a.status='ACTIVE'
                AND a.accepted_at<=clock_timestamp() AND a.valid_from<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
                AND (a.valid_to IS NULL OR a.valid_to>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date)
                AND r.scope_kind='INSTITUTION' AND r.code='COORDINATOR')))) THEN
        RAISE EXCEPTION 'Institution submission authority or scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_submission BEFORE INSERT ON flexbridge.institution_onboarding_submissions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_submission();
    CREATE FUNCTION flexbridge.guard_institution_consent() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM institution_onboarding_requests q
        JOIN verification_cases c ON c.id=q.case_id JOIN role_catalog r ON r.id=q.role_id
        JOIN users u ON u.id=q.target_user_id JOIN sessions s ON s.id=NEW.session_id
        JOIN institution_onboarding_submissions v ON v.case_id=q.case_id AND v.revision=NEW.revision
        WHERE q.case_id=NEW.case_id AND c.current_revision=NEW.revision AND NEW.actor_id=u.id
          AND u.status='ACTIVE' AND u.auth_version=NEW.auth_version
          AND s.user_id=u.id AND s.auth_version=u.auth_version AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
          AND (r.code='TEACHER' OR s.assurance='MFA') AND
          (NEW.decision='DECLINE' OR (c.status IN ('PENDING','IN_REVIEW','APPROVED') AND
            NEW.contact_id=v.target_contact_id AND NEW.contact_digest=v.target_contact_digest AND
            NEW.contact_verified_at=v.target_contact_verified_at AND u.auth_version=v.target_auth_version AND
            EXISTS(SELECT 1 FROM user_contacts contact WHERE contact.id=NEW.contact_id AND contact.user_id=u.id
              AND contact.revoked_at IS NULL AND contact.verified_at=NEW.contact_verified_at
              AND contact.verified_at<=clock_timestamp())))) THEN
        RAISE EXCEPTION 'Institution consent authority or scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_consent BEFORE INSERT ON flexbridge.institution_onboarding_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_consent();
    CREATE FUNCTION flexbridge.guard_institution_decision() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM institution_onboarding_requests q
        JOIN verification_cases c ON c.id=q.case_id JOIN users u ON u.id=NEW.actor_id
        JOIN sessions s ON s.id=NEW.session_id JOIN platform_role_grants g ON g.id=NEW.platform_grant_id
        JOIN role_catalog r ON r.id=g.role_id WHERE q.case_id=NEW.case_id
          AND c.current_revision=NEW.revision AND c.status='IN_REVIEW' AND c.assigned_reviewer_id=u.id
          AND u.id<>q.requester_user_id AND u.id<>q.target_user_id AND u.status='ACTIVE' AND u.auth_version=NEW.auth_version
          AND s.user_id=u.id AND s.auth_version=u.auth_version AND s.assurance='MFA'
          AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
          AND g.user_id=u.id AND g.revoked_at IS NULL AND g.expires_at>clock_timestamp()
          AND r.scope_kind='PLATFORM' AND r.code='MODERATOR'
          AND NOT EXISTS(SELECT 1 FROM institution_memberships m WHERE m.institution_id=q.institution_id AND m.user_id=u.id)) THEN
        RAISE EXCEPTION 'Institution decision authority or scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_institution_decision BEFORE INSERT ON flexbridge.institution_onboarding_decisions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_institution_decision();
    """)


def downgrade():
    raise RuntimeError('Institution review and consent history requires an explicit data-preserving rollback plan')
