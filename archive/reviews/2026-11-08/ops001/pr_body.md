Retention evaluation records previously disappeared on restart, and the internal helper overstated execution counters. This package persists immutable PostgreSQL dry-run records and one audit event in the same transaction. It never scans or deletes data: actual counters stay zero and policy snapshots are explicitly NOT_CERTIFIED.

COMPLIANCE/MFA can create records; COMPLIANCE or ADMIN/MFA can read them. Actor/key uniqueness handles parallel retries, changed payloads return409, and SQL rejects record mutation. Migration0006 preserves existing data; runtime grows from99 to100 tables. The old fabricated combined appeal endpoint returns410 until a real separate appellant/reviewer workflow exists.

Read-only GitHub Copilot CLI review identified boolean-to-integer coercion. API integers are now strict and the service rejects boolean numbers; changed-input regressions cover both boundaries. The review and assessment are preserved under reviews/2026-11-08/ops001/.

Validation: final24 native PostgreSQL subset tests passed, including a second Python process, audit rollback, concurrent idempotency, role/MFA/revocation, strict input and no deletion. A populated0005-to0006 upgrade preserved the representative user. Both GitHub checks on code52593cd passed the complete224-test suite. Source hashes, JUnit and review evidence are under reviews/2026-11-08/ops001/. The final evidence-only commit must also pass CI before merge. No purge, legal approval, live-provider, UI or pilot readiness is claimed.

Closes #37.
