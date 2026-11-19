# OpenCode Consensus Review: Organization HR Dashboard, Public Profiles & Placement Canonicalization

## Review Date: 2026-11-11
## Reviewer: OpenCode 1.18.29 (Independent Adversarial Review Engine)
## Target: `backend/app/services/org_dashboard.py`, `backend/app/api/v1/placement_admission.py`, `backend/app/api/v1/canonical_routes.py`, `backend/app/main.py`

### Adversarial & Security Assessment:

1. **Authorization & Boundary Verification**:
   - Authentication check verified: anonymous requests to `/api/v1/organizations/{id}/dashboard` immediately return 401 `AUTH_REQUIRED`.
   - Cross-tenant IDOR attack testing: foreign organization members, candidates, and revoked members receive uniform 404 (`ORGANIZATION_NOT_FOUND`) without information leakage or timing difference.
   - Anti-enumeration defense verified: nonexistent UUIDs, malformed IDs, and unauthorized queries produce identical uniform 404 responses, preventing resource probing.
   - Scoped roles strictly enforced: only active `OWNER`, `HR`, and `HOST_COORDINATOR` members can access internal organization HR metrics (`CAP-015`).

2. **Public Boundary Isolation & Verification Filtering**:
   - `API-009` (`GET /api/v1/organizations/{id}/opportunities`):
     * Strictly verifies organization exists with `status == 'VERIFIED'`. Unverified or suspended organizations return 404.
     * Only opportunities with `status == 'PUBLISHED'` and `closed_at IS NULL` are exposed. Drafts, internal reviews, and closed positions are strictly masked.
     * Keyset pagination over `(created_at DESC, id DESC)` prevents offset exhaustion attacks.
   - `API-010` (`GET /api/v1/organizations/{id}/rating-summary`):
     * Strictly verifies organization exists with `status == 'VERIFIED'`.
     * CAP-040 compliance: checks `ratings` feature flag; when flag is disabled, scores are withheld (`feature_enabled: false`).
     * AC-023 differential privacy compliance: sample size $n < 5$ suppresses discrete scores with `WITHHELD_INSUFFICIENT_SAMPLE`.
     * Deterministic query ordering ensures reproducible results without nondeterministic `.first()` selection.

3. **Placement Canonical Contracts Stamping**:
   - Verified that `API-050`, `API-051`, `API-030`, `API-069`, and `API-089` return their respective canonical contract ID tags in response envelopes.
   - Optimistic concurrency control on `API-051` rejects stale plan versions with 409 `STALE_PLAN_VERSION`.

4. **Performance & Zero N+1**:
   - High-performance SQL aggregation: single-transaction queries grouped by status eliminate N+1 latency across `opportunities`, `applications`, `job_engagements`, and `interviews`.

5. **Stage 2 / Freelance Decoupling**:
   - Verified that strictly NO freelance business logic (gig escrow, disputes, milestone billing, wallet transfers) is introduced in R1. Clean extension hooks preserved for future milestones.

### Verdict:
- **APPROVED**: Zero security vulnerabilities, full test suite passes against isolated PostgreSQL cluster (port 55440).
