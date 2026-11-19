# AGY-005 / Issue72: savepoint-safe same-transaction audit binding

Workspace D:/Codex/FlexBridge-agents/antigravity, branch agent/antigravity-r1,
base integration e5068a07. MAIN/MASTER FROZEN at764fb984: no Git mutations.
You are not alone. Codex edits feature_flags.py/operations.py and separate tests.
OWN ONLY backend/alembic/versions/0017_feature_flag_administration.py.
Do not revert others, edit tests/services/wiring, read .env/.data/credentials,
install anything, call other agents, access providers, or run native tests.

Actual previous tasks produced draft0017,127tables and durable API121. Initial
SQL NULL bug was corrected; two real native positives now pass. Copilot then
found two P2s; Codex reproduced BOTH in readiness_savepoint_red_junit.xml:
2failed8.422s. Your responsibility is only the savepoint defect:
an actual ADMIN administer call inside conn.begin_nested() is rejected with
"feature flag event requires its same-transaction audit event". Audit xmin is
the child subxid, but txid_current modulo2^32 is top-level. Ordinary writes pass.

Fix without removing same-transaction assurance. Approved approach:
1. Add a narrowly scoped BEFORE INSERT trigger on audit_events only for action
   FEATURE_FLAG_ADMINISTERED. Unconditionally stamp a reserved scope_snapshot
   key such as _feature_flag_top_xid with pg_current_xact_id()::text, overriding
   any caller-supplied value. Preserve other metadata and other audit actions.
   DB-owned stamping, not Python/user-provided metadata, is essential.
2. Event guard compares the stamped xid8 text to pg_current_xact_id()::text
   instead of child xmin, retaining every exact actor/action/object/source/code/
   event/version association and all canonical/proof/receipt/current authority
   checks. Audit remains append-only. No new table or revision;0017 is unreleased.
3. Keep existing legacy capture, PUBLIC origins, disabled protected flags,
   commit-time authority and rollback semantics. No changes to prior migrations.

Primary PostgreSQL17 docs verified by controller:
https://www.postgresql.org/docs/17/functions-info.html
pg_current_xact_id returns top-level xid8 even in subtransactions.

Codex owns native acceptance, not you: valid savepoint success, genuine outer
rollback removes all effects, earlier-transaction audit cannot be reused, caller
cannot forge DB stamp, full flag suite. You may syntax-compile the owned file
using D:/FlexBridge/.venv/Scripts/python.exe. Return <=500 words: actual diff,
commands/results, remaining risks. Do not claim any native test ran.
Requested model Gemini4ArgonHigh; suitable listed fallback only on actual quota.
