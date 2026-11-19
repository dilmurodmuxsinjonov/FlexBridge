# Issue63 — enrollment implementation evidence

2026-11-10, Codex. Draft PR64; not final package/pilot acceptance.
Runtime fix pin:dbc5033a9572cfa10e508b81bfbcd2defaabdabe. Complete source/test pin:
a92e380b97fda3b6dc20d9c20ac0b2bc1a83ab0f. The following evidence-only commit must
preserve those app/migration/test bytes. The three
legacy HTTP cases were added in80d6c71; runtime replay fix and four review tests
are indbc5033. source_manifest.json hashes exact Git blob bytes.
The later a92e380 test-only addition verifies populated upgrade failure rollback;
runtime is unchanged from revieweddbc5033.

## Resulting behavior

Canonical027/034 own education history is implemented, with detail, revision and
terminal end/withdraw helpers. Declarations remain non-eligible. Existing operator
claim/detail/private-file/decision dispatch now handles enrollment explicitly:
current independent assigned MFA/MODERATOR review, exact immutable revision,
current owned CLEAN version-pinned evidence and atomic case/enrollment/event/audit.
One-weekday first response is a weekday-only target, not automatic approval.

Forward0013 and three typed immutable proof tables loaded on real disposable
PostgreSQL:114 runtime tables. Historical canonical94 is unchanged. Exact old rows
are marked LEGACY_IMPORT without invented review; only previously-VERIFIED imports
retain prior current eligibility. New legacy insertion, raw VERIFIED promotion,
resurrection and approved history rewrite are denied. Academic binding uses the
same effective predicate; date-expiry and legitimate end are separate tests.
Old academic setup now obtains independently reviewed enrollment through actual
sessions rather than inserting a new VERIFIED row directly.

All human boundaries take actual actors/current authority after material locks,
with READ COMMITTED and current ordinary/sensitive assurance policy. Own reads
hold profile SHARE and render a joined projection. New own paths have existing
private HTTP/body middleware. roles_for remains unchanged. End preserves history,
profile and ordinary application rows; existing application service access remains.
That evidence does not certify the unfinished public application/eligibility APIs.

## Actual execution and peer findings

native_results.json retains every initial/fixed XML stage separately. Counts
overlap; no sum or complete native-suite pass is claimed.

- Schema initial:5 setup errors4.05s (strict startup still0012 after0013 load).
  Exact expected head corrected, check retained. Next1 pass/4 fixture name-argument
  failures20.43s, then4 pass/1 incomplete NULL-column comparison26.41s. Explicit
  insert and complete before/after database snapshot corrected, no guard relaxed.
- Corrected populated/proof3 passed17.45s. New exact independent SQL approval
  succeeds; changed current metadata rejects it. Later SQL positive also asserts
  approved dates cannot be rewritten.
- Initial HTTP/PG lifecycle8 passed24.75s; transactions/security12 passed36.23s.
  Actual profile and institution waits then completed session DELETE200 deny
  writes/private reads; audit failures roll back proof/business; concurrent
  create/review-versus-end and frozen outer RR are covered.
- Academic+updated replay positive63:62 passed/1 raw-date fixture failure237.93s.
  A valid end path, separate already-expired approved enrollment and SQL date guard
  targeted3 passed13.43s. Date-expiry coverage retained, runtime unchanged.
- Populated0012->0013 actual-session legacy HTTP3 passed35.10s: current/future
  VERIFIED and PENDING imports, end/withdraw/replay, preserved profile/original
  program/start/markers with no fabricated verification case or submission.
- Actual populated upgrade collision/rollback1 passed12.93s: a preexisting table
  forces0013 to fail after origin creation/capture; prior schema version, full
  enrollment row and preexisting table data remain, new origin table is rolled back.
- Actual pinned d360 read-only Copilot source review exited0. It found P2 stale
  revision replay could acknowledge changed file metadata and a self-review test
  gap. On independently diff-checked same runtime, new2 probes had1 failed/1 passed
  11.12s: stale replay202 without extra business effect; actual requester MODERATOR/
  MFA self-review was already denied. New approval already rejected stale material;
  no approval bypass or public S3 overwrite is claimed. Exact initial probe retained.
- Fix pins/compares current replay material before current account authority.
  Changed snapshot409; unchanged replay same receipt/no extra audit. Review+initial
  lifecycle10 passed31.80s. Actual replay file-row wait -> logout200 ->deny and
  ordinary application preservation/service-access2 passed13.84s.

Holder PID was observed via pg_blocking_pids with isolated pending requests; no
separately traced HTTP backend PID claim. CLEAN and published-opportunity metadata
are trusted fixtures; one presigner is explicitly doubled. No new real-provider,
antivirus, legal document truth, frontend/browser or production evidence is implied.

## Current gates and limits

Initial d36059b full922 PostgreSQL CI42710013191(push)/42710023813(PR) passed
547.75s/516.38s,1 framework warning each. Actual heads/log summaries are stored in
pr64_initial_ci.json. That green source still had the reproduced P2; it is not
acceptance of the later fix/test/evidence head. Current complete final-head CI and
the pinned narrow follow-up review are separate gates before ready/matching-head
merge. The actual clean detacheddbc5033 follow-up completed exit0: P2 appears
closed, no concrete regression/material gap in the inspected delta or file/authority
lock inversion found. It also checked added self-review/legacy coverage. Latest
full-head CI is still required. Agent analysis is not test/SHA/model/pilot certification.

contracts.json observes132 registrations:51 explicit/81 placeholders/0 missing.
Two enrollment handlers are added; registration is not functional/security
acceptance. Remaining R1 APIs/AC, broader student/job eligibility, accepted
supervision/academic assignment/export/signature, frontend, live identity/providers/
retention/credential rotation/DR and pilot readiness remain open. All DB work here
uses disposable isolated PostgreSQL; pg_live was not started or migrated.
