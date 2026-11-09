# Initial admission guards — implementation still in progress

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
