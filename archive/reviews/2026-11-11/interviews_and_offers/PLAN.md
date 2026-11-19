# Interviews and Offers Acceptance Package (API-042, API-043, API-085, API-086 / CAP-009, CAP-011 / AC-012)

## 1. Context and Goals
- **Package Scope**:
  - `API-042`: `POST /api/v1/interviews/{id}/responses` (`CAP-009` / `INTERVIEW` / `DB-044`, `DB-045`)
  - `API-043`: `POST /api/v1/offers/{id}/respond` (`CAP-011` / `OFFER_ACCEPT` / `DB-046`, `DB-035`, `DB-041`)
  - `API-085`: `POST /api/v1/applications/{id}/interviews` (Helper for host to schedule interviews)
  - `API-086`: `POST /api/v1/applications/{id}/offers` (Helper for host to issue formal job offers)
  - `AC-012`: Acceptance criteria - "Bir qolgan o'ringa ikki parallel ACCEPT: biri 200, biri 409, occupied_count=capacity."

## 2. Invariants & Boundaries
- **Muzlatilgan main**: `764fb98496fa40857acb07844fd09fcafa99b7d6` is strictly frozen. No direct commits or pushes.
- **Integration Target**: Target branch is `integration/r1-agent-collaboration`. Dedicated feature branch `feature/104-interviews-and-offers`.
- **Zero pg_live Access**: Tests execute strictly on isolated test PostgreSQL instance on port `55440`.
- **Concurrency & Capacity Control**: Atomic row-level lock (`with_for_update()`) on `opportunities` row during offer acceptance ensures capacity over-allocation is physically impossible under concurrent requests.
- **Strict IDOR Isolation**: Uniform 404 response on any attempt to inspect or respond to interviews/offers belonging to another candidate.
- **Decoupled Architecture**: Freelance / 2nd stage logic is strictly out of R1 scope while keeping extension points clean.

## 3. Implementation Details
- Service: `backend/app/services/interviews_and_offers.py`
  - `schedule_interview` (`API-085`): Validates organizer membership, timing constraints (`ends_at > starts_at`), inserts `interviews` row, transitions application status to `INTERVIEW_SCHEDULED`, writes audit event.
  - `respond_to_interview` (`API-042`): Validates party authorization, rejects updates on finalized interviews (409), upserts `interview_responses`, updates interview status (`CONFIRMED`, `CANCELLED`, `RESCHEDULE_REQUESTED`, `COMPLETED`, `NO_SHOW`), increments version, writes audit event.
  - `issue_offer` (`API-086`): Issues terms snapshot, sets `OFFERED` status, expiry time (default 7 days), sets application status `OFFERED`, writes audit event.
  - `respond_to_offer` (`API-043`): Strict candidate ownership check (404), handles idempotent replay (200), validates expiration, executes `with_for_update()` lock on `opportunities`, checks `occupied_count < capacity` (409 `CAPACITY_EXHAUSTED` on violation), increments `occupied_count`, sets offer to `ACCEPTED`, sets application to `ACCEPTED`, creates `job_engagements` for non-internship opportunities, writes audit event.
- Router: `backend/app/api/v1/canonical_routes.py`
  - Mounted `API-042`, `API-043`, `API-085`, `API-086` with Pydantic v2 schemas and actor context resolution.
- Test Suite: `backend/tests/security/test_interviews_api042_offers_api043.py`
  - 11 comprehensive tests covering functional flows, IDOR boundaries, error conditions, expiry, idempotency, and AC-012 parallel race conditions.
