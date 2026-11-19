### Summary (AGY-005 / Issue 72)

Updated [0017_feature_flag_administration.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/alembic/versions/0017_feature_flag_administration.py#L188-L252) to make same-transaction audit binding savepoint-safe without weakening database-enforced transaction identity or append-only audit integrity:

1. **DB-owned top-XID stamping (`flexbridge.stamp_feature_flag_audit_event`)**:
   - Added a `BEFORE INSERT` trigger on `flexbridge.audit_events` scoped via `WHEN (NEW.action='FEATURE_FLAG_ADMINISTERED')` (and guarded inside the function).
   - Unconditionally merges `jsonb_build_object('_feature_flag_top_xid', CAST(pg_current_xact_id() AS text))` onto `NEW.scope_snapshot` (normalizing non-object/NULL `scope_snapshot` to `{}` first so `||` performs JSONB object key overwrite), overriding any caller-supplied `_feature_flag_top_xid` while preserving all other metadata keys and leaving all other audit actions untouched.
2. **Savepoint-safe event guard (`flexbridge.guard_feature_flag_change_event`)**:
   - Replaced `CAST(CAST(a.xmin AS text) AS bigint)=mod(txid_current(),4294967296)` with `a.scope_snapshot->>'_feature_flag_top_xid'=CAST(pg_current_xact_id() AS text)`.
   - Uses `CAST(... AS text)` and PL/pgSQL `=` assignment to maintain the file invariant of zero colons (`:`) or percent signs (`%`) inside `op.execute()` strings.
   - Retains all existing actor, action, object, `event_id`, `source`, `code`, `version`, canonical snapshot/digest, chain, receipt, legacy capture, PUBLIC origin, and deferred commit-time authority checks.

### Actual Diff

```diff
--- a/backend/alembic/versions/0017_feature_flag_administration.py
+++ b/backend/alembic/versions/0017_feature_flag_administration.py
@@ -187,6 +187,21 @@ def upgrade():

     # 5. Events: exact current ADMIN proof, chain, canonical equality, same-transaction audit, exact receipt.
     op.execute(sql("""
+    CREATE FUNCTION flexbridge.stamp_feature_flag_audit_event() RETURNS trigger
+    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
+      IF NEW.action='FEATURE_FLAG_ADMINISTERED' THEN
+        NEW.scope_snapshot = (CASE
+          WHEN NEW.scope_snapshot IS NOT NULL AND jsonb_typeof(NEW.scope_snapshot)='object'
+          THEN NEW.scope_snapshot
+          ELSE jsonb_build_object()
+        END) || jsonb_build_object('_feature_flag_top_xid',CAST(pg_current_xact_id() AS text));
+      END IF;
+      RETURN NEW;
+    END $$;
+    CREATE TRIGGER stamp_feature_flag_audit_event BEFORE INSERT ON flexbridge.audit_events
+      FOR EACH ROW WHEN (NEW.action='FEATURE_FLAG_ADMINISTERED')
+      EXECUTE FUNCTION flexbridge.stamp_feature_flag_audit_event();
+
     CREATE FUNCTION flexbridge.guard_feature_flag_change_event() RETURNS trigger
     LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
     DECLARE
@@ -232,7 +247,7 @@ def upgrade():
         AND a.object_type='feature_flag' AND a.object_key=CAST(NEW.flag_id AS text)
         AND a.scope_snapshot->>'event_id'=CAST(NEW.id AS text) AND a.scope_snapshot->>'source'='API-121'
         AND a.scope_snapshot->>'code'=NEW.code AND a.scope_snapshot->'version'=to_jsonb(NEW.version)
-        AND CAST(CAST(a.xmin AS text) AS bigint)=mod(txid_current(),4294967296)) THEN
+        AND a.scope_snapshot->>'_feature_flag_top_xid'=CAST(pg_current_xact_id() AS text)) THEN
         RAISE EXCEPTION 'feature flag event requires its same-transaction audit event' USING ERRCODE='23514';
       END IF;
```

### Commands and Results

- `D:/FlexBridge/.venv/Scripts/python.exe -m py_compile backend/alembic/versions/0017_feature_flag_administration.py` → Exit code `0` (no output).
- No native PostgreSQL/pytest tests or Git mutations were executed.

### Remaining Risks

- **Native PostgreSQL verification pending**: Requires Codex's native test execution to confirm savepoint (`conn.begin_nested()`) success, outer rollback cleanup, rejection of prior-transaction `audit_events` rows, rejection of caller-forged `_feature_flag_top_xid`, and the full feature-flag suite against PostgreSQL 17.
- **Downstream whole-JSON equality**: Any external test asserting exact full-dict equality on raw `audit_events.scope_snapshot` for `FEATURE_FLAG_ADMINISTERED` will observe the DB-stamped `_feature_flag_top_xid` key.
