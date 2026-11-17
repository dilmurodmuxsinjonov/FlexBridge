# API-052 Placement Report Export Plan (CAP-026)

## 1. Context & Objectives
- Capability: `REPORT_EXPORT` / contract: `API-052` (Issue #82).
- Endpoint: `POST /api/v1/placements/{placement_id}/exports`.
- Roles & Authorized Parties:
  - `CANDIDATE` / `STUDENT`: The candidate assigned to the placement.
  - `MENTOR`: Active assigned workplace mentor (`mentor_assignments.accepted_at IS NOT NULL` and `revoked_at IS NULL`).
  - `TEACHER`: Active assigned academic teacher (`academic_assignments.accepted_at IS NOT NULL` and `revoked_at IS NULL`).
  - `HOST`: Active `OWNER` / `HOST_COORDINATOR` / `HR` of the placement organization.
  - `COORDINATOR`: Active institutional supervisor for the student's active enrollment.
  - Unassigned / Unrelated actors: Strictly `403 Forbidden` (`PLACEMENT_ACTOR_FORBIDDEN` / `REPORT_EXPORT_FORBIDDEN`).
  - `GUEST` / Unauthenticated: `401 Unauthorized`.

## 2. Technical Architecture & Constraints
- **Migration `0020_placement_exports.py`**:
  - Creates `flexbridge.placement_exports`:
    - `id UUID PRIMARY KEY`
    - `placement_id UUID NOT NULL REFERENCES flexbridge.placements(id)`
    - `actor_id UUID NOT NULL REFERENCES flexbridge.users(id)`
    - `file_id UUID NOT NULL REFERENCES flexbridge.files(id)`
    - `created_at TIMESTAMPTZ NOT NULL`
    - `expires_at TIMESTAMPTZ NOT NULL`
    - `format TEXT NOT NULL CHECK (format IN ('PDF', 'JSON'))`
    - `idempotency_key TEXT NOT NULL`
    - `request_fingerprint TEXT NOT NULL`
    - `summary_snapshot JSONB NOT NULL`
    - Indexes on `placement_id`, and composite index/constraint on `(actor_id, idempotency_key)`.
- **Files Integration (`DB-018`)**:
  - Registers the generated export file in `flexbridge.files` with `retention_class='PRIVATE_EXPORT_FILE'`.
  - Sets 24-hour expiration (`expires_at = now + 24 hours`).
- **Audit Integration (`DB-089`)**:
  - Appends audit event `REPORT_EXPORT` via `AppendOnlyAuditStore`.
- **Informational Disclaimer (`CAP-026`)**:
  - Explicit disclaimer embedded in the metadata and generated payload:
    `"Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi."`
- **Security & Idempotency Rules**:
  - Priority authorization check before any state queries to prevent oracle probing.
  - Safe actor-bound idempotency replay (403 for mismatched actor, 409 for reused key with different payload).
  - Storage adapter presigned / simulated download URL issuance.

## 3. Multi-Agent Verification Plan
1. Generate initial plan and implementation.
2. Run GitHub Copilot CLI review on architecture, security, and edge cases.
3. Run OpenCode CLI review.
4. Execute full local unit, contract, migration, and regression tests in isolated PostgreSQL test database.
5. Push `feature/82-placement-report-exports` and open PR to `integration/r1-agent-collaboration`.
6. Verify GitHub Actions CI.
