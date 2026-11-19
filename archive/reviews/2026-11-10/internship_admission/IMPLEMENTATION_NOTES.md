# Admission implementation — current draft and preserved stages

LOG-067 current: forward0014 executed118 runtime tables, preserving imported
canonical history without inventing consent. New PUBLIC intake binds the exact
accepted internship/attempt/revision/source and actual host session/grant. New
PLANNED starts require current-version personal candidate and named original-grant
MENTOR consent plus independent host ACTIVATE. Plan publication, cancellation,
nomination revoke, current minimal projections and strict actual-session aliases
are implemented. Workplace review checks current original mentor grant/consent.
Initial terms expose only a minimal original revision plan projection, no payroll.

Current broad native37 passed156.15s; corrected history/rollback2 passed19.83s
partly overlap. Old affected integration47 passed/1 academic fixture failed148.70s.
That old fixture still uses UID-only confirmation and raw academic admission fields;
replace it with genuine pending school/teacher admission, without waiving guards.
See backend/PLACEMENT_ADMISSION.md and NEXT_ACADEMIC_UNIT.md for exact remaining
retry-receipt/pagination/viewer-notification/academic/full CI acceptance work.

Initial native lifecycle3 failed/9 passed40.65s: a list column typo and Python vs
PostgreSQL JSON timestamp formatting caused failures. Corrected list access and
server-produced exact snapshots ->15 passed46.36s. Populated upgrade fixtures
initial2 failed21.69s due missing required paid salary metadata; corrected2 passed
20.54s. Additional source-based SQL history probe1 failed34.67s revealed appending
tasks to superseded unconsented initial terms; guard now requires current pending
terms and publication switches the pointer before task inserts in the same UOW.
Corrected2 includes actual audit-failure rollback of pointer/terms/tasks/event.

Read-only Copilot source review and corrective follow-up both exit0; each launch
scope was unchanged during its run. No concrete reviewed P1/P2 delta reported;
source reasoning is not runtime/SHA/model/security/pilot certification. The initial
review's role/retry concurrency gaps received actual public revocation and duplicate
HTTP tests. Historical stages below are preserved, not current acceptance claims.

## Historical initial guard stage

Baseline PR64 merged1b2bbbf after actual final930 CI twice. Extra unchanged-source
formal Teacher PASSWORD own enrollment1 passed10.14s, preserved separately and now
retained as a permanent regression in this branch. No extra test is claimed in
the earlier930 CI. Accepted runtime is still0013/114;0014 has not been written or
executed yet. No new canonical admission handlers are accepted.

Initial exact08b probes3 failed13.64s with actual HTTP and persisted SQL rows:
PART_TIME placement created, general ACTIVE with no mentor, HR-only mentor nominated.
Published opportunity/role metadata is trusted setup; actual applications/offers/
offer response/placement/confirmation/nomination used HTTP/sessions. Last nomination
remained unaccepted, not an immediate private-review authority grant.

First code changes:

- create_placement and mentor nomination now require actual ActorContext. APIs and
  all direct fixtures were updated; there is no UID-only compatibility fallback.
  Organization -> offer or placement material -> current account/session ->
  current OWNER/HOST_COORDINATOR authority. Current host capability is required.
- New placement requires INTERNSHIP and an internship contract, with exact offer/
  application/revision/candidate/host binding. Shared require_internship_placement
  also blocks legacy ordinary-job diary creation. Ordinary work uses engagements.
- Nomination requires current same-host MENTOR via a nonblocking target role pin,
  rather than merely active membership; actual nomination audit shares the UOW.
- Existing diary fixture now creates a genuine INTERNSHIP/INTERNSHIP_AGREEMENT and
  passes an actual-session actor. Academic fixture receives actual host actor too;
  no role/status flag is added to waive a guard.

initial_guard_junit.xml:2 passed/1 failed11.21s. PART_TIME and HR nomination are
now denied. The unchanged candidate+host confirm path still activates without a
personally accepted mentor; that failure is intentionally retained as unfinished
implementation, not labelled fixed. Full source-contract lifecycle remains open.
actor_teacher_initial_junit.xml3 passed12.79s: actual offer/placement row waits,
completed host session DELETE200 ->create/nominate denied without business/audit
effects, plus the permanent formal Teacher PASSWORD enrollment control.
affected_guard_junit.xml2 passed10.75s: valid internship log immutability and
ordinary Teacher PASSWORD academic review remain. These stages overlap; not a
complete native or current full CI acceptance claim.

Next required implementation: immutable intake/plan/consent/original-mentor-grant/
activation event proofs and forward0014; actual versioned candidate and mentor
acceptance, private own/named/host projections, host activation/cancel and legacy
aliases with exact version; real positive end-to-end and all denial/upgrade/history/
concurrency/regrant/rollback cases; full old affected suites/current CI/pinned review/
manifests/handoff. The ACTIVE-before-teacher cycle requires the explicit academic
follow-on; academic-required placements must not silently activate as general ones.
Do not mark Issue65 complete merely by keeping the two initial guards green.
