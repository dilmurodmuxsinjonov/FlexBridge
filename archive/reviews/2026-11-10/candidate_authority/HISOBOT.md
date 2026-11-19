# Issue61 — candidate self-service authority

2026-11-10, Codex. Draft PR62; backend scope only, acceptance still requires
both complete checks on the final PR head. Runtime source is bc4f95e7e2021dfd1911645f4487d747aeaf30d9;
the final teacher coverage delta and pinned source/test manifest use
a31b08413f8546761bbd22129785cc9194f09811. This evidence commit does not change
application, migrations or tests. No pilot or deployment acceptance is claimed.

## Problem and implementation

On pinned pre-fix source370d9c3, nine actual HTTP/PostgreSQL probes still received
200/201 after logout200 had completed while requests waited for business locks.
Seven writes changed candidate business/audit rows; two private GETs returned the
actor's own candidate data. Combined9 failed17.20s. Earlier5/5/2/2 runs overlap.
Writes used profile-row waits; the old plain SELECT reads used table locks.
These are authenticated in-flight requests, not anonymous or foreign-data exploits.
The holder PID was observed via pg_blocking_pids in an isolated pending request;
a separately traced HTTP backend PID is not claimed. CV/skills metadata are trusted
fixtures, not live scanning, legal identity or document verification.

All nine human API paths now pass the actual ActorContext: profile GET/PATCH,
skills PATCH, CV link/unlink, rules/exceptions replacement, private schedule GET
and both legacy availability-add POST routes. CV unlink is a tenth operation
variant of the same path. Services derive own scope and lock the profile, plus
the owned file for CV linking, before checking current account/session/assurance.
User-ID-only human service authorization is removed. Audit and response rendering
remain inside the guarded transaction; legacy inserts gain atomic candidate audits.

The human transaction wrapper requires actual READ COMMITTED and rejects frozen
outer REPEATABLE READ contexts. Private reads hold profile FOR SHARE through the
current-authority check and rendering. All schedule writers use the same profile
lock, including legacy paths. Internal matching get_schedule/read_snapshot and
load_snapshot behavior is preserved. Existing sensitive-role MFA, ordinary
PASSWORD, verification invalidation, CV provenance, EXCLUDE/date/range/alias and
matching query-count semantics remain. See backend/CANDIDATE_AUTHORITY.md.

## Actual native execution

| Artifact | Observed result | Scope |
| --- | --- | --- |
| authority_initial_junit.xml | 109 tests,107 passed/2 failed,318.06s JUnit | New gate; both failures expected the wrong exception class for existing legacy403. Runtime scope guards correctly denied access. |
| fixture_fix_teacher_junit.xml | 3 passed,12.18s | Corrected two class expectations plus initial formal teacher PASSWORD positive. No runtime guard relaxed. |
| affected_native_junit.xml | 88 passed,215.63s | Existing candidate/contracts/regressions, including schedule snapshot/query-count and range behavior. |
| teacher_scope_fix_junit.xml | 1 passed,8.45s | Same formal teacher positive expanded to all10 operation variants after source-review coverage finding. |

No errors/skips in these runs. Initial/follow-up scopes overlap and must not be
added into a unique total. The final new suite contains110 cases; a complete
native110 all-pass rerun is not claimed. Full CI is a separate mandatory gate.
Initial terminal time was318.07s; JUnit reports318.060s. Actual XML is preserved.

The new gate covers five post-wait account/session changes across all variants,
CV file waits, reverse actual logout serialization, ordinary/current-MFA positives,
forged sessions, foreign legacy targets, audit rollback, schedule serialization
and frozen outer snapshots. Administrative SQL for trusted security-state setup
is distinguished from actual HTTP logout. This package adds no S3/AV proof.

## Actual peer review and source evidence

Copilot CLI ran read-only in the isolated candidate-authority worktree. Initial
seven-path planning and subsequent two-legacy-path planning are retained as
separate reviews; the first review is not represented as nine-path coverage.
The bc4f95e source review exited0 with no concrete implementation defect and a P2
teacher PASSWORD test-coverage finding: only four paths had been exercised.

Codex expanded the same formal public appointment/review/consent teacher test to
every KINDS entry, including CV unlink. Canonical schedule resets avoid invalid
legacy fixture overlaps and assert success. Runtime code did not change.
The actual a31b084 narrow follow-up exited0 and closed the finding without skipped
paths or masked failures. Its precision note is retained: the role assertion
checks TEACHER present and COORDINATOR absent, rather than asserting an exact role
set; actual session PASSWORD is read. No fabricated session assurance is used.
Agent review is source analysis, not execution, SHA, model or pilot certification.

source_manifest.json hashes pinned Git blob bytes, including runtime/tests/config;
native_results.json separates all retained XML stages. contracts.json inventories
132 registrations:49 explicit/83 placeholders/0 missing. These counts do not
measure functional or security acceptance. build_evidence.py is read-only.

## GitHub and remaining work

PR60/Issue59 previously merged73d3565 after final935742d complete785 CI passed
twice525.26s/469.37s; pr60_final_ci.json preserves the actual metadata. Its green
result did not detect the separate nine candidate-authority failures above.

At this report snapshot, PR62 source bc4f95e runs42703218978(push) and
42703231479(pull_request) are in progress; neither is claimed successful. The
evidence/test-coverage head still needs both complete matching-head runs before
ready/merge. Later observed run results belong in the PR and next package's
handoff/evidence, without rewriting a pending snapshot as earlier success.

No migration, canonical handler or dependency is added: runtime0012/111 tables,
canonical historical94. Generic catalog, matching/job applications and other
domains remain separate audit scopes. Remaining EDU enrollment/admission and R1
APIs/AC, frontend, live IAM/storage/retention, credential rotation, legal identity,
DR and full pilot acceptance remain open.

Tests use isolated PostgreSQL17.11 at127.0.0.1:55440 and disposable databases.
pg_live was observed stopped again at02:38 Asia/Tashkent; no live migration/deploy
was performed. Docker/WSL administrative installation remains incomplete. Exact
environment and continuation steps are in ANTIGRAVITY_HANDOFF.md.
