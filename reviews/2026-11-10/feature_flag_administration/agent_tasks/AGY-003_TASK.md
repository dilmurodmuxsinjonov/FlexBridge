# AGY-003 / Issue72 - owned implementation draft, phase1

You are not alone. Codex reviewed AGY002. Main/master FROZEN764fb984; all future
PRs target integration/r1-agent-collaboration. Your workspace remains
D:/Codex/FlexBridge-agents/antigravity, branch agent/antigravity-r1 based on that
integration baseline. No Git/GitHub mutations, live/provider/pg_live actions,
credentials/.env/.data reads, dependency installs or edits outside ownership.
Codex owns all shared wiring. Requested model claude-sonnet-5-5-high for coding;
controller selects another suitable CLI-listed model on actual quota, not timeout.

OWN ONLY these FOUR NEW files (do not edit existing files, even to make tests pass):
1 backend/alembic/versions/0017_feature_flag_administration.py
2 backend/app/db/feature_flag_admin.py
3 backend/app/services/feature_flag_admin.py
4 backend/tests/security/test_feature_flag_admin_api121.py

Implement a draft of the following fixed contract, then report exact files/known
gaps. Do not repeat the report's unexecuted50 tests as results. Phase1 verification
is syntax compilation only, if permitted. Native HTTP tests wait until Codex wires
storage/head/router; do not edit shared modules or claim they passed now.

PRIMARY: CAP037/ADMIN/DB092/API121, actual current MFA and expiring platform grant;
preserve canonical94/old rows, forward from0016, never edit released migrations.
Catalog exact codes: R1_PART_TIME_JOBS, R1_GENERAL_INTERNSHIPS,
R1_ACADEMIC_INTERNSHIPS, ratings, academic_official_export, WhatsApp,
paid_checkout, R2_FREELANCE_MARKETPLACE. Last five are disable-only in R1. The
R1_PAID_ORG_PLANS legacy alias cannot be PATCHed (409), reads map to paid_checkout
effective false; unknown codes fail404. No client rule_schema or org override.
Server schema exactly {"schema_version":1,"scope":"GLOBAL"}. No live enablement.

SERVICE INTERFACE for Codex wiring:
- class FeatureFlagAdministrationService, singleton flag_admin_service.
- administer(*,actor,code,enabled,reason,idempotency_key,expected_version) -> minimal
  identical stored receipt: flag_id/event_id/audit_event_id/code/enabled/
  effective_enabled/version/reason/decided_at. Keep actual session/grant/auth_version
  internal to proof, not response. Actual ActorContext/session only, no UID fallback.
- effective_enabled(code, *, conn=None) -> bool, DB-backed/no RAM cache. False for
  missing/unproved/legacy-only/mismatched/protected/R2. Valid config survives
  original author logout. Storage failures must not masquerade as certified ON.
- use GovernanceError with appropriate status codes and existing real audit API.
  Strict bool/reason15..2000/nonce8..128; stale version412, key conflict409.
  Codex router owns headers Idempotency-Key/If-Match (missing/malformed400).
- typed DB module exposes register_tables(metadata,types), matching actual DDL.

LOCKING: actor/key advisory -> code advisory -> canonical row FOR UPDATE (if exists)
-> actual current user/session/MFA/exact deterministically locked ADMIN grant.
Namespaced single BIGINT hashtextextended lock, not invalid (int,bigint) signature.
Do NOT INSERT an actor-FK intent before business locks: that acquires a user lock.
No third intents table: append-only events have UNIQUE(actor_id,idempotency_key).
After all waits recheck session/grant clock expiry/current original identity. Pin
authority to commit. Require actual READ COMMITTED for privileged mutation (no
stale outer RR actor proof). Read current state consistently, no stale RAM default.

SCHEMA: exactly TWO proposed helpers feature_flag_origins and
feature_flag_change_events. Runtime125+2 must be measured later, not claimed now.
Origins: immutable flag_id/code/origin/initial_snapshot/created_at. Capture EVERY
existing canonical row verbatim as LEGACY_IMPORT with no fabricated actor/event;
close legacy capture immediately. New PUBLIC origins require actual event proof
at commit and always preserve their initial snapshot. Never upgrade a legacy
origin to PUBLIC. Current version/proof derives from latest valid PUBLIC event.
Events: actual actor/session/auth_version/exact admin grant; flag/code/version/
prior event/snapshots and digests; nonce/fingerprint/exact minimal receipt/audit FK.
Unique actor/key and flag/version; append-only. Validate actual clock-current
ADMIN/PLATFORM MFA/session/account/grant (chosen self-grant rejected as explicit
new design), strict server schema, code policy, current canonical snapshot and
atomic audit association. New/updated canonical flags require matching latest
event at commit; block delete, code/ID/creation identity changes. Deferred proof
checks must allow same-UoW canonical -> origin -> audit -> event order and roll
back any missing/invalid proof. Raw SQL cannot silently create effective ON.

TIMEZONE: canonical snapshot helper/guards must use stable UTC rendering independent
of connection TimeZone (e.g. SQL functions with SET TimeZone='UTC'). Preserve old
canonical rows; capture via the stable helper. State equality cannot break on a
different session timezone. Use exact stored receipts on replay, no toggling
idempotent_replay. Replays require current ADMIN authority but don't resurrect the
original session. After later version, an old valid key returns original receipt.

AUDIT: use the actual existing AppendOnlyAuditStore interface/return type; don't
invent an API or insert a fake audit. Associate exact event/action/actor/source
inside same transaction. Injected failure AFTER audit insert must roll back all.

TEST DRAFT: real PostgreSQL/current actual MFA identities; trusted role/legacy
metadata declared. HTTP endpoint after Codex mounts it, direct SQL proof checks,
populated0016->0017 and DDL collision rollback, true legacy quarantine, alias/R2/
protected schema denial, exact receipt/new-session/logout behavior, timezone and
cross-process read, actual observed lock waits for missing-row and cross-code key
races, real expiry after waits, audit rollback. Reuse existing fixtures/diagnostic
observer appropriately; no test literals in production or disabled security guards.
Do not modify archived tests/shared fixtures/current125 expectations in phase1.

Allowed terminal verification ONLY:
D:/FlexBridge/.venv/Scripts/python.exe -m py_compile <the four owned file paths>
Read-only git status/diff is permitted for your own worktree. No commits/pushes.
Return <=1000 words: files, implementation decisions, actual compilation command/
exit or why not executed, unresolved concerns and exact Codex wiring needed. Then
wait for next task; no silent broad implementation. Full R1/API108/providers/legal/
pilot still unaccepted; state administration doesn't wire downstream paid/rating/
official-export/WhatsApp authorization boundaries in this unit.
