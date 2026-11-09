Implement the next institution onboarding package after PR #54. Canonical API017,
API096 and API097 currently return placeholders. A person selecting an intended
role must submit a claim, with no authority granted by email domain or client flags.

Scope: authenticated generic options; current-MFA first-institution/first-COORDINATOR
claim; existing current coordinator's reviewed TEACHER appointment request; own/named
appointment status and personal revision-bound acceptance; independent assigned
moderator review with private eligible evidence and agreement/legal-basis snapshot.
Use explicit institution reviewer dispatch and preserve organization case behavior.
Grant only after both approval and exact-revision named acceptance. Additional
coordinators, institution recovery, student admission/supervision/export/grades,
frontend and live providers are separate work.

Keep one normalized registry identity, serialize concurrent claims, and never reopen
bootstrap for a known institution after authority loss. Staff targets initially need
a registered account/current verified contact. Contact recycling or a new revision
must not reuse stale consent. Preserve same-case NEEDS_INFO evidence/decisions and
the original three-weekday first-response target; it is not consent expiry or
automatic acceptance. A moderator cannot approve their own request, named appointment
or participating institution. Teacher-only assurance remains unchanged; privileged
submitters/coordinators retain MFA.

DB019 cases must have exactly one subject: anchor on appointment_id and resolve the
institution through that appointment. Add narrow immutable runtime revision/consent
records and a forward migration after0010, with structural role/appointment scope
checks, populated-upgrade preservation and normalized-registry collision preflight.
No fabricated legacy review/consent, deleted history, implicit institution merge or
test-specific runtime bypass. Current authority guards, business/user/session lock
ordering and nonblocking foreign-user/contact locks apply to new service actions.

Validation: real success and denial HTTP/session flows; named/contact/evidence IDOR;
wrong role/user/institution/reviewer; no grant before both prerequisites; same-case
resubmission, stale/recycled consent and replay; dedupe; real SQL waits in both
security orderings, atomic retry and audit rollback; fresh and populated migrations;
affected native modules, complete PostgreSQL CI and pinned read-only source review.
Document/identity/signature truth and pilot readiness are not certified by fixtures.

Planning evidence: D:/Codex/FlexBridge-plans/edu/onboarding_architecture_review.md
(actual read-only Copilot exit0) and ONBOARDING_DECISIONS.md (Codex constraints).
Copy the concrete plan into the repository on the implementation branch.
