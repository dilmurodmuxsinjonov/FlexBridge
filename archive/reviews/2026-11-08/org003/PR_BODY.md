Additional organization owners now require a current owner's request, consent from the named existing staff member with MFA and a verified contact, and approval by an independently assigned moderator. No OWNER grant exists before those steps; approval commits the grant, ownership history, case and audit together.

Revoking and regranting authority cannot revive an old request or consent: both retain their original grant IDs. Staff invitation acceptance preserves revoked grant rows and creates a fresh row. Evidence revisions, cancellation, decline, rejection, concurrency and audit failures retain a truthful history.

Validation on f118e23e2a0d2d48d08a6ad8fd500f5a43bca9d2:

- Native PostgreSQL: 120 affected tests passed, zero failures/errors/skips; 282.714 seconds.
- Complete GitHub PostgreSQL CI: 297 passed; run42503498638.
- Populated0007-to-0008 upgrade replay passed:101-to-103 tables, legacy grant/event preservation, duplicate-active rejection and immutable history.
- Actual read-only Copilot review found the invitation history defect, which was fixed. Final grant-binding follow-up completed exit0 with no confirmed HTTP defect; its replay-attribution concern is retained in the assessment.
- Two stale-grant lifecycle tests initially failed against the prior295-test snapshot. Their original failures and subsequent passing results are retained under reviews/2026-11-08/org003.

Direct database writers are trusted. API authentication verifies actual MFA and contact HMAC; SQL proof enforces relational integrity. Synthetic contact/file metadata and TestClient tests do not establish live delivery, legal identity, browser or production readiness. Canonical inventory remains46 explicit handlers and86 placeholders out of132; this package adds helper routes. Transfer/recovery and pilot acceptance remain open.

Closes #41
