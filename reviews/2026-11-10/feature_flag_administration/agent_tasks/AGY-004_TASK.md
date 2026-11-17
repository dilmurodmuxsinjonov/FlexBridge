# AGY-004 / Issue72 - fix the actual first native failures (two owned files only)

You are not alone. MAIN/MASTER FROZEN764fb984; only integration/r1-agent-collaboration
may receive PRs/merges. Workspace D:/Codex/FlexBridge-agents/antigravity has now
fast-forwarded to accepted integratione5068a07bc4b94f9238883b80e817fd62cc6e709;
all11 agent/Codex WIP files were hash-preserved. Do NOT undo Codex shared wiring.

Actual AGY003 completed. Codex independently compiled and ran two real migrated
PostgreSQL/HTTP positives: both failed409 FEATURE_FLAG_PROOF_REJECTED (17.31s).
A direct bounded diagnostic (8.23s) exposed SQLSTATE23514:
"feature flag first event must match its public origin" in BEFORE event guard.
Cause: SQLAlchemy JSONB() serializes Python None as JSON null, not SQL NULL.
New PUBLIC before_snapshot must be SQL NULL, but the producer binds Python None.

OWN ONLY:
- backend/app/services/feature_flag_admin.py
- backend/tests/security/test_feature_flag_admin_api121.py
Other two AGY files, all Codex wiring and diagnostics are frozen for this task.

Fixes:
1. Produce actual SQL NULL for optional absent before_snapshot (e.g. sqlalchemy.null())
   when the previous row did not exist. Do not replace absence with {}, weaken
   schema/proof checks, add test flag-name exceptions or alter the migration.
2. Replace fresh_mfa_actor's directly inserted assurance=MFA session with a genuine
   auth_service.login using the actual fixture password and TOTP secret/code.
   Inspect actual login/TOTP behavior. If a fresh real code needs a new window,
   wait bounded real time; no fake assurance, monkeypatched clock or client MFA flag.
   A current session must come from actual server authentication, not hand-built rows.
3. Fix first test's audit snapshot: logout legitimately adds SESSION_REVOKED.
   It currently captures all audit rows before logout, then requires them unchanged
   after logout/replay. Preserve/check logout audit and require replay adds no flag
   proof/effect/audit; compare the appropriate post-logout baseline. Don't suppress audit.

Important source correction: backend/tests/test_s2_1_3_retention_flags.py is ACTIVE,
not archived. Actual collect-only on clean source found3 cases. Codex updated its
one obsolete R2-org-override test to real ADMIN HTTP/current durable reads/R2 denial;
the two retention cases and actual .txt archive remain untouched. Don't edit that file.

Shared storage/0017 head/router/private middleware/old RAM adapter/operations are
now wired by Codex, but no native flag case has passed yet. Syntax compile of
the two owned files is allowed. Do not run native tests in this task; Codex will
run the exact failed positive tests first, then broader cases. No Git mutations,
installs/.env/.data/credentials/live or provider actions. Return <=600 words with
exact changes and actual compilation result/remaining gaps, no claimed tests.
Controller uses Sonnet5.5High for this focused fix and actual-quota fallback only.
