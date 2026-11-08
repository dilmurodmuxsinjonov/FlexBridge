An organization can now submit a real appeal against the latest rejection on its opportunity. Submission uses the authenticated appellant; a separate independent MFA moderator claims the case and alone decides through canonical API-111. UPHOLD keeps REJECTED; REOPEN returns DRAFT for ordinary review and paid publishing. Accepted relations and evidence remain intact.

Migration0007 pins the original action/rationale and revision/skills/shifts in a new helper table, makes moderation actions append-only, and checks exact current evidence/latest-decision integrity in SQL. Current user/session/grant authority is rechecked after business locks and held until commit; concurrent grant/session revocation is serialized. Unassigned queue entries contain minimal metadata, and private evidence requires appellant identity or the assigned independent moderator.

Actual read-only Copilot CLI review found revocation interleaving and missing original rationale; those are fixed, along with exact PostgreSQL snapshot byte limits and SQL integrity guards. The preserved review/assessment separates confirmed findings from its inaccurate password-fixture assertion.

Validation: final pinned native PostgreSQL suite250 passed,0 failure/error/skip,1 framework warning,586.00s. Both GitHub checks on c46ff70 passed the complete250-test suite. Additional selected25 and authority-lock2 regressions, populated0006->0007 upgrade (100->101 runtime tables), original-decision mutation protection, source hashes, route inventory and actual peer-review evidence are under reviews/2026-11-08/ops002/. The initial fixture lookup and revoked-session401/role403 expectation failures are preserved with explicit scope; synthetic fixture secrets in the failed full JUnit were redacted. The final evidence-only commit must also pass CI before merge. No runtime edits occurred during the final native run.

Supported scope is opportunity rejection appeals. Other API-111 actions, scam hiding, public reports, rating appeals, live providers, UI and DR remain incomplete; pilot_ready stays false.

Closes #39.
