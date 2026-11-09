# Backend validation and operation

Run commands from `D:\FlexBridge`. Python 3.11+ and PostgreSQL 17 are required.
Dependencies have one source: `backend/requirements.txt`, also used by pyproject and Docker.
The IAM extension (OTP/contact verification, recovery, MFA tickets, passkeys and its separate worker)
is documented in [IAM.md](IAM.md). Public registration now requires a verified contact proof and
the configured published policy versions.
Candidate profile, self-declared skills, private CV linking and date-aware 28-day matching
are documented in [CANDIDATE.md](CANDIDATE.md). The CAN package uses the existing migrated
schema; no additional migration is required.
Organization onboarding and independent first-owner/capability verification are documented
in [ORGANIZATIONS.md](ORGANIZATIONS.md). Deployments now require migration
`0004_org_onboarding` or later; conflicting normalized legacy tax IDs fail without merging data.
Explicit 24-hour contact-bound staff invitations
and legacy-token handling are documented in [INVITATIONS.md](INVITATIONS.md).
Durable, immutable retention dry-run
records and the retired combined appeal endpoint are documented in [OPERATIONS.md](OPERATIONS.md).
Separate authenticated opportunity rejection
appeals and independent assigned review are documented in [MODERATION_APPEALS.md](MODERATION_APPEALS.md).
The current branch head is `0012_file_storage_versions` (runtime111 tables;
canonical v1.4 remains94). Reviewed first-coordinator and named teacher onboarding,
revision/consent/revocation behavior and bounded validation are documented in
[INSTITUTION_ONBOARDING.md](INSTITUTION_ONBOARDING.md). Source eadac11 passed full
732-test CI twice; final evidence-head732 CI also passed twice and PR56 merged12cd307.
Provider version-pinned private retrieval remains open in Issue57; pilot is not ready.
The draft implementation, migration/legacy policy and required real S3 test setup
are documented in [STORAGE_VERSIONS.md](STORAGE_VERSIONS.md); validation is in progress.
For the current Windows tool installation status and exact continuation steps, read
[ANTIGRAVITY_HANDOFF.md](../ANTIGRAVITY_HANDOFF.md). Use the project `.venv` interpreter.
Additional owners require an existing active staff
membership, named-target consent and independent review; see [OWNER_ADDITIONS.md](OWNER_ADDITIONS.md).
Reviewed departure to an existing OWNER successor preserves other staff roles; see
[OWNER_TRANSFERS.md](OWNER_TRANSFERS.md). Inaccessible-owner recovery remains open.
Existing-staff continuity through two independent reviewers is described in
[OWNER_CONTINUITY.md](OWNER_CONTINUITY.md); manual same-account/zero-owner recovery remains open.

```powershell
python -m pip install -r backend/requirements.txt
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/flexbridge'
python -m alembic -c backend/alembic.ini upgrade head
Set-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# In a separate terminal with the same environment:
python -m app.workers.outbox
```

No default SQLite database or automatic `create_all` is used. An unavailable database,
missing migration, missing signing key, or unavailable AV/storage cannot grant authority,
capture a payment, or mark a file CLEAN. The first migration installs the canonical SQL;
the second adds operational columns, real overlap constraints, pinned trigger search paths,
and stricter submitted-revision immutability. Offline Alembic SQL generation is unsupported
and fails explicitly. Run migration DDL directly against PostgreSQL; runtime connections
may use PgBouncer transaction pooling (`prepare_threshold=None`).

The third migration adds IAM delivery/continuations/rate limits and account/session auth versions.
It upgrades the canonical PostgreSQL schema without copying the old prototype's SQLite data.

These migrations target a new canonical database. The previous prototype stored incompatible
SQLite/JSON records and its Alembic command was a no-op. Existing data is never silently
converted or deleted: take a backup and perform a separately reviewed data conversion before
switching any existing installation. Do not stamp a populated prototype as migrated.

## Regression tests

```powershell
# Test server only; the role needs CREATE DATABASE and permission to install btree_gist.
$env:FLEXBRIDGE_TEST_ADMIN_URL='postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/postgres'
python -m pytest backend -q
# Or start/stop a dedicated native PostgreSQL test cluster automatically:
powershell -File scripts/Test-Backend.ps1
```

The fixture creates a random `flexbridge_test_*` database, migrates it, truncates only that
disposable database between tests, and drops it afterward. It never truncates the supplied
admin database. HTTP assertions use TestClient; concurrency uses real PostgreSQL locks and
another Python process. S3/gateway tests use explicit test doubles; ClamAV protocol tests use
a local TCP fixture. They do not certify live external services or a browser/UI.

