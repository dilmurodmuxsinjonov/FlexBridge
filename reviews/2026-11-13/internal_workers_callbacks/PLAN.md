# Package Implementation Plan: Internal Workers System (Issue #134)

## 1. Overview & Objective
Complete canonical implementation of Package 4: Internal Workers System (`API-X07`, `API-X08` / `CAP-039`, `CAP-040` / `DB-018`, `DB-073`, `DB-083`), achieving the monumental milestone of 132/132 (100.0%) canonical contracts implemented and verified for FlexBridge R1.

## 2. Contracts in Scope
1. **API-X07 (`POST /api/v1/internal/workers/scan-result`)**:
   - Internal ClamAV + pypdf malware and document sanitization callback (`CAP-039` / `OPERATIONS` / `DB-018`, `DB-073`).
   - Handles `CLEAN`, `INFECTED`, and `FAILED` scan statuses.
   - For `CLEAN` files: updates `scan_status = 'CLEAN'`, verifies sha256 checksum, ensures storage provenance (`storage_key` under `private/`, `object_version = storage_version_id`).
   - For `INFECTED` files: immediate quarantine (`scan_status = 'QUARANTINED'`, `quarantine_reason` recorded), blocks downloads, and records immutable audit event `FILE_SCAN_QUARANTINED`.
   - For `FAILED` files: maps to database error state (`scan_status = 'ERROR'`) while preserving storage references.
   - Idempotent callback processing for duplicate delivery.
   - Uniform 404 IDOR defense for nonexistent files (`FILE_NOT_FOUND`).
   - Stamped Contract: `"contract_id": "API-X07"`.

2. **API-X08 (`POST /api/v1/internal/workers/retention-sweep`)**:
   - Automated background cleanup executing DB-083 retention policies (`CAP-040` / `OPERATIONS` / `DB-083`).
   - Purges expired sessions, expired platform/organization role grants, and soft-deleted files past retention window.
   - Supports `dry_run` mode for policy audit without mutating database records.
   - Respects batch `limit` bounds (1 to 1000).
   - Zero Customer PII in response summary.
   - Emits immutable audit event `RETENTION_SWEEP_EXECUTED`.
   - Stamped Contract: `"contract_id": "API-X08"`.

## 3. Worker Authority & Security
- Endpoints accept either internal token authentication via `X-Internal-Worker-Token` matching configured secret, or authenticated staff actor context with `ADMIN`, `OPERATIONS`, or `SECURITY_LEAD` platform roles.
- Unauthenticated or non-staff callers strictly denied with 401 `UNAUTHORIZED` or 403 `PERMISSION_DENIED`.

## 4. Operational & Security Constraints
- Target integration branch: `integration/r1-agent-collaboration`.
- Frozen `main` branch (`764fb98496fa40857acb07844fd09fcafa99b7d6`): Zero mutations.
- Isolated test PostgreSQL port: `127.0.0.1:55440`. Live production DB `pg_live` untouched.
- Pure R1 scope: Zero Stage 2 freelance code.
- Zero Customer PII leakage across all worker responses.
