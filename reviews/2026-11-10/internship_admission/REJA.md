# Source-first sequence from enrollment to reachable academic admission

Planning only at source08b4129. PR64 enrollment final-head CI is running, not yet
accepted. Codex remains owner of source changes; planning review must be read-only.

Primary sources: specs/v1_3/FlexBridge_toliq_topshiriq.md:67,120; CAP017/018/020/021;
PG028/035/036/040/041/042; canonical v1.4 DB034/049/050/051/052/054 and
API048/050/051/098/099/101/102/103/104. v1.4 PDF INV03 composite scope, INV08
accepted internship/current agreement+mentor+teacher, personal acceptance, private
data purpose and current revocation requirements remain authoritative. No signatures
or institution-wide ordinary work/application/salary access is implied.

## Authoritative current observations

- Enrollment prototype now has verified-vs-declared/history/current predicate,
  0013/114, API027/034; final matching-head CI still needed before its merge.
- Generic placement_service.create_placement accepts any accepted offer, including
  PART_TIME_JOB; only candidate+host terms confirmations make it ACTIVE. It passes
  user IDs rather than actual ActorContext through its final service boundary.
- create_mentor_assignment checks active organization membership, not MENTOR role;
  there is no implemented personal acceptance endpoint. Canonical048/050/051 are501.
- Existing academic_assignment creation requires already ACTIVE+academic_track
  placement; no public academic-track binding workflow exists. Merely aliasing
  canonical102 to it cannot construct the source-required academic admission path.
- Native independently pinned08b4129 HTTP/PG probes:3 failed13.64s, no harness
  error. A PART_TIME accepted offer created an actual placement201; actual general
  INTERNSHIP became ACTIVE200 with zero mentor assignments after candidate/host
  confirmations; actual active HR-only staff was nominated mentor201. Published
  opportunity and role catalog setup are trusted fixtures; applications, offers,
  offer response, placement/confirm and nomination used actual HTTP/sessions.
  The last result is an invalid nomination, not immediate accepted-mentor/review
  authority: accepted_at remains unset. No anonymous/foreign/live exploitation claim.
  Exact probe and XML are placement_prereq_probe.py.txt/placement_prereq_initial_junit.xml.

## Proposed ordering to refine before code

1. Complete a reachable host internship admission unit before academic bindings:
   only internship-family accepted offer/current exact application/candidate/host;
   immutable versioned terms; actual candidate and host acceptance; nomination of
   current MENTOR in the same host; personal assignment acceptance; ACTIVE only when
   required current proofs are complete. Canonical048/050/051 and explicit bounded
   host plan/mentor intake/revoke helpers, actual actors after material locks.
   Reject ordinary-job placement/diary creation; do not fake an internship kind to
   preserve current tests. Job engagement flow stays separate. Existing wrong
   legacy rows/history must survive upgrade without becoming new verified starts.
2. Then implement own-institution exact enrollment supervision and purpose/legal
   agreement, canonical098/099/101, academic assignment102/103/104 and personal
   teacher acceptance. Avoid the current ACTIVE-before-teacher circular dependency.
   Coordinator cannot self-assign teacher, nor grade their own candidate result.
   An academic ACTIVE path requires candidate+host exact terms, current accepted
   mentor, current approved enrollment, current same-institution purpose agreement,
   supervision and personally accepted teacher. No client academic/verified flag.
3. Persist idempotency, immutable request/accept/revoke and original scoped grant
   identity, so revoke/regrant cannot resurrect old accepted assignments. Bound
   accept to exact current terms/assignment identity. Keep data minimization and
   private own/named/institution scope with current ordinary/MFA rules.
4. Forward migration(s) preserve complete legacy history, mark provenance explicitly,
   reject new invalid transitions, keep canonical94 and report runtime counts.
   Existing tests currently build ordinary-job placements and set accepted/academic
   fields directly. Replace them with legitimate internship/actual-session flows
   rather than test-only grandfathering or privileged-status mutation shortcuts.
5. Reuse actual business->current account/session/scoped authority patterns, but
   derive one compatible institution/org/placement/terms/assignment/enrollment/file
   lock order with existing academic/enrollment services before coding. Real session
   waits, replay/concurrency/capacity/rollback/expiry/current grant and ordinary
   positives, populated upgrade, old affected suites, full current CI and actual
   pinned source review are mandatory. Registration is not complete API acceptance.

Decision needed from source review: the smallest functional next package that
advances this complete intended workflow without merely exposing unreachable or
unsafe legacy aliases. Name exact new canonical scopes and explicit prerequisites/
follow-ups, legacy behavior, acceptance proofs, authority/lock order and fixture
changes. Do not silently claim all APP/offer capacity/cooldown/engagement/diary/export
or full academic R1 acceptance; identify required boundaries and dependency gates.
No runtime code has changed for this planning exercise, and pg_live is untouched.
