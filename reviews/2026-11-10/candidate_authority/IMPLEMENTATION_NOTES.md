# Pre-implementation additional boundary notes

All9 human paths also cover CV unlink as a distinct nullable-body branch in the
new tests (10 operation variants). Account guard must be outside file_id-not-null.
Legacy2 write audits should be atomic with their inserts, using the existing
candidate audit store; existing direct fixture calls gain actual ActorContext.

Enforce the planned READ COMMITTED human boundary with a narrow candidate_transaction
wrapper: enter existing transaction, inspect actual connection isolation, fail closed
with RuntimeError if not READ COMMITTED, then own-profile/material locks and current
account_authority. All candidate human services/legacy writes use that wrapper;
internal get_schedule/read_snapshot/matching remain unchanged. This prevents a
trusted outer read_snapshot from silently freezing current-role authorization.
The two private-read tests deliberately call from an established REPEATABLE READ
outer snapshot and require fail-closed behavior. No new public assurance policy,
MFA bypass or mutation is allowed in that unsupported context. Route default stays
READ COMMITTED. Validate against actual PG and existing snapshot/query-count tests.

Only implement after PR60 final-head CI/merge. These are staged tests/planning,
not executed future success, and not a claim the nine61 paths are fixed yet.
