"""Durable, immutable-history administration proofs for DB-092 feature flags (API-121 / CAP-037).

Draft: forward from 0016 only. Existing canonical feature_flags rows are captured verbatim as
LEGACY_IMPORT with no fabricated actor, session, grant or event. Legacy values never become certified
enablement; only append-only PUBLIC change events created by a current MFA ADMIN with an expiring
platform grant can. SQL deliberately avoids colons and percent signs because op.execute() wraps strings
in text().
"""
from alembic import op

revision = '0017_feature_flag_administration'
down_revision = '0016_academic_reviews'
branch_labels = depends_on = None

CATALOG = ("('R1_PART_TIME_JOBS','R1_GENERAL_INTERNSHIPS','R1_ACADEMIC_INTERNSHIPS','ratings',"
           "'academic_official_export','WhatsApp','paid_checkout','R2_FREELANCE_MARKETPLACE')")
LOCKED = "('ratings','academic_official_export','WhatsApp','paid_checkout','R2_FREELANCE_MARKETPLACE')"
ENABLEABLE = "('R1_PART_TIME_JOBS','R1_GENERAL_INTERNSHIPS','R1_ACADEMIC_INTERNSHIPS')"
SERVER_SCHEMA = "jsonb_build_object('schema_version',1,'scope','GLOBAL')"


def sql(text):
    return (text.replace('@CATALOG@', CATALOG).replace('@LOCKED@', LOCKED)
            .replace('@ENABLEABLE@', ENABLEABLE).replace('@SCHEMA@', SERVER_SCHEMA))


