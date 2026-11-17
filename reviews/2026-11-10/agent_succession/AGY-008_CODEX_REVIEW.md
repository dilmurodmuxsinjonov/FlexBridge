# AGY008 design review: corrections required before implementation

Actual SUCCESS/exit0, requested GeminiArgonHigh, reported-model field absent,
conversationf8fbb8d4-2ed1-4ac4-a3a8-6c156dba0aba,379.69s. No source implementation
or tests accepted from this plan. Codex independently verified the following.

Useful: nonofficial advisory teacher statement, exact current plan/assignment and
explicit reviewed revision basis, separate workplace/completion/official authority,
declared new vocabulary rather than claiming canonical enums, immutable proof and
data-preserving history. These remain new design proposals, not executed behavior.

Reject/correct:
1. Agent branch HEAD is e5068a07 with preserved19file WIP matching published83548d3,
   not actual HEAD83548d3. Draft0017 measured127 runtime; one new helper would128,
   not the report's126->127. Registration actualbaseline70/62 ->current71/61.
2. placement_admission_events has NO decision_id column. Actual HOST writer inserts
   a decision separately after its event. Proposed legacy selection/deferred HOST
   proof join references an imaginary column and would break existing activation/
   cancellation. Do not broaden HOST producer semantics casually. A bounded new
   TEACHER-row proof guard can preserve old HOST workflows, with legacy snapshots
   retained without fabricated intent; justify exact capture/immutability boundary.
3. Nonofficial advisory endpoint should not read raw feature_flags.enabled or
   require official gate OFF. Raw legacy enabled=true is deliberately unproved
   and effectivelyOFF. Official fields/authority remain denied independently;
   any future effective gate does not disable ordinary nonofficial statements.
4. Proposed users lock before actor/key intent repeats a rejected ordering risk.
   Use an exact namespaced single-bigint actor/key intent BEFORE current user/
   session/grant locks, and recheck actual authority after all waits. Compare the
   existing actual academic review path instead of inventing signatures.
5. Replay contradiction: requiring current daily-log pointer before receipt lookup
   cannot replay an old exact receipt after pointer advances. Current parent/
   teacher/session/terms/purpose authority precedes replay; NEW-intent basis pointer
   and ACTIVE-state eligibility checks must be placed separately and explicitly.
6. Actual audit API is AppendOnlyAuditStore.append_audit_event, not record_audit_event.
   Do not invent models.py or helper-table column/function names; verify source.
7. Legacy API051 notice probe already passed and PR71 was accepted integratione506
   after full1090twice. Do not re-open it from stale historical NEXT.md. API108
   planning may proceed while PR73 full CI runs; forward0018 implementation waits
   for actual0017 integration acceptance. User Q016 succession work is now active.

Next precise task: revise the read-only API108 contract with actual metadata and
lock/replay/legacy/HOST compatibility resolved. No implementation until approved.
