# Reviewed institution appointments

Issue55 / draft PR56 implements first-institution/first-COORDINATOR claims and an
existing coordinator's TEACHER requests. This is a bounded backend workflow. It
does not certify identity, document truth, legal signatures or pilot readiness.
Additional coordinators, authority-loss recovery, student admission/enrollment,
supervision/academic assignments, exports, official grades, frontend and live
providers are separate work.

## Entry points and review

- API017 options require a current signed-in account. Ungranted ordinary PASSWORD
  users can read generic requirements. Existing globally sensitive roles retain MFA.
- API096 requires current MFA, a verified contact, owned eligible private PDFs,
  appointment dates and agreement/legal basis. A new normalized registry identity
  creates a first-coordinator claim for the current user. A known institution needs
  current institutional COORDINATOR authority to request a named registered TEACHER.
  Client role flags and email domains grant no authority. A verified institution
  with no current coordinator does not reopen bootstrap.
- API097 returns the requester's or named appointee's case/appointment metadata and
  an intelligible current proposal, including document hashes and narrowly scoped
  download links. It excludes reviewer evidence and internal storage keys. The
  named inbox is GET `/api/v1/me/institution-appointments`.
- Existing operator verification queue/claim/detail/download/decide routes explicitly
  dispatch institution cases. Current assigned MODERATOR MFA is checked in the
  transaction; requester, named target and any related institution member cannot
  review the case. Organization-only handlers keep their original case guards.

POST `/institution-appointments/{id}/consent` records named ACCEPT/DECLINE for the
exact revision and current pinned contact. It requires actual current-session
authority. First coordinators and any globally sensitive accounts need MFA;
teacher-only PASSWORD sessions retain baseline assurance. The SQL consent guard
also recognizes sensitive platform, organization and institution roles.

Only independent approval plus valid exact-revision acceptance can activate the
appointment and grant. Either order works. Every activation rechecks original
requester security/contact, the exact current coordinator grant for staff proposals,
target security/contact, current document hash/object version, dates and agreement.
An original role revoke/regrant cannot revive the old proposal. Current role labels
are supplied by the shared effective-institution predicate from PR54.

## Revision, expiry, revocation and history

Acceptance lasts24 hours for pending activation. The three-weekday Tashkent first-
response target is separate, does not expire consent and does not automatically
approve anything. Holiday treatment is not specified. The original response target
survives revisions. Expired consent needs fresh explicit acceptance; an unchanged
approved proposal does not need another reviewer outcome solely for consent expiry.

POST `/institution-appointments/{id}/revisions` is an explicit new intent under
current requester MFA/authority. It can revise never-activated NEEDS_INFO, REJECTED,
CANCELLED or approved-pending proposals while preserving the immutable requester,
named user, institution and role. Each new revision requires new review and named
acceptance; earlier outcomes, evidence and consent remain stored. Activated cases
cannot use this route to recreate a revoked grant. A new formal appointment is
required. Registered contact recycling cannot silently change the named user.

Matching intake, revision, accept and reviewer retries return receipts without
duplicate grants or audit events. Every caller still needs a current valid session
and applicable MFA/role. Persisted intent records retain their submitting session
for audit; ordinary logout invalidates that session's subsequent actions, while
explicit decline/revocation withdraws recorded intent. Security/auth-version or
contact changes invalidate the pinned pending proposal.

POST `/institution-appointments/{id}/revoke` permits the current named account or a
current institution coordinator to close the appointment. Privileged accounts keep
MFA. Role grants are revoked once; their identities, original revocation timestamps
and rows cannot be repointed, unrevoked or deleted. Revocation preserves membership
and consent/decision history and other appointments. Reappointment creates a fresh
membership if the old membership itself was revoked, preserving the old row. A
fresh role does not reopen a revoked assignment or membership. Independently
accepted nonrevoked academic assignments still require every current academic guard.

## Files, transactions and migration

Named appointees can download only the current appointment/agreement files;
requesters can also view their own submitted evidence. Assigned independent
reviewers can view linked revision evidence. All downloads require current scope,
eligible CLEAN/nondeleted unchanged content, an audit record and a60-second URL.
General file downloads retain their owner-only policy. These APIs use the shared
128KB body limit, no-store/no-cache and no-referrer response headers.

The service locks registry identity, institution, case/appointment and sorted
business material before current user/session authority. Foreign-user locks use
NOWAIT; the identity service's exact contact advisory key is tried nonblockingly,
then the contact is re-read under NOWAIT. Contention returns
INSTITUTION_BUSY_RETRY409 and rolls back the entire unit of work. Current original
coordinator authority also uses NOWAIT. An authorized operation holding authority
locks commits before a competing logout; a completed logout before authority denies
the pending write. Date/expiry checks occur at guarded boundaries, not frozen time.

Forward0011 adds four append-only runtime proof tables, giving111 runtime tables.
The historical canonical v1.4 baseline remains94 tables. DB019 cases anchor only on
appointment_id and resolve institution through the immutable request; its exactly-
one-subject rule is preserved. Normalized registry collisions abort the complete
upgrade for explicit reconciliation. Structurally invalid legacy grants are closed
with migration audit provenance, without deleting/repointing rows or inventing
historical review/acceptance. Valid trusted imported appointments remain valid.
New structural grant/parent checks prevent cross-user/institution/catalog links;
revoked membership history coexists with one current active membership.

Native PostgreSQL evidence uses actual sessions and observed database waits.
Contact/document/legacy metadata fixtures and mocked presigned storage are trusted
test setup, not live identity, scanning, provider or legal certification. Source
review, source-specific native/full CI and evidence-head checks are reported
separately in reviews/2026-11-09/institution_onboarding. Draft status is not acceptance.