def upgrade():
    # 1. Tables and stable helper functions (capture needs the UTC snapshot function).
    op.execute(sql("""
    CREATE TABLE flexbridge.feature_flag_origins (
      flag_id uuid PRIMARY KEY REFERENCES flexbridge.feature_flags(id),
      code text NOT NULL UNIQUE,
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE flexbridge.feature_flag_change_events (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      flag_id uuid NOT NULL REFERENCES flexbridge.feature_flags(id),
      code text NOT NULL CHECK(code IN @CATALOG@),
      version integer NOT NULL CHECK(version>=1),
      prior_event_id uuid REFERENCES flexbridge.feature_flag_change_events(id),
      enabled boolean NOT NULL,
      rule_schema jsonb NOT NULL CHECK(rule_schema=@SCHEMA@),
      reason text NOT NULL CHECK(length(reason) BETWEEN 15 AND 2000 AND reason=btrim(reason)),
      before_snapshot jsonb CHECK(before_snapshot IS NULL OR jsonb_typeof(before_snapshot)='object'),
      after_snapshot jsonb NOT NULL CHECK(jsonb_typeof(after_snapshot)='object'),
      before_digest text CHECK(before_digest IS NULL OR before_digest ~ '^[0-9a-f]{64}$'),
      after_digest text NOT NULL CHECK(after_digest ~ '^[0-9a-f]{64}$'),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      auth_version integer NOT NULL,
      admin_grant_id uuid NOT NULL REFERENCES flexbridge.platform_role_grants(id),
      decided_at timestamptz NOT NULL,
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      audit_event_id uuid NOT NULL UNIQUE REFERENCES flexbridge.audit_events(id),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      UNIQUE(actor_id,idempotency_key), UNIQUE(flag_id,version), UNIQUE(prior_event_id),
      CONSTRAINT feature_flag_event_chain CHECK(
        (version=1 AND prior_event_id IS NULL) OR (version>1 AND prior_event_id IS NOT NULL
          AND before_snapshot IS NOT NULL)),
      CONSTRAINT feature_flag_event_digest_pair CHECK((before_snapshot IS NULL)=(before_digest IS NULL)),
      CONSTRAINT feature_flag_locked_enable CHECK(NOT(enabled AND code IN @LOCKED@))
    );

    -- Stable UTC rendering: never depends on the connection TimeZone.
    CREATE FUNCTION flexbridge.feature_flag_snapshot(f flexbridge.feature_flags) RETURNS jsonb
    LANGUAGE sql STABLE SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$ SELECT to_jsonb(f) $$;
    CREATE FUNCTION flexbridge.feature_flag_digest(value jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT encode(sha256(convert_to(CAST(value AS text),'UTF8')),'hex') $$;
    CREATE FUNCTION flexbridge.feature_flag_state_valid(f flexbridge.feature_flags) RETURNS boolean
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT f.code IN @CATALOG@ AND f.rule_schema=@SCHEMA@ AND NOT(f.enabled AND f.code IN @LOCKED@)
        AND length(f.reason) BETWEEN 15 AND 2000 AND f.reason=btrim(f.reason) $$;

    -- Preserve exactly what existed. No actor/session/grant/event is manufactured and legacy
    -- enabled=true values stay unproved. Capture closes immediately below.
    INSERT INTO flexbridge.feature_flag_origins(flag_id,code,origin,initial_snapshot)
      SELECT f.id,f.code,'LEGACY_IMPORT',flexbridge.feature_flag_snapshot(f) FROM flexbridge.feature_flags f;
    """))

    # 2. Current-authority predicate shared by the BEFORE guard and the commit-time recheck.
    op.execute(sql("""
    CREATE FUNCTION flexbridge.feature_flag_admin_current(actor uuid,sid uuid,version integer,
      grant_id uuid,decided timestamptz) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM users u JOIN sessions s ON s.user_id=u.id
        JOIN platform_role_grants g ON g.user_id=u.id JOIN role_catalog r ON r.id=g.role_id
        WHERE u.id=actor AND u.status='ACTIVE' AND u.auth_version=version AND s.id=sid
          AND s.auth_version=version AND s.revoked_at IS NULL AND s.assurance='MFA'
          AND s.expires_at>clock_timestamp() AND s.expires_at>decided
          AND g.id=grant_id AND g.revoked_at IS NULL AND g.expires_at>clock_timestamp()
          AND g.expires_at>decided AND g.granted_by_id<>g.user_id
          AND r.code='ADMIN' AND r.scope_kind='PLATFORM')
    $$;
    """))

    # 3. Canonical row guard: no delete, no identity change, only valid server-owned states.
    op.execute(sql("""
    CREATE FUNCTION flexbridge.guard_feature_flag_row() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'feature flag rows cannot be deleted' USING ERRCODE='23514';
      END IF;
      IF TG_OP='UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.code IS DISTINCT FROM OLD.code
           OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
          RAISE EXCEPTION 'feature flag identity is immutable' USING ERRCODE='23514';
        END IF;
        IF NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
      END IF;
      IF NEW.enabled AND NEW.code IN @LOCKED@ THEN
        RAISE EXCEPTION 'feature flag is locked in R1' USING ERRCODE='23514';
      END IF;
      IF NOT flexbridge.feature_flag_state_valid(NEW) THEN
        RAISE EXCEPTION 'feature flag state is not a valid server-owned state' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_feature_flag_row BEFORE INSERT OR UPDATE OR DELETE ON flexbridge.feature_flags
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_feature_flag_row();

    -- Deferred equality: every written canonical row must equal its latest proof event (or, for a
    -- captured legacy row without events, its untouched initial snapshot) when the transaction commits.
    CREATE FUNCTION flexbridge.require_feature_flag_state_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE
      cur flexbridge.feature_flags;
      origin_row flexbridge.feature_flag_origins;
      latest flexbridge.feature_flag_change_events;
    BEGIN
      SELECT * INTO cur FROM flexbridge.feature_flags WHERE id=NEW.id;
      IF NOT FOUND THEN RETURN NULL; END IF;
      SELECT * INTO origin_row FROM flexbridge.feature_flag_origins WHERE flag_id=cur.id;
      IF NOT FOUND OR origin_row.code IS DISTINCT FROM cur.code THEN
        RAISE EXCEPTION 'feature flag requires an immutable origin' USING ERRCODE='23514';
      END IF;
      SELECT * INTO latest FROM flexbridge.feature_flag_change_events
        WHERE flag_id=cur.id ORDER BY version DESC LIMIT 1;
      IF FOUND THEN
        IF flexbridge.feature_flag_snapshot(cur) IS DISTINCT FROM latest.after_snapshot THEN
          RAISE EXCEPTION 'feature flag state requires its latest proof event' USING ERRCODE='23514';
        END IF;
      ELSIF origin_row.origin<>'LEGACY_IMPORT'
         OR flexbridge.feature_flag_snapshot(cur) IS DISTINCT FROM origin_row.initial_snapshot THEN
        RAISE EXCEPTION 'feature flag state is unproved' USING ERRCODE='23514';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER feature_flag_state_requires_proof AFTER INSERT OR UPDATE ON flexbridge.feature_flags
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_feature_flag_state_proof();
    """))

    # 4. Origins: capture is closed; a new PUBLIC origin needs its first event at commit.
    op.execute(sql("""
    CREATE FUNCTION flexbridge.guard_feature_flag_origin() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE cur flexbridge.feature_flags;
    BEGIN
      IF NEW.origin<>'PUBLIC' THEN
        RAISE EXCEPTION 'feature flag legacy set is closed' USING ERRCODE='23514';
      END IF;
      SELECT * INTO cur FROM flexbridge.feature_flags WHERE id=NEW.flag_id;
      IF NOT FOUND OR cur.code IS DISTINCT FROM NEW.code
         OR flexbridge.feature_flag_snapshot(cur) IS DISTINCT FROM NEW.initial_snapshot THEN
        RAISE EXCEPTION 'feature flag origin must preserve the exact initial canonical snapshot'
          USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_feature_flag_origin BEFORE INSERT ON flexbridge.feature_flag_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_feature_flag_origin();
    CREATE FUNCTION flexbridge.require_feature_flag_origin_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM flexbridge.feature_flag_change_events e WHERE e.flag_id=NEW.flag_id
        AND e.version=1 AND e.before_snapshot IS NULL AND e.after_snapshot=NEW.initial_snapshot) THEN
        RAISE EXCEPTION 'feature flag origin requires its first proof event' USING ERRCODE='23514';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER feature_flag_origin_requires_event AFTER INSERT ON flexbridge.feature_flag_origins
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_feature_flag_origin_proof();
    """))

    # 5. Events: exact current ADMIN proof, chain, canonical equality, same-transaction audit, exact receipt.
    op.execute(sql("""
    CREATE FUNCTION flexbridge.stamp_feature_flag_audit_event() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.action='FEATURE_FLAG_ADMINISTERED' THEN
        NEW.scope_snapshot = (CASE
          WHEN NEW.scope_snapshot IS NOT NULL AND jsonb_typeof(NEW.scope_snapshot)='object'
          THEN NEW.scope_snapshot
          ELSE jsonb_build_object()
        END) || jsonb_build_object('_feature_flag_top_xid',CAST(pg_current_xact_id() AS text));
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER stamp_feature_flag_audit_event BEFORE INSERT ON flexbridge.audit_events
      FOR EACH ROW WHEN (NEW.action='FEATURE_FLAG_ADMINISTERED')
      EXECUTE FUNCTION flexbridge.stamp_feature_flag_audit_event();

    CREATE FUNCTION flexbridge.guard_feature_flag_change_event() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE
      cur flexbridge.feature_flags;
      origin_row flexbridge.feature_flag_origins;
      prior flexbridge.feature_flag_change_events;
    BEGIN
      IF NOT flexbridge.feature_flag_admin_current(NEW.actor_id,NEW.session_id,NEW.auth_version,
           NEW.admin_grant_id,NEW.decided_at) OR NEW.decided_at>clock_timestamp() THEN
        RAISE EXCEPTION 'feature flag change requires current ADMIN authority' USING ERRCODE='23514';
      END IF;
      SELECT * INTO cur FROM flexbridge.feature_flags WHERE id=NEW.flag_id;
      IF NOT FOUND OR cur.code IS DISTINCT FROM NEW.code OR cur.enabled IS DISTINCT FROM NEW.enabled
         OR cur.rule_schema IS DISTINCT FROM NEW.rule_schema OR cur.reason IS DISTINCT FROM NEW.reason
         OR cur.changed_by_id IS DISTINCT FROM NEW.actor_id OR NOT flexbridge.feature_flag_state_valid(cur)
         OR flexbridge.feature_flag_snapshot(cur) IS DISTINCT FROM NEW.after_snapshot
         OR flexbridge.feature_flag_digest(NEW.after_snapshot) IS DISTINCT FROM NEW.after_digest THEN
        RAISE EXCEPTION 'feature flag event must equal the canonical flag state' USING ERRCODE='23514';
      END IF;
      SELECT * INTO origin_row FROM flexbridge.feature_flag_origins WHERE flag_id=NEW.flag_id;
      IF NOT FOUND OR origin_row.code IS DISTINCT FROM NEW.code THEN
        RAISE EXCEPTION 'feature flag event requires an immutable origin' USING ERRCODE='23514';
      END IF;
      IF NEW.version=1 THEN
        IF origin_row.origin='LEGACY_IMPORT' THEN
          IF NEW.before_snapshot IS DISTINCT FROM origin_row.initial_snapshot
             OR NEW.before_digest IS DISTINCT FROM flexbridge.feature_flag_digest(origin_row.initial_snapshot) THEN
            RAISE EXCEPTION 'feature flag first event must start from the legacy snapshot' USING ERRCODE='23514';
          END IF;
        ELSIF NEW.before_snapshot IS NOT NULL OR NEW.after_snapshot IS DISTINCT FROM origin_row.initial_snapshot THEN
          RAISE EXCEPTION 'feature flag first event must match its public origin' USING ERRCODE='23514';
        END IF;
      ELSE
        SELECT * INTO prior FROM flexbridge.feature_flag_change_events WHERE id=NEW.prior_event_id;
        IF NOT FOUND OR prior.flag_id<>NEW.flag_id OR prior.version<>NEW.version-1
           OR NEW.before_snapshot IS DISTINCT FROM prior.after_snapshot
           OR NEW.before_digest IS DISTINCT FROM prior.after_digest THEN
          RAISE EXCEPTION 'feature flag event must extend the previous version' USING ERRCODE='23514';
        END IF;
      END IF;
      IF NOT EXISTS(SELECT 1 FROM flexbridge.audit_events a WHERE a.id=NEW.audit_event_id
        AND a.actor_id=NEW.actor_id AND a.action='FEATURE_FLAG_ADMINISTERED'
        AND a.object_type='feature_flag' AND a.object_key=CAST(NEW.flag_id AS text)
        AND a.scope_snapshot->>'event_id'=CAST(NEW.id AS text) AND a.scope_snapshot->>'source'='API-121'
        AND a.scope_snapshot->>'code'=NEW.code AND a.scope_snapshot->'version'=to_jsonb(NEW.version)
        AND a.scope_snapshot->>'_feature_flag_top_xid'=CAST(pg_current_xact_id() AS text)) THEN
        RAISE EXCEPTION 'feature flag event requires its same-transaction audit event' USING ERRCODE='23514';
      END IF;
      IF NEW.receipt-'decided_at' IS DISTINCT FROM jsonb_build_object('flag_id',NEW.flag_id,
           'event_id',NEW.id,'audit_event_id',NEW.audit_event_id,'code',NEW.code,'enabled',NEW.enabled,
           'effective_enabled',(NEW.enabled AND NEW.code IN @ENABLEABLE@),'version',NEW.version,
           'reason',NEW.reason)
         OR CAST(NEW.receipt->>'decided_at' AS timestamptz) IS DISTINCT FROM NEW.decided_at THEN
        RAISE EXCEPTION 'feature flag event requires the exact minimal receipt' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_feature_flag_change_event BEFORE INSERT ON flexbridge.feature_flag_change_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_feature_flag_change_event();

    -- Authority is pinned to commit: re-evaluate the same clock-current predicate and canonical equality.
    CREATE FUNCTION flexbridge.require_feature_flag_event_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT flexbridge.feature_flag_admin_current(NEW.actor_id,NEW.session_id,NEW.auth_version,
           NEW.admin_grant_id,NEW.decided_at) THEN
        RAISE EXCEPTION 'feature flag change requires current ADMIN authority at commit' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM flexbridge.feature_flag_origins o WHERE o.flag_id=NEW.flag_id) THEN
        RAISE EXCEPTION 'feature flag event requires an immutable origin' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM flexbridge.feature_flag_change_events later
           WHERE later.flag_id=NEW.flag_id AND later.version>NEW.version)
         AND NOT EXISTS(SELECT 1 FROM flexbridge.feature_flags f WHERE f.id=NEW.flag_id
           AND flexbridge.feature_flag_snapshot(f)=NEW.after_snapshot) THEN
        RAISE EXCEPTION 'feature flag state differs from its latest proof event' USING ERRCODE='23514';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER feature_flag_event_current_at_commit AFTER INSERT ON flexbridge.feature_flag_change_events
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_feature_flag_event_proof();

    CREATE TRIGGER immutable_feature_flag_origins BEFORE UPDATE OR DELETE ON flexbridge.feature_flag_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_feature_flag_change_events BEFORE UPDATE OR DELETE ON flexbridge.feature_flag_change_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    """))


def downgrade():
    raise RuntimeError('Feature flag history needs a reviewed data-preserving rollback plan')