Twelve prototype test modules are preserved byte-for-byte under
`reviews/2026-11-07/codex_fix/legacy_tests` with SHA-256 manifest. They asserted incompatible
contracts (unauthenticated writes, raw session IDs as bearer, fake PDF/provider success,
in-memory dictionaries and unconditional readiness). SQL-backed regressions replace those
fixtures. Retention policy tests remain, with a real authenticated audit identity.
This replacement does not claim all 42 acceptance criteria are covered.

## Authentication and finance contracts

- Public registration creates only CANDIDATE. Verified grants are stored in scope-specific
  tables. No seed-operator or test-role helper exists in runtime. Initial operator grants
  require an administrative provisioning process.
- Login returns separate `session_id` (public UUID) and `access_token` (secret bearer).
  Every bearer is hashed; the digest itself never authenticates. Expiry/revocation and
  grants are read from PostgreSQL on every request, without an authoritative memory cache.
- `MFA_ENCRYPTION_KEY` is a Fernet key. Enabling TOTP requires the current password and
  proof of the new code; replacing an existing factor additionally requires its current code.
- Actor/requester/approver identity comes from the authenticated request. Refund request,
  first FINANCE approval and second FINANCE approval are separate operations. Only captured
  payments can be reserved for refund; locks prevent oversubscription.
- HMAC is an explicit adapter contract, not a Payme/Click implementation. Configure
  `PAYMENT_WEBHOOK_SECRET` (at least 32 characters). The callback fields are `provider_event_id`,
  `attempt_id` (UUID), `amount_uzs`, `currency`, `timestamp` (Unix seconds), `signature`.
  Sign UTF-8 compact JSON `["HMAC",event_id,attempt_uuid,amount,"UZS",timestamp]` with HMAC-SHA256
  and hex encoding. Timestamp tolerance is 300 seconds. Replays do not duplicate capture,
  entitlement or ledger entries. Factual signed capture callbacks are recorded even during
  OPEN finance incidents; new commerce remains blocked.
- Refund worker requires `PAYMENT_GATEWAY_URL` (HTTPS) and `PAYMENT_GATEWAY_TOKEN`. It posts
  `/refunds` with bearer authorization and `Idempotency-Key: refund_uuid`; body contains
  `refund_id`, `payment_attempt_id`, `provider`, `provider_transaction_id`, decimal-string
  `amount`, and `currency`. A final response must contain the same `refund_id`, status
  `REFUNDED`, and a nonempty `provider_refund_id`. The gateway must persist idempotency across
  retries. Missing configuration/failure leaves the outbox event pending; approval alone
  never means money was returned. Actual provider integration needs staging verification.
- Publishing requires independent moderation approval, an active paid entitlement and an
  organization lock. Draft creation never bypasses moderation. Pause/resume does not consume
  the same single-post credit twice. Closing frees a concurrent slot.

## Files, worker and deployment

Configure `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, and optionally
`S3_PUBLIC_ENDPOINT_URL` for browser-reachable presigned URLs. The bucket must remain private.
`CLAMAV_HOST`/`CLAMAV_PORT` point to an internal clamd TCP service. Keep it off public networks.

Upload intent returns a real 300-second presigned PUT to a UUID quarantine key. Completion
checks stored length and pins its ETag. The worker reads that version with If-Match, sends
actual bytes over clamd INSTREAM, then parses PDF in a killable child process. Linux production
enforces 512 MiB address-space and 20 CPU seconds; timeout is 30 seconds. Limits also cover
20 MiB input/decoded streams, 50 pages, 5000 visited graph nodes, depth and active content.
Only a successful scan plus durable private write can set CLEAN; downloads expire in 60 seconds.
The former client-controlled `/complete-scan` returns 410.

Outbox claims pending rows before LIMIT, uses SKIP LOCKED, expiring leases and claim tokens.
Effects occur before acknowledgment; state application and acknowledgment share one transaction.
External effects must be idempotent because a crashed/expired worker can retry. After five
failures events remain unprocessed for operator investigation; no automatic success/deletion.

Compose build context is repository root and includes canonical SQL/specs. API and worker run
as an unprivileged OS user. `migrate` must finish before either starts. The local development
compose provisions a private MinIO bucket and versioning. Copy `infra/.env.example` to
`infra/.env`, configure URL-safe secrets and a real gateway, then run:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up --build
```

Compose database/object-storage owner credentials are for local development. Separate least
privilege runtime credentials, real payment-provider staging, container execution, backup/restore
and all remaining 501 contracts are release tasks. Liveness proves the process is running;
readiness probes database/migration, bucket, AV and worker heartbeat plus required configuration.
`pilot_ready` remains false pending full end-to-end acceptance and a recovery drill. Setting
`FLEXBRIDGE_EXTERNAL_SERVICES_VERIFIED` has no effect.
