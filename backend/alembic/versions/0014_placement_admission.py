"""Preserve imported placements; bind new starts to versioned personal evidence."""
from alembic import op

revision = '0014_placement_admission'
down_revision = '0013_enrollment_verification'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.placement_intakes (
      placement_id uuid PRIMARY KEY REFERENCES flexbridge.placements(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      offer_id uuid NOT NULL REFERENCES flexbridge.offers(id),
      attempt_id uuid NOT NULL REFERENCES flexbridge.application_attempts(id),
      revision_id uuid NOT NULL REFERENCES flexbridge.opportunity_revisions(id),
      academic_required boolean NOT NULL,
      actor_id uuid REFERENCES flexbridge.users(id), session_id uuid REFERENCES flexbridge.sessions(id),
      auth_version integer, host_grant_id uuid REFERENCES flexbridge.org_role_grants(id),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      source_snapshot jsonb NOT NULL CHECK(jsonb_typeof(source_snapshot)='object'),
      CHECK((origin='PUBLIC' AND actor_id IS NOT NULL AND session_id IS NOT NULL
        AND auth_version IS NOT NULL AND host_grant_id IS NOT NULL)
        OR (origin='LEGACY_IMPORT' AND actor_id IS NULL AND session_id IS NULL
          AND auth_version IS NULL AND host_grant_id IS NULL))
    );
    INSERT INTO flexbridge.placement_intakes(placement_id,origin,offer_id,attempt_id,revision_id,
      academic_required,initial_snapshot,source_snapshot)
      SELECT p.id,'LEGACY_IMPORT',o.id,o.attempt_id,o.revision_id,
        r.contract_type='ACADEMIC_TRIPARTITE',to_jsonb(p),
        jsonb_build_object('offer',to_jsonb(o),'application',to_jsonb(a),'attempt',to_jsonb(t),'revision',to_jsonb(r))
      FROM flexbridge.placements p JOIN flexbridge.offers o ON o.id=p.offer_id
      JOIN flexbridge.applications a ON a.id=p.application_id
      JOIN flexbridge.application_attempts t ON t.id=o.attempt_id
      JOIN flexbridge.opportunity_revisions r ON r.id=o.revision_id;

    CREATE TABLE flexbridge.mentor_assignment_proofs (
      assignment_id uuid PRIMARY KEY REFERENCES flexbridge.mentor_assignments(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_intakes(placement_id),
      mentor_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      mentor_grant_id uuid REFERENCES flexbridge.org_role_grants(id),
      actor_id uuid REFERENCES flexbridge.users(id), session_id uuid REFERENCES flexbridge.sessions(id),
      auth_version integer, host_grant_id uuid REFERENCES flexbridge.org_role_grants(id),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.mentor_assignments(id,placement_id),
      CHECK((origin='PUBLIC' AND mentor_grant_id IS NOT NULL AND actor_id IS NOT NULL
        AND session_id IS NOT NULL AND auth_version IS NOT NULL AND host_grant_id IS NOT NULL)
        OR (origin='LEGACY_IMPORT' AND actor_id IS NULL AND session_id IS NULL
          AND auth_version IS NULL AND host_grant_id IS NULL))
    );
    INSERT INTO flexbridge.mentor_assignment_proofs(assignment_id,origin,placement_id,mentor_user_id,
      mentor_grant_id,initial_snapshot)
      SELECT a.id,'LEGACY_IMPORT',a.placement_id,m.user_id,g.id,to_jsonb(a)
      FROM flexbridge.mentor_assignments a JOIN flexbridge.org_memberships m ON m.id=a.membership_id
      LEFT JOIN flexbridge.role_catalog r ON r.scope_kind='ORG' AND r.code='MENTOR'
      LEFT JOIN flexbridge.org_role_grants g ON g.membership_id=m.id AND g.role_id=r.id AND g.revoked_at IS NULL;

    CREATE TABLE flexbridge.placement_consents (
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_intakes(placement_id),
      terms_id uuid NOT NULL, side text NOT NULL CHECK(side IN ('CANDIDATE','MENTOR','HOST')),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id), session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      auth_version integer NOT NULL, org_grant_id uuid REFERENCES flexbridge.org_role_grants(id),
      assignment_id uuid, idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(terms_id,placement_id) REFERENCES flexbridge.placement_terms(id,placement_id),
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.mentor_assignments(id,placement_id),
      UNIQUE(actor_id,idempotency_key),
      UNIQUE NULLS NOT DISTINCT(placement_id,terms_id,side,actor_id,assignment_id),
      CHECK((side='CANDIDATE' AND org_grant_id IS NULL AND assignment_id IS NULL)
        OR (side='HOST' AND org_grant_id IS NOT NULL AND assignment_id IS NULL)
        OR (side='MENTOR' AND org_grant_id IS NOT NULL AND assignment_id IS NOT NULL))
    );
    CREATE TABLE flexbridge.placement_admission_events (
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_intakes(placement_id), terms_id uuid NOT NULL,
      action text NOT NULL CHECK(action IN ('PLAN_PUBLISHED','ACTIVATE','MENTOR_REVOKED','CANCEL')),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id), session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      auth_version integer NOT NULL, org_grant_id uuid NOT NULL REFERENCES flexbridge.org_role_grants(id),
      assignment_id uuid, idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(terms_id,placement_id) REFERENCES flexbridge.placement_terms(id,placement_id),
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.mentor_assignments(id,placement_id),
      UNIQUE(actor_id,idempotency_key), CHECK((action='MENTOR_REVOKED')=(assignment_id IS NOT NULL))
    );
    CREATE UNIQUE INDEX uq_placement_initial_activation ON flexbridge.placement_admission_events(placement_id) WHERE action='ACTIVATE';
    CREATE UNIQUE INDEX uq_placement_cancel ON flexbridge.placement_admission_events(placement_id) WHERE action='CANCEL';
    CREATE INDEX ix_placement_consent_terms ON flexbridge.placement_consents(placement_id,terms_id,side);

    CREATE FUNCTION flexbridge.placement_actor_current(actor uuid,sid uuid,version integer) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM users u JOIN sessions s ON s.user_id=u.id WHERE u.id=actor
        AND u.status='ACTIVE' AND u.auth_version=version AND s.id=sid AND s.auth_version=version
        AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp() AND (s.assurance='MFA' OR
          (NOT institution_sensitive_account(actor)
          AND NOT EXISTS(SELECT 1 FROM org_memberships m JOIN org_role_grants g ON g.membership_id=m.id
            JOIN role_catalog r ON r.id=g.role_id WHERE m.user_id=actor AND m.status='ACTIVE'
            AND m.revoked_at IS NULL AND g.revoked_at IS NULL AND r.scope_kind='ORG'
            AND r.code IN ('OWNER','BILLING','COORDINATOR','MODERATOR','SUPPORT','FINANCE','ADMIN'))
          AND NOT EXISTS(SELECT 1 FROM platform_role_grants g JOIN role_catalog r ON r.id=g.role_id
            WHERE g.user_id=actor AND g.revoked_at IS NULL AND g.expires_at>clock_timestamp()
            AND r.scope_kind='PLATFORM' AND r.code IN ('OWNER','BILLING','COORDINATOR','MODERATOR','SUPPORT','FINANCE','ADMIN')))))
    $$;
    CREATE FUNCTION flexbridge.placement_host_grant(actor uuid,org uuid,grant_id uuid) RETURNS boolean
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM org_role_grants g JOIN org_memberships m ON m.id=g.membership_id
        JOIN role_catalog r ON r.id=g.role_id WHERE g.id=grant_id AND g.revoked_at IS NULL
        AND m.user_id=actor AND m.organization_id=org AND m.status='ACTIVE' AND m.revoked_at IS NULL
        AND r.scope_kind='ORG' AND r.code IN ('OWNER','HOST_COORDINATOR'))
    $$;
    CREATE FUNCTION flexbridge.placement_host_capable(org uuid) RETURNS boolean
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM organizations o JOIN organization_capabilities c ON c.organization_id=o.id
        JOIN verification_cases v ON v.id=c.approved_case_id WHERE o.id=org AND o.status='VERIFIED'
        AND c.capability='INTERNSHIP_HOST' AND c.status='ACTIVE' AND v.organization_id=o.id
        AND v.kind=c.capability AND v.status='APPROVED' AND v.assigned_reviewer_id IS NOT NULL
        AND v.assigned_reviewer_id<>v.requester_id)
    $$;
    CREATE FUNCTION flexbridge.guard_placement_intake() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN RAISE EXCEPTION 'placement legacy set is closed' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS(SELECT 1 FROM placements p JOIN offers o ON o.id=p.offer_id
        JOIN applications a ON a.id=p.application_id JOIN application_attempts t ON t.id=o.attempt_id
        JOIN opportunity_revisions r ON r.id=o.revision_id JOIN opportunities v ON v.id=r.opportunity_id
        WHERE p.id=NEW.placement_id AND p.status='PLANNED' AND NOT p.academic_track
          AND p.enrollment_id IS NULL AND o.id=NEW.offer_id AND t.id=NEW.attempt_id AND r.id=NEW.revision_id
          AND o.application_id=a.id AND t.application_id=a.id AND t.opportunity_id=a.opportunity_id
          AND t.revision_id=r.id AND r.opportunity_id=a.opportunity_id
          AND a.candidate_id=p.candidate_id AND v.organization_id=p.organization_id
          AND v.kind='INTERNSHIP' AND r.contract_type IN ('INTERNSHIP_AGREEMENT','ACADEMIC_TRIPARTITE')
          AND NEW.academic_required=(r.contract_type='ACADEMIC_TRIPARTITE') AND o.status='ACCEPTED'
          AND o.accepted_at IS NOT NULL AND o.accepted_at<=o.expires_at
          AND NEW.initial_snapshot=to_jsonb(p)
          AND NEW.source_snapshot=jsonb_build_object('offer',to_jsonb(o),'application',to_jsonb(a),'attempt',to_jsonb(t),'revision',to_jsonb(r))
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND placement_host_grant(NEW.actor_id,p.organization_id,NEW.host_grant_id)
          AND placement_host_capable(p.organization_id))
      THEN RAISE EXCEPTION 'placement intake requires exact accepted internship and current host proof' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_placement_intake BEFORE INSERT ON flexbridge.placement_intakes
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_intake();

    CREATE FUNCTION flexbridge.guard_mentor_nomination_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN RAISE EXCEPTION 'mentor legacy set is closed' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS(SELECT 1 FROM mentor_assignments a JOIN placements p ON p.id=a.placement_id
        JOIN candidate_profiles c ON c.id=p.candidate_id JOIN org_memberships m ON m.id=a.membership_id
        JOIN users u ON u.id=m.user_id JOIN org_role_grants g ON g.membership_id=m.id
        JOIN role_catalog r ON r.id=g.role_id WHERE a.id=NEW.assignment_id AND p.id=NEW.placement_id
          AND a.organization_id=p.organization_id AND m.organization_id=p.organization_id
          AND m.user_id=NEW.mentor_user_id AND m.user_id<>c.user_id AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND u.status='ACTIVE' AND g.id=NEW.mentor_grant_id AND g.revoked_at IS NULL
          AND r.code='MENTOR' AND r.scope_kind='ORG' AND a.assigned_by_id=NEW.actor_id
          AND a.accepted_at IS NULL AND a.revoked_at IS NULL AND NEW.initial_snapshot=to_jsonb(a)
          AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE')
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND placement_host_grant(NEW.actor_id,p.organization_id,NEW.host_grant_id)
          AND placement_host_capable(p.organization_id))
      THEN RAISE EXCEPTION 'mentor nomination requires original current mentor grant and host proof' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_mentor_nomination_proof BEFORE INSERT ON flexbridge.mentor_assignment_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_mentor_nomination_proof();

    CREATE FUNCTION flexbridge.guard_placement_consent() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE p placements; BEGIN
      SELECT * INTO p FROM placements WHERE id=NEW.placement_id FOR UPDATE;
      IF p.current_terms_id IS DISTINCT FROM NEW.terms_id OR p.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE')
        OR NOT placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
      THEN RAISE EXCEPTION 'consent requires current actor and exact current terms' USING ERRCODE='23514'; END IF;
      IF NEW.side='CANDIDATE' THEN
        IF NOT EXISTS(SELECT 1 FROM candidate_profiles c WHERE c.id=p.candidate_id AND c.user_id=NEW.actor_id)
        THEN RAISE EXCEPTION 'candidate consent is personal' USING ERRCODE='23514'; END IF;
      ELSIF NEW.side='HOST' THEN
        IF NOT placement_host_grant(NEW.actor_id,p.organization_id,NEW.org_grant_id)
          OR EXISTS(SELECT 1 FROM candidate_profiles c WHERE c.id=p.candidate_id AND c.user_id=NEW.actor_id)
        THEN RAISE EXCEPTION 'host consent requires independent host authority' USING ERRCODE='23514'; END IF;
      ELSE
        IF NOT EXISTS(SELECT 1 FROM mentor_assignment_proofs q JOIN mentor_assignments a ON a.id=q.assignment_id
          JOIN org_role_grants g ON g.id=q.mentor_grant_id JOIN org_memberships m ON m.id=a.membership_id
          JOIN role_catalog r ON r.id=g.role_id JOIN candidate_profiles c ON c.id=p.candidate_id
          WHERE a.id=NEW.assignment_id AND a.placement_id=p.id AND a.organization_id=p.organization_id
            AND q.mentor_user_id=NEW.actor_id AND q.mentor_grant_id=NEW.org_grant_id AND g.revoked_at IS NULL
            AND m.id=g.membership_id AND m.user_id=NEW.actor_id AND m.organization_id=p.organization_id
            AND m.status='ACTIVE' AND m.revoked_at IS NULL AND r.scope_kind='ORG' AND r.code='MENTOR'
            AND a.revoked_at IS NULL AND c.user_id<>NEW.actor_id)
        THEN RAISE EXCEPTION 'mentor consent requires personal original current grant' USING ERRCODE='23514'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_placement_consent BEFORE INSERT ON flexbridge.placement_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_consent();

    CREATE FUNCTION flexbridge.placement_ready_for_start(pid uuid,tid uuid) RETURNS boolean
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM placements p JOIN placement_intakes i ON i.placement_id=p.id
        JOIN offers o ON o.id=i.offer_id JOIN opportunity_revisions r ON r.id=i.revision_id
        JOIN applications app ON app.id=p.application_id JOIN application_attempts t ON t.id=i.attempt_id
        JOIN opportunities v ON v.id=r.opportunity_id JOIN candidate_profiles c ON c.id=p.candidate_id
        WHERE p.id=pid AND p.current_terms_id=tid AND NOT i.academic_required AND NOT p.academic_track
          AND v.kind='INTERNSHIP' AND r.contract_type='INTERNSHIP_AGREEMENT'
          AND o.id=p.offer_id AND o.application_id=p.application_id AND v.organization_id=p.organization_id
          AND o.revision_id=r.id AND o.attempt_id=t.id AND t.application_id=app.id
          AND t.revision_id=r.id AND t.opportunity_id=app.opportunity_id AND r.opportunity_id=app.opportunity_id
          AND app.candidate_id=p.candidate_id
          AND EXISTS(SELECT 1 FROM placement_consents x WHERE x.placement_id=p.id AND x.terms_id=tid
            AND x.side='CANDIDATE' AND x.actor_id=c.user_id)
          AND EXISTS(SELECT 1 FROM placement_consents x JOIN mentor_assignments a ON a.id=x.assignment_id
            JOIN mentor_assignment_proofs q ON q.assignment_id=a.id JOIN org_memberships m ON m.id=a.membership_id
            JOIN org_role_grants g ON g.id=q.mentor_grant_id JOIN role_catalog z ON z.id=g.role_id
            JOIN users u ON u.id=m.user_id WHERE x.placement_id=p.id AND x.terms_id=tid AND x.side='MENTOR'
              AND a.placement_id=p.id AND a.accepted_at IS NOT NULL AND a.revoked_at IS NULL
              AND m.id=g.membership_id AND m.organization_id=p.organization_id AND m.user_id=x.actor_id
              AND m.status='ACTIVE' AND m.revoked_at IS NULL AND u.status='ACTIVE' AND m.user_id<>c.user_id
              AND g.revoked_at IS NULL AND g.id=x.org_grant_id AND q.mentor_user_id=x.actor_id
              AND z.scope_kind='ORG' AND z.code='MENTOR'))
    $$;
    CREATE FUNCTION flexbridge.guard_placement_admission_event() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ DECLARE p placements; BEGIN
      SELECT * INTO p FROM placements WHERE id=NEW.placement_id FOR UPDATE;
      IF p.current_terms_id IS DISTINCT FROM NEW.terms_id
        OR NOT placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
        OR NOT placement_host_grant(NEW.actor_id,p.organization_id,NEW.org_grant_id)
        OR NOT placement_host_capable(p.organization_id)
        OR EXISTS(SELECT 1 FROM candidate_profiles c WHERE c.id=p.candidate_id AND c.user_id=NEW.actor_id)
      THEN RAISE EXCEPTION 'admission event requires exact terms and current independent host' USING ERRCODE='23514'; END IF;
      IF NEW.action='ACTIVATE' AND (p.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION')
        OR NOT placement_ready_for_start(p.id,NEW.terms_id)
        OR NOT EXISTS(SELECT 1 FROM placement_consents x WHERE x.placement_id=p.id AND x.terms_id=NEW.terms_id
          AND x.side='HOST' AND x.actor_id=NEW.actor_id AND x.org_grant_id=NEW.org_grant_id))
      THEN RAISE EXCEPTION 'activation requires exact candidate, mentor and host consent' USING ERRCODE='23514'; END IF;
      IF (NEW.action='PLAN_PUBLISHED' AND p.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION'))
        OR (NEW.action='CANCEL' AND p.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE'))
      THEN RAISE EXCEPTION 'admission event is not valid for placement state' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_placement_admission_event BEFORE INSERT ON flexbridge.placement_admission_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_admission_event();

    CREATE FUNCTION flexbridge.guard_placement_terms_history() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'placement plan history is immutable' USING ERRCODE='23514'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.candidate_accepted_at IS NOT NULL OR NEW.host_accepted_at IS NOT NULL
        THEN RAISE EXCEPTION 'new terms cannot invent acceptance' USING ERRCODE='23514'; END IF;
        IF NOT EXISTS(SELECT 1 FROM placements p WHERE p.id=NEW.placement_id
          AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION'))
        THEN RAISE EXCEPTION 'active plan amendment requires a separate lifecycle' USING ERRCODE='23514'; END IF;
        RETURN NEW;
      END IF;
      IF (to_jsonb(NEW)-ARRAY['updated_at','candidate_accepted_at','host_accepted_at'])
        IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['updated_at','candidate_accepted_at','host_accepted_at'])
      THEN RAISE EXCEPTION 'placement plan content is immutable' USING ERRCODE='23514'; END IF;
      IF NEW.candidate_accepted_at IS DISTINCT FROM OLD.candidate_accepted_at AND
        (OLD.candidate_accepted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM placement_consents x
          WHERE x.terms_id=NEW.id AND x.side='CANDIDATE' AND x.created_at=NEW.candidate_accepted_at))
      THEN RAISE EXCEPTION 'candidate acceptance requires personal evidence' USING ERRCODE='23514'; END IF;
      IF NEW.host_accepted_at IS DISTINCT FROM OLD.host_accepted_at AND
        (OLD.host_accepted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM placement_consents x
          WHERE x.terms_id=NEW.id AND x.side='HOST' AND x.created_at=NEW.host_accepted_at))
      THEN RAISE EXCEPTION 'host acceptance requires personal evidence' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_placement_terms_history BEFORE INSERT OR UPDATE OR DELETE ON flexbridge.placement_terms
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_terms_history();
    CREATE TRIGGER immutable_plan_tasks BEFORE UPDATE OR DELETE ON flexbridge.plan_tasks
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE FUNCTION flexbridge.guard_plan_task_insert() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ DECLARE pid uuid; BEGIN
      SELECT p.id INTO pid FROM placements p JOIN placement_terms t ON t.placement_id=p.id
        WHERE t.id=NEW.terms_id AND p.current_terms_id=t.id
          AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION') FOR UPDATE OF p;
      IF pid IS NULL THEN RAISE EXCEPTION 'superseded or active plan tasks are immutable' USING ERRCODE='23514'; END IF;
      IF EXISTS(SELECT 1 FROM placement_consents c WHERE c.terms_id=NEW.terms_id)
        OR EXISTS(SELECT 1 FROM placement_admission_events e WHERE e.terms_id=NEW.terms_id AND e.action='PLAN_PUBLISHED')
      THEN RAISE EXCEPTION 'published plan tasks are immutable' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_plan_task_insert BEFORE INSERT ON flexbridge.plan_tasks
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_plan_task_insert();

    CREATE FUNCTION flexbridge.guard_placement_start() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'PLANNED' OR NEW.academic_track OR NEW.enrollment_id IS NOT NULL
        THEN RAISE EXCEPTION 'new placement requires planned intake' USING ERRCODE='23514'; END IF;
      ELSE
        IF NEW.status='ACTIVE' AND OLD.status<>'ACTIVE' AND
          (OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION')
            OR NOT placement_ready_for_start(NEW.id,NEW.current_terms_id) OR NOT EXISTS(
            SELECT 1 FROM placement_admission_events e WHERE e.placement_id=NEW.id
              AND e.terms_id=NEW.current_terms_id AND e.action='ACTIVATE'))
        THEN RAISE EXCEPTION 'placement start requires immutable admission proof' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.application_id,NEW.offer_id,NEW.candidate_id,NEW.organization_id,NEW.start_date,NEW.end_date)
          IS DISTINCT FROM ROW(OLD.application_id,OLD.offer_id,OLD.candidate_id,OLD.organization_id,OLD.start_date,OLD.end_date)
        THEN RAISE EXCEPTION 'placement source and dates are immutable' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.academic_track,NEW.enrollment_id) IS DISTINCT FROM ROW(OLD.academic_track,OLD.enrollment_id)
        THEN RAISE EXCEPTION 'academic binding requires admission proof' USING ERRCODE='23514'; END IF;
        IF NEW.current_terms_id IS DISTINCT FROM OLD.current_terms_id AND OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION')
        THEN RAISE EXCEPTION 'active plan amendment requires a separate lifecycle' USING ERRCODE='23514'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_placement_start BEFORE INSERT OR UPDATE ON flexbridge.placements
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_start();
    CREATE FUNCTION flexbridge.guard_mentor_assignment_history() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'mentor assignment history is immutable' USING ERRCODE='23514'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.accepted_at IS NOT NULL OR NEW.revoked_at IS NOT NULL
        THEN RAISE EXCEPTION 'new nomination cannot invent acceptance' USING ERRCODE='23514'; END IF;
        RETURN NEW;
      END IF;
      IF (to_jsonb(NEW)-ARRAY['updated_at','accepted_at','revoked_at'])
        IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['updated_at','accepted_at','revoked_at'])
      THEN RAISE EXCEPTION 'mentor nomination is immutable' USING ERRCODE='23514'; END IF;
      IF NEW.accepted_at IS DISTINCT FROM OLD.accepted_at AND
        (OLD.accepted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM placement_consents x
          WHERE x.assignment_id=NEW.id AND x.side='MENTOR' AND x.created_at=NEW.accepted_at))
      THEN RAISE EXCEPTION 'mentor acceptance requires personal evidence' USING ERRCODE='23514'; END IF;
      IF NEW.revoked_at IS DISTINCT FROM OLD.revoked_at AND
        (OLD.revoked_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM placement_admission_events x
          WHERE x.assignment_id=NEW.id AND x.action='MENTOR_REVOKED' AND x.created_at=NEW.revoked_at))
      THEN RAISE EXCEPTION 'mentor revocation requires host evidence' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_mentor_assignment_history BEFORE INSERT OR UPDATE OR DELETE ON flexbridge.mentor_assignments
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_mentor_assignment_history();
    CREATE TRIGGER immutable_placement_intakes BEFORE UPDATE OR DELETE ON flexbridge.placement_intakes
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_mentor_assignment_proofs BEFORE UPDATE OR DELETE ON flexbridge.mentor_assignment_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_placement_consents BEFORE UPDATE OR DELETE ON flexbridge.placement_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_placement_admission_events BEFORE UPDATE OR DELETE ON flexbridge.placement_admission_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    """)


def downgrade():
    raise RuntimeError('Admission evidence/history needs a reviewed data-preserving rollback plan')
