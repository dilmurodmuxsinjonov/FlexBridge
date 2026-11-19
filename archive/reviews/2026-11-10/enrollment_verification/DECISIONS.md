# Implementation decisions after actual read-only Copilot planning review

2026-11-10; Codex. Review ran from clean detached source7fb411b with only
view/glob/grep, exit0. No execution/SHA/model/pilot certification. Its early
progress sentence called operator actions placeholders; the final review correctly
states API109/110 are live organization/institution handlers. Codex verified this
directly; only027/034 are new canonical handlers here.

1. Implement canonical027/034 plus own detail/submit-revision/end helpers and
   explicit existing operator claim/detail/file/decision integration. Own education
   stays optional. DECLARED without files never grants student eligibility; an
   actual owned CLEAN, version-pinned evidence submission creates PENDING. New
   requests use existing VERIFIED institutions; no institution creation/bootstrap.
2. Every new public enrollment gets a typed immutable PUBLIC origin tied to actual
   candidate/user/institution, idempotency key/fingerprint and one enrollment-only
   case. A declaration's case is DRAFT and outside operator queues. Submission
   increments exact revision on that same case, with immutable proposal and full
   file snapshots. Case enrollment_id is the only non-null subject, never also
   candidate_id/institution_id. Evidence, revisions and decision/lifecycle events
   are append-only. Forward0013 adds three helper tables (actual count to verify).
3. Preserve exact pre-upgrade rows/history and mark them LEGACY_IMPORT in the
   origin table during migration. Capture whether they were already VERIFIED and
   their original identity/program/dates; do not manufacture reviewer/evidence.
   Install a guard after this capture which forbids new legacy-origin inserts.
   Only the captured already-VERIFIED set keeps its existing current eligibility,
   with current institution/date/status checks. Never auto-promote old pending rows.
   New raw VERIFIED inserts and unproved promotions are rejected. Reductions are
   allowed; ended/unverified legacy state cannot resurrect through status editing.
   A fresh approved public entry is needed for a new program, institution, start
   or extension. No destructive cleanup or invented legacy approval.
4. New public VERIFIED state requires matching immutable approved revision/event,
   exact candidate/enrollment/institution/case and file snapshots. Academic
   _academic_binding uses the same effective enrollment predicate under its
   existing business locks, preserving accepted legacy current behavior while
   refusing unproved new status. Existing academic fixtures currently insert
   VERIFIED directly; update that fixture to create and independently approve an
   enrollment through actual-session services. Do not add a test-only legacy bypass.
   Other trusted academic setup remains clearly labelled as such.
5. Keep roles_for unchanged. Own responses expose current_student and verification
   origin PUBLIC_REVIEW/LEGACY_IMPORT/DECLARED as informational fields; a label is
   not authority. Matching/application eligibility and accepted supervision/teacher
   assignment remain explicit subsequent scopes, not certified by this package.
6. Full current moderator MFA/platform grant, independent assigned reviewer,
   expected_revision and reason required. Recheck owned current CLEAN exact file
   metadata, user/institution and dates under locks before approval. Source1.3:69
   candidate document1-weekday response target; no holiday calendar/live escalation
   acceptance. An overdue case never becomes approved. NEEDS_INFO/rejection can
   resubmit on the same case, retaining old decisions; no silent approved extension.
7. New mutations/decisions/end lock institution -> own candidate profile -> enrollment
   -> verification case -> revisions/evidence -> UUID-sorted files -> actual current
   user/session/MFA/platform authority, through commit. Academic rows are not
   modified; never acquire placement/supervision after enrollment. Existing academic
   operations acquire institution first, so end/review serialize without reversed
   academic locks. Preliminary IDs are not authorization; scope rechecked while
   locked. Own list/detail uses profile SHARE, current session and a consistent
   response without taking every institution lock. Reject frozen outer RR human
   contexts like the accepted candidate boundary.
8. End/withdraw is terminal reduction with immutable event and persisted replay
   key/fingerprint/receipt, no deletion. Preserve approved proposal and case decision
   history separately from reduced effective status/end. Future-start withdrawal
   does not synthesize end_date<start_date. Same create/end key returns the same
   resource/receipt without new audit; conflicting body409. Revision submits and
   decisions are serialized with exact revision and state checks.
9. No raw optional student reference persisted or returned; purpose-bound HMAC,
   no PINFL/diploma requirement for ordinary work. Strict own request DTOs reject
   candidate/status/reviewer/verified fields. All own path family gets existing
   no-store/no-cache/no-referrer/body bound. Evidence downloads are scoped to current
   independent assigned reviewer and exact pinned revision; no key/version leaks.

Required: fresh/populated upgrade and rollback/SQL guards; actual HTTP lifecycle,
scope/flags/assurance/private evidence, version changes, same-case revision,
concurrency/idempotency/review-versus-end/audit rollback; physical session waits;
old candidate/academic/onboarding/storage regressions; full latest-head CI and
pinned source review; manifests/HISOBOT/journals/handoff. No live pg_live mutation,
frontend/live identity/legal document truth/DR/global pilot claim. Start source only
after PR62 matching-head checks/merge.
