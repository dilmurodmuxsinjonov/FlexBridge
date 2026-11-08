# Operational evaluations

Migration `0006_retention_evaluations` adds a noncanonical helper table, bringing the
runtime total to 100 tables. It preserves existing business records. The canonical
model still has 94 tables; DB-084 is `legal_holds`, not `retention_executions`.

`POST /api/v1/operations/retention-executions` now records an evaluation, with a current
COMPLIANCE grant, an MFA-authenticated session and `Idempotency-Key` (8–128 characters).
The strict JSON body accepts `data_category`, nonnegative `age_days`, and an optional
`records_scanned` compatibility field. That last field is stored as a requested count;
the service does not scan records. Actual `records_scanned` and `records_actioned` are
always zero. `dry_run` is true and `execution_status` is `NOT_EXECUTED`.

The reference policy snapshot is explicitly `NOT_CERTIFIED`. A `PURGE_DUE` evaluation
is a policy calculation, without legal approval, legal-hold checks or deletion.
Custom policy installation fails closed pending a separately authorized review workflow.

Evaluation and audit insert share one PostgreSQL transaction. Concurrent retries with
the same actor/key/payload return the same record and create one audit event; a changed
payload returns 409. SQL triggers reject UPDATE and DELETE. Downgrade refuses to remove
audit history. Read records through `GET /api/v1/operations/retention-executions/{id}`
with a current COMPLIANCE or ADMIN grant and MFA. Responses use `Cache-Control: no-store`.

The old `POST /api/v1/operations/moderation-appeals` returns 410 to an authenticated
moderator. It previously combined an invented appellant identity, review and resolution
in process memory. A real appellant submission and independently assigned durable
review remain OPS-CODEX-002 work. No appeal is represented as successfully resolved here.

`GET /api/v1/operations/pilot-readiness` continues to return `pilot_ready: false`.
This package does not certify a purge worker, live providers, UI acceptance or recovery.
