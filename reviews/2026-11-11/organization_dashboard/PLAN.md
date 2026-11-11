# Implementation & Verification Plan: Organization HR Dashboard, Public Profiles & Placement Canonicalization

- **Issue**: #110 (`feat(organizations): implement organization HR dashboard API-068, public opportunities API-009, rating summary API-010, and placement plan canonicalization API-050/051/030`)
- **Dedicated Branch**: `feature/110-organization-dashboard`
- **Target Integration Branch**: `integration/r1-agent-collaboration`
- **Frozen Main SHA**: `764fb98496fa40857acb07844fd09fcafa99b7d6` (strictly untouched)
- **Database Scope**: Isolated PostgreSQL instance on port `55440`; `pg_live` untouched.

---

## 1. Capabilities & Contracts

| Contract ID | HTTP Verb & Path | Capability | Required Roles | Key Business Invariants |
|---|---|---|---|---|
| **API-068** | `GET /api/v1/organizations/{org}/dashboard` | `CAP-015` (Organization Dashboard) | `OWNER`, `HR`, `HOST_COORDINATOR`, `ADMIN` | Aggregated HR metrics across opportunities (draft, published, closed, paused), applications (pending, accepted), engagements (active), and interviews (scheduled). Strict IDOR defense (uniform 404 on foreign membership or non-existent org to prevent enumeration). Single-transaction aggregated SQL queries with zero N+1. Returns `contract_id: "API-068"`. |
| **API-009** | `GET /api/v1/organizations/{id}/opportunities` | `CAP-001` (Public Opportunities List) | Public / Any | Public listings filtered strictly to `status == 'PUBLISHED'` and non-closed postings. Keyset cursor pagination over `(created_at DESC, id DESC)`. Suppresses internal drafts, closed roles, and paused postings. Returns `contract_id: "API-009"`. |
| **API-010** | `GET /api/v1/organizations/{id}/rating-summary` | `CAP-027` (Public Rating Aggregate) | Public / Any | Public employer rating summary with AC-023 differential privacy sample size threshold ($n < 5$ suppresses discrete score and returns `WITHHELD_INSUFFICIENT_SAMPLE`; $n = 0$ returns `UNRATED`). Returns `contract_id: "API-010"`. |
| **API-050** | `GET /api/v1/placements/{id}/plan` | `CAP-018` (Placement Plan Inspection) | `CANDIDATE`, `STUDENT`, `OWNER`, `HR`, `HOST_COORDINATOR`, `COORDINATOR`, `TEACHER` | Returns canonical placement plan with stamped `contract_id: "API-050"`, tasks, and active term version. Uniform 404 IDOR defense. |
| **API-051** | `POST /api/v1/placements/{id}/assignments/{assignment_id}/accept` | `CAP-022` (Assignment Acceptance) | `MENTOR`, `TEACHER` | Personally accepted mentor or academic supervisor assignment returns canonical receipt stamped with `contract_id: "API-051"`. Optimistic locking via term version check (409 STALE_PLAN_VERSION on concurrency conflict). |
| **API-030** | `GET /api/v1/placements` | `CAP-018` (Candidate Own Placements) | `CANDIDATE`, `STUDENT` | Returns candidate's own placement collection stamped with `contract_id: "API-030"`. |

---

## 2. Architecture & Database Interactions

1. **`OrgDashboardService` (`backend/app/services/org_dashboard.py`)**:
   - `get_dashboard_api_068`:
     * Resolves and verifies UUID organization existence.
     * Evaluates caller membership via `org_memberships`, `org_role_grants`, and `role_catalog` for active `OWNER`, `HR`, `HOST_COORDINATOR` roles or platform `ADMIN` via `platform_role_grants`.
     * Non-members / unauthorized callers immediately receive uniform 404 (`ORGANIZATION_NOT_FOUND`) to thwart organization presence enumeration.
     * Issues 4 aggregated `COUNT(*)` queries grouped by status across `opportunities`, `applications`, `job_engagements`, and `interviews`.
   - `get_public_opportunities_api_009`:
     * Public endpoint verifying organization existence (`status == 'VERIFIED'`).
     * Filters `opportunities.status == 'PUBLISHED'` and `closed_at.is_(None)`.
     * Keyset cursor pagination over composite `(created_at DESC, id DESC)` with limit clamping (default 20, max 100).
     * Calculates `vacancies_available = max(0, capacity - occupied_count)`.
   - `get_public_rating_summary_api_010`:
     * Queries `rating_aggregates` for `target_org_id == org_uuid`.
     * Enforces AC-023 privacy threshold: sample size $n < 5$ masks average score with `WITHHELD_INSUFFICIENT_SAMPLE`.
2. **Canonical Contracts Stamping**:
   - `backend/app/api/v1/placement_admission.py`:
     * `API-050`: stamped on placement plan retrieval.
     * `API-051`: stamped on assignment acceptance receipts.
     * `API-030`: stamped on candidate own placement list.
     * `API-069`: stamped on host placement list.
     * `API-089`: stamped on mentor assignments list.

---

## 3. Stage 2 (Freelancing) Decoupling & Extension Hooks

- Strictly **NO** freelance business logic (no gig escrow, no gig milestones, no order disputes, no hourly tracker) in R1.
- Clean extension points preserved:
  * Public opportunities schema accommodates future `PROJECT_GIG` or `FREELANCE_CONTRACT` enum variants without schema refactoring.
  * Org dashboard metrics aggregate across domain tables via foreign key joins, allowing addition of freelance gig metrics in Stage 2 without breaking existing contract.

---

## 4. Test Evidence

- `backend/tests/security/test_organization_dashboard_api068.py`: 8 passed in 36.29s (100% green).
- `backend/tests/security/test_organization_dashboard_adversarial.py`: 10 passed in 42.74s (100% green).
- `backend/tests/security/test_placement_plan_canonicalization_api050_051.py`: 5 passed in 28.11s (100% green).
- Regression suite `backend/tests/security/test_academic_admission.py`: 5 passed in 30.72s (100% green).
- Total new test coverage: 23 new security & contract tests passing.
