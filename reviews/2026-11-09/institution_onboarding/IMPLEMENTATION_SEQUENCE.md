# Issue55 — executable work sequence (planning)

1. Start implementation branch from merged PR54 and copy the source map, reviewed
   architecture plan and Codex decisions into reviews/2026-11-09/institution_onboarding.
   Record final PR54 evidence checks/merge in the project journal. No onboarding
   implementation or acceptance is claimed by this planning document.

2. Define strict API DTOs and the dedicated service state machine before exposing
   routes. Canonical017 generic authenticated options;096 first claim or existing
   coordinator-requested TEACHER resolved by institution/actor state;097 metadata
   scoped to requester/named target. Helper inbox, named acceptance/decline,
   same-case resubmission and revocation are necessary for a usable bounded flow.
   Decide the smallest narrowly authorized appointment-file view needed for an
   intelligible acceptance; generic file downloads remain owner-only.

3. Stable request record pins case, appointment, institution, requester and target,
   initial mode/role and idempotency identity. Immutable submissions pin revision,
   role/dates, agreement/purpose/legal-basis/evidence snapshot, contact and original
   submitter authority proof. Immutable consent pins named actor/current session,
   auth version/contact and exact revision. An immutable per-revision reviewer
   outcome can preserve approval/NEEDS_INFO/rejection independently of mutable case
   status; audit events remain atomic alongside the domain rows. Use runtime
   extension metadata consistently with existing governance migrations.

4. Forward migration seeds institution COORDINATOR/TEACHER roles and adds the narrow
   proof records, indexes and append-only protection. New structural grant checks
   validate catalog scope and exact membership/appointment user/institution links;
   they must not invent legal review for old rows. Invalid active legacy grants are
   revoked with migration provenance, retaining original rows and evidence. Tests
   intentionally manufacturing bad legacy links may need a populated0010 upgrade
   fixture rather than inserting forbidden new rows after0011. Preserve canonical
   standalone schema loading and distinguish its94-table inventory from runtime
   extensions. Upgrade tests must prove collision preflight/rollback and no silent
   legacy data loss, not just assert the new head string/table count.

5. Build intake/own-status/inbox with zero-grant invariants first, using actual current
   MFA/registered verified contacts, eligible private PDFs and business/user/session
   ordering. Registry normalization is an application identity policy, not claimed
   validation against a government registry. Current contact locking uses the exact
   identity-service key and nonblocking foreign-user/try-advisory locks; do not copy
   older blocking owner-contact helpers without adapting the #47 ordering fixes.

6. Add independent institution reviewer claim/queue/detail/download/decision service
   methods. Use explicit dispatch in existing verification API wrappers and leave
   organization-only service guards unchanged. DB019 cases anchor on appointment
   only. Reviewer must differ from requester/target and have no related institution
   membership, matching the conservative existing owner-review precedent. Every
   business action rechecks current moderator MFA/role after its business locks.

7. Activation runs under the same institution/case/appointment locks from either
   consent or review. Check both exact-revision prerequisites, current named contact,
   user/security and original submitter authority where applicable, current eligible
   evidence, appropriate agreement and appointment dates. First coordinator must
   be current on activation. A matching accept/review replay returns its receipt
   without creating another grant or resurrecting revoked authority. A stale proof
   requires explicit renewed acceptance/resubmission; it never inherits a replacement
   target or silently changes the approved revision.

8. Resubmission: NEEDS_INFO and never-activated REJECTED proposals can add a revision
   to the same case; preserve prior evidence, reviewer outcomes and consent. Require
   original immutable requester/target and a current authorized submitter. A first
   claim additionally needs a never-verified institution and no prior activation
   history; stale approved-but-not-activated proposals may explicitly refresh via
   a new revision, requiring fresh independent review and personal acceptance.
   Never use a fresh case or a changed current status to reopen completed bootstrap.
   Any consent lifetime is a separate documented policy; do not reuse the three-day
   response target as its expiry. Original first-response target survives revisions.

   Use an explicit appointment-revisions helper rather than interpreting a fresh
   API096 POST as permission to recreate bootstrap. Stable request identity remains
   fixed; each revision captures the current authority grant/session/contact proof.
   A replacement grant cannot revive old consent, but a deliberate authorized new
   revision is new intent and needs new review/acceptance. Activated appointments
   cannot use this path to resurrect revoked grants. Preserve normalized legacy
   registry spelling where possible: a normalized unique expression/lookup plus
   collision preflight is preferable to overwriting identity strings or merging rows.

9. Revocation/expiry preserve memberships, grants and acceptance history; subsequent
   requests use the shared effective authority predicate from PR54. Security/contact
   changes before activation invalidate stale intent; ordinary contact maintenance
   after a completed activation must not be confused with automatic institutional
   revocation or a new user taking over the appointment.

10. Native PostgreSQL acceptance should include first claim/no-grant/options/status,
    duplicate registry claims, known institution bootstrap denial, current coordinator
    TEACHER request, wrong/no MFA/session/contact/file/actor, review independence and
    explicit case dispatch, approval-before/after-acceptance, exact revision and
    stale/recycled target consent, positive replay and revoked replay, future/current
    appointment dates, distinct agreement dates/purposes, same-case history, real
    waits before and after authority, busy409 retry, audit rollback and populated
    upgrade constraints. Run affected institution/IAM/org-review/billing modules and
    full PostgreSQL CI. Pin an isolated source worktree for actual read-only Copilot
    review; independently reproduce material findings, rerun relevant tests, then
    final full CI/evidence-only head checks and matching-head merge.

No frontend, legal identity/document/signature certification, live delivery/provider
integration, academic admission/enrollment/supervision/export/grade or pilot readiness
is implied. Additional coordinator delegation and authority-loss recovery are queued
separately. A missing recovery workflow is reported as a limitation, not bypassed.
