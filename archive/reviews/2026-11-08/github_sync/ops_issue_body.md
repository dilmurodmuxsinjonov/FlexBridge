Operations still stores retention/appeal records in process-local containers. The legacy retention helper can report requested rows as actioned even though no purge occurs, and the combined appeal helper can resolve a record without a durable case workflow.

This package makes retention evaluations durable and truthful: PostgreSQL evaluation records plus audit in one transaction, bounded/idempotent authenticated COMPLIANCE/MFA requests, cross-process retrieval, and action/scanned counters fixed at zero while this remains a dry run. It disables the legacy combined nonpersistent appeal path until the separate durable submission/assigned-review package follows.

Acceptance:

- Real PostgreSQL migration and restart/second-process evidence.
- No client-reported count becomes a claim that data was scanned/deleted.
- No unauthenticated, wrong-role or password-only request can create/read operational records.
- Existing feature packages and publication hygiene gate remain green in CI.
- No destructive purge, live provider, legal approval or pilot readiness is claimed.
