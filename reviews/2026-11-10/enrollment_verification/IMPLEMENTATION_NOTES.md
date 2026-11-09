# Prototype execution snapshot

Current branch feature/63-enrollment-verification from mergedb94da55. PR62 final
metadata is retained here: both895 passed547.44s/582.45s; Issue61 closed. This is
Issue63 implementation, not final acceptance.

0013 creates three typed immutable proof tables,114 actual runtime tables. Captured
legacy origin set, exact public approval/current predicate, actual session metadata,
private file snapshots and no unproved promotion are implemented. Canonical027/034,
own detail/revision/end, operator dispatch/claim/detail/file/decision and academic
predicate are now connected. New own family has private HTTP/body protection.

Native stages (not additive):

- schema_initial_junit.xml:5 setup errors4.05s. Migration itself loaded, but startup
  still expected0012; exact expected head updated to0013, strict check retained.
- schema_head_fix_junit.xml:1 passed/4 fixture failures20.43s. Institutions have a
  `name` field which collided with insert_row's table-name argument; corrected to
  an explicit typed insert. No runtime guard relaxed.
- schema_fixture_fix_junit.xml:4 passed/1 assertion failure26.41s. Database row had
  three legitimate NULL fields omitted from the fixture dictionary. Preservation
  assertion now compares complete actual before/after database rows.
- schema_proof_junit.xml:3 passed17.45s. Corrected populated legacy preservation,
  closed marker/promotion/resurrection and two new SQL tests: independently approved
  exact current owned revision can verify; changed metadata rejects approval.
- lifecycle_initial_junit.xml:8 passed24.75s,1 framework warning. Actual HTTP/PG
  declaration/history/privacy, review/download/approval/end/replay, same-case
  NEEDS_INFO revision history, caller authority field denial and own/foreign scope.
  CLEAN metadata trusted; download presigner explicitly doubled.

Accepted decision replay was then refined to return its immutable receipt without
revalidating delivery material as a new approval. Positive test now changes trusted
file metadata after acceptance and checks identical retry receipt. The current
academic fixture uses actual-session enrollment create/claim/approve services;
other agreement/track/assignment acceptance remains trusted setup. Its affected
suite plus that updated positive completed:63 cases,62 passed/1 fixture failure
237.93s. The old enrollment_expired setup directly rewrote approved dates and was
correctly rejected by23514. The review-chain case now uses legitimate end_own;
a new separate already-expired approved enrollment denies assignment creation.
The SQL positive also now asserts approved dates cannot be overwritten.
Those targeted3 passed13.43s (academic_fixture_fix_junit.xml), runtime unchanged.
No guard was relaxed and expiry coverage was not removed.

transactions_initial_junit.xml:12 passed36.23s,1 framework warning. Actual
PostgreSQL/HTTP profile-row waits followed by completed session DELETE200 for
create/list/detail/revision/end; moderator session DELETE during institution-row
wait; three audit-failure rollbacks; concurrent create replay and review-versus-end;
frozen outer RR read refusal. Holder PID is observed via pg_blocking_pids in an
isolated pending request, not a separately traced HTTP backend PID. Counts/stages
overlap and are not a full current native-suite or complete CI pass claim.

legacy_http_initial_junit.xml:3 passed35.10s,1 framework warning. A separate
disposable database is populated at0012 with real-password/session fixture users
and trusted pre-upgrade enrollments, then upgraded to0013. Actual HTTP shows
current VERIFIED, future VERIFIED and PENDING imports as LEGACY_IMPORT/unreviewed,
with correct current-student flags. End/withdraw/replay preserves profile, original
program/start and marker history, adds exactly one terminal event without inventing
a verification case/submission or invalid future dates. The global engine is
restored in finally; no pg_live changes. This is a test-only delta afterd36059b.

DraftPR64/source d36059b full CI42710013191/42710023813 and isolated pinned source
review are running. Read-only agent output/exit must be checked when terminal;
pending state is not a source acceptance certificate. No new runtime change
after the prototype commit is implied by the legacy HTTP test expansion.

Actual d360 source review exit0 found P2 revision replay could202 after trusted
file metadata changed, and a self-review test gap. Codex verified root runtime
identical to that pinned source before review_initial_junit.xml:1 failed/1 passed
11.12s, unchanged business/audit state. This is a misleading submission receipt,
not an approval bypass; new approval already checked current evidence. Own MODERATOR
with real MFA was already denied self-claim/self-decision. Initial exact probe retained.

Replay branch now locks/pins owned current files before current account authority,
compares full snapshot to the submitted revision, then returns an idempotent receipt
or409 ENROLLMENT_EVIDENCE_CHANGED. No guard-first/file-wait inversion is introduced.
review_fix_junit.xml10 passed31.80s: positive unchanged replay, changed-material
denial, self-review scopes and all initial lifecycle cases. replay_wait_ordinary_
junit.xml2 passed13.84s: observed actual file-row wait then completed logout200
denies revision replay without effects; actual enrollment end preserves an existing
ordinary application row and the existing service can create another afterward.
Published opportunity metadata is trusted; this is not acceptance of still-open
public application/eligibility handlers. Native stages overlap. Pinned follow-up
source review and full current final-head CI remain required.

Remaining: complete affected outcome, legitimate fixture changes if needed,
actual session/security/business waits, concurrency/replay/rollback/provider/error
edges and source-pinned review/full current CI/manifests/HISOBOT/journals/handoff.
No complete full-package/all-R1 acceptance, live identity or pg_live migration.
