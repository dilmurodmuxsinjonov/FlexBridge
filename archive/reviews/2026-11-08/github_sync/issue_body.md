The default branch still contains the pre-remediation prototype at 1460ab8 while the PostgreSQL security, IAM, candidate and organization packages exist only in the local working tree. Reviewers therefore see a different runtime and the old 39-test suite.

Publish a reviewable, tested baseline that removes probe-specific runtime exceptions, uses real PostgreSQL migrations and scoped authority, and includes the regression/upgrade/native HTTP evidence. Preserve the original prototype tests and SHA-256 archive rather than claiming the new test suite is identical.

Acceptance:

- Publication hygiene gate passes with no environment/state files or captured credentials.
- A branch/commit/PR identifies the exact source snapshot; PostgreSQL CI runs against it.
- Review remains explicit that 87 canonical APIs still return 501, frontend/live provider/DR acceptance is incomplete, and pilot_ready stays false.
- The known in-memory operations retention/appeal records are tracked and fixed in a separate following package.
