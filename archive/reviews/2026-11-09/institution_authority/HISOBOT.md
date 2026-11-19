# EDU-CODEX-001A — current institution authority

Issue53 / PR54. Source: `2c3f2e1017a75ce5d7e151b0e2da8ba5dce92b82`.
Final native93 passed273.95s. Complete PostgreSQL CI675 passed twice on this source:
push42620428502 in418.26s and PR42620435667 in346.12s. Evidence-only head checks
and matching-head merge follow separately. This is not pilot acceptance.

The shared effective-institution query replaces membership/grant-only authority in
session role labels and existing scoped checks. Current roles require matching
active accepted appointments, membership acceptance, current Tashkent validity
dates, verified institution, active user and correct catalog scope. Invalid legacy
history remains stored. Existing academic create/revoke/review paths use actual
sessions and current authority after business locks. Teacher-only PASSWORD sessions
retain their ordinary scope; every current sensitive role preserves global MFA.
Target-teacher contention returns atomic 409/retry. Enrollment, agreement, purpose,
assignment, placement, log and author/candidate bindings are checked; audit writes
share the transaction. Official grades require their separate future workflow.

Validation evidence is deliberately separated:

- Original runtime1368 corrected role probe: 8 failed, 1 valid control passed in
  17.77s. These prove authenticated role-label/scope defects, not anonymous grants,
  public data writes or actual FINANCE authority. The prior9 fixture name-collision
  failures18.35s are retained as harness errors. Initial predicate fix9 passed17.28s.
- First academic fixture run:46 failed/9 scope controls passed184.54s, all46 because
  the trusted TEACHER catalog fixture was missing. Diagnostic1 failed27.28s; corrected
  ordinary-teacher control1 passed18.06s. These failures are not security findings.
- Expanded scope31 passed before a revoke test compared equivalent UTC and Tashkent
  timestamp strings. The assertion now compares actual instants; no runtime timestamp
  or idempotency workaround was added. This intermediate32-case run failed1 in83.35s.
- Initial academic59 passed267.27s. Existing affected billing/organization/moderation
  authority128 passed362.14s. These are bounded native runs, not a complete backend
  acceptance claim. The initial academic run preceded an unrelated dead workplace
  branch cleanup; final source-specific verification is separate below.
- Actual read-only Copilot review of4c11b95 returned exit0 and identified the dual-role
  MFA service gap. Static dual-role HTTP was already blocked by middleware. Independent
  probes on that runtime failed3 in51.04s: direct service teacher/coordinator PASSWORD
  review, actual HTTP sensitive grant arriving after preflight during a real SQL wait,
  and trusted imported wrong revision-author/candidate binding. The last is not proof
  of a public draft-mutation path. Red artifacts retain the actual201 responses.
- The2c3f2e1 fix enforces the current sensitive role set and revision author binding.
  Those3 regressions plus the teacher-only PASSWORD control passed4 in38.59s.
  Read-only follow-up Copilot exit0 found the findings resolved and no concrete remaining
  defect/deadlock. The agent did not execute tests, verify the Git SHA or certify pilot
  readiness; Codex independently pinned the worktree and collected execution evidence.

The native suites overlap. Do not add their counts into a unique coverage total.
Final93 passed273.95s on the exact2c3f2e1 runtime/test source and reruns the complete
new gate cases; existing128 cover unchanged shared MFA semantics. Complete CI675
includes the whole backend, not just these modules. The prior4c11b95 CI672 also
passed twice (367.75s/503.25s) despite the later independently reproduced defects;
those green runs do not substitute for the three added regressions and final675.
One Starlette/httpx deprecation warning is recorded; no skip is treated as a pass.
`source_manifest.json` hashes pinned Git blob bytes; `contracts.json` is handler
registration inventory, not security or functional acceptance coverage.

Tests run against migrated disposable PostgreSQL databases. Role/contact/document,
agreement, enrollment, academic-track and assignment acceptance fixture metadata are
trusted setup, not implemented public onboarding/admission/acceptance APIs, actual
document scanning, institution identity certification or legal-signature validation.
Actual HTTP token sessions and database waits are exercised. Wait-graph helpers
correlate a held backend with an isolated pending request through pg_blocking_pids;
a separately traced HTTP backend PID is not claimed. Role/date/expiry evaluation is
at the guarded boundary; row locks do not freeze wall-clock time through commit.

No migration, new canonical handler or external provider policy was added. Runtime
head0010/107 tables and canonical94 remain. API017/096/097 are still placeholders;
canonical registration inventory remains46 explicit /86 placeholders. Student
admission, enrollment intake, academic exports/official grades, frontend/browser,
live providers/credential rotation, hardware/DR and overall pilot acceptance remain
outside this gate. Next: reviewed institution/appointment onboarding EDU-CODEX-001B.
