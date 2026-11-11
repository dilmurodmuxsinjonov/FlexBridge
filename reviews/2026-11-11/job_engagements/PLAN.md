# Dual-Confirmed Job Engagements Package (API-045, API-046 / CAP-012 / AC-014, AC-016 / DB-047, DB-048)

## 1. Context and Goals
- **Package Scope**:
  - `API-045`: `GET /api/v1/me/engagements/{id}` (`CAP-012` / `JOB_CONFIRM` / `DB-047`, `DB-048`)
  - `API-046`: `POST /api/v1/engagements/{id}/confirmations` (`CAP-012` / `JOB_CONFIRM` / `DB-048`, `DB-047`)
  - `AC-014`: Invariant - Status transitions to `ACTIVE` only when BOTH CANDIDATE and EMPLOYER confirm `CONFIRM_START`. Dispute marks `DISPUTED` without automatic negative rating.
  - `AC-016`: Invariant - Non-internship job engagements do not require academic diaries; `/logs` route does not open diaries for job engagements.

## 2. Invariants & Security Boundaries
- **Muzlatilgan main**: `764fb98496fa40857acb07844fd09fcafa99b7d6` is strictly frozen. All PRs target `integration/r1-agent-collaboration`.
- **Dedicated Branch**: `feature/106-job-engagements` (Issue #106).
- **Isolated PostgreSQL**: Tests execute exclusively on port `55440`. `pg_live` is untouched.
- **Server-Side Side Resolution**: `CANDIDATE` vs `EMPLOYER` is determined strictly by verifying actor context and ownership; client cannot spoof party side (403 `ENGAGEMENT_ACTOR_FORBIDDEN`).
- **Row-Level Transaction Locks**: `with_for_update()` lock on `job_engagements` prevents race conditions during concurrent confirmation calls.
- **Strict IDOR Isolation**: Uniform 404 `ENGAGEMENT_NOT_FOUND` returned on unauthorized engagement access to prevent probing.
- **Freelance Boundary**: Pure R1 scope (`PART_TIME` and `JOB`); clean decoupling for Stage 2 extensions.
