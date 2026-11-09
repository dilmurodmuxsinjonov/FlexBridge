# Placement admission — current draft

Issue65 / draft PR66. This branch is not an accepted release. Accepted main remains
PR64, migration0013 and114 runtime tables. Native tests have executed0014 with118
tables, including four new proof tables. The model's94 canonical tables are unchanged.

## Host flow

1. An accepted internship offer opens a `PLANNED` placement through `POST /api/v1/placements`.
   The actual current OWNER/HOST_COORDINATOR, independent host capability and exact
   offer/application/attempt/original revision/candidate/organization binding are required.
   PART_TIME uses job engagements and cannot acquire placement/diary rights.
2. Read `GET /placements/{id}/plan`. Before activation a host can publish a new
   plan using `PUT /placements/{id}/plan`, supplying the exact old `terms_id`,
   `version`, retry key, title, objectives, limits, required minutes and tasks.
   A new version preserves the old content and requires new version consents.
   Initial terms contain a minimal projection of the original revision; plan readers
   never receive its payroll fields or the private application/evidence snapshot.
3. The candidate personally calls `POST /placements/{id}/accept` with the exact
   current `terms_id`, `version` and `idempotency_key` of8–128 characters.
4. The host nominates an actual same-host MENTOR through
   `POST /placements/{id}/mentor-assignments` with `mentor_id`. The nominee personally
   calls `POST /placements/{id}/assignments/{assignment}/accept` with the exact
   terms/version/key. A nomination by itself grants no private diary/review rights.
   Candidate self-mentoring is denied. An OWNER may also independently hold MENTOR.
5. The host calls `POST /placements/{id}/host-decisions` with `action: ACTIVATE`
   and the exact terms/version/key. Current original mentor grant and personal
   candidate/mentor consents must still qualify. Host acceptance, the initial start
   event, canonical projections and audit commit together.

Candidate and host lists are `/me/placements` and `/organizations/{org}/placements`.
`/me/mentor-assignments` is a minimal own nomination inbox, not a diary feed.
Lists currently return at most100 records; pagination remains required. Plan access
is limited to the candidate, current host authority or currently named original
mentor scope. Private route families receive no-store headers and bounded bodies.

The legacy `/placements/{id}/confirm-start` now requires `party`, exact `terms_id`,
`version`, retry key and actual session. It delegates to candidate consent or host
activation; it never accepts an unspecified latest version. The legacy nomination
route delegates to the same host service. Ordinary PASSWORD remains valid for
MENTOR/HOST_COORDINATOR when current global sensitive-role policy allows it.

## Evidence and history

`placement_intakes` captures the exact source and explicit PUBLIC/LEGACY_IMPORT
origin. `mentor_assignment_proofs` pins the original nomination grant; imported
proofs identify the grant visible at upgrade, without claiming it was the original
historical nomination. `placement_consents` records personal version intent.
`placement_admission_events` records plan/start/cancel/revoke actions. Evidence is
append-only; accepted timestamps are projections, not substitute evidence.

Candidate/mentor logout after a completed consent preserves that intent. Every new
human call checks current account/session/sensitive-role assurance after business
locks. Mentor role or membership loss closes new private access and start eligibility;
a new grant cannot resurrect an old assignment. A host can revoke the old nomination
and create a fresh one. Workplace review now uses the actual actor and original
current accepted mentor scope. Candidate draft/submit authority remains a separate
unfinished LOG unit.

Host `CANCEL` records a historical decision. Replaying an earlier start acknowledges
its original receipt and cannot restore ACTIVE. An active plan amendment requires a
separate lifecycle. Imported canonical rows and acceptance timestamps are preserved
exactly, without creating new consents/start events. New fake legacy markers are
rejected. Migration downgrade is intentionally refused until a reviewed history-
preserving rollback exists; transactional failed-upgrade rollback is tested separately.

## Remaining acceptance work

- New academic activation is denied until current enrollment, school coordinator
  supervision/agreement/purpose and personal teacher assignment bind a pending
  placement. The old ACTIVE-before-teacher helper cannot supply this admission flow.
  API051 implements MENTOR only; its TEACHER branch remains pending.
- API088 implements ACTIVATE/CANCEL. Completion, dispute and later amendments remain
  explicit follow-ons. Source registration is not full contract completion.
- Intake/nomination retry receipts, pagination and candidate notification of the
  new mentor/view scope still need implementation and verification.
- Restore legitimate academic fixture flows through actual admission services;
  do not waive new proof guards or fabricate post-upgrade legacy rows to make tests green.
- Finish complete current CI, all affected academic/diary tests, final source review,
  manifest and exact-head GitHub acceptance before merging PR66/closing Issue65.

The live `pg_live` cluster is untouched and stopped. Native disposable PostgreSQL
tests and source review do not certify deployment, legal identity, live providers,
Docker readiness, full R1 completion or pilot readiness.
