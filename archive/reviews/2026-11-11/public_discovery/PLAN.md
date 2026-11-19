# Issue #112: Public Discovery, Onboarding Options, and Knowledge Catalog Implementation Plan

## 1. Scope and Canonical Contracts
- **Target Branch**: `feature/112-public-discovery-and-catalog`
- **Base Branch**: `integration/r1-agent-collaboration`
- **Protected Main SHA**: `764fb98496fa40857acb07844fd09fcafa99b7d6` (strictly frozen, untouched)
- **Target Contracts**:
  1. `API-001`: `GET /api/v1/opportunities` (CAP-001, Public Search)
  2. `API-002`: `GET /api/v1/onboarding/options` (CAP-002, Public Onboarding Routes & Stage 2 Freelance Extension Hook)
  3. `API-011`: `GET /api/v1/services/public` (CAP-039, Public Service Catalog)
  4. `API-012`: `GET /api/v1/prices/public` (CAP-039, Public Pricing & Refund Terms)
  5. `API-013`: `GET /api/v1/help/{document}` (CAP-039, Public Help CMS Documentation)
  6. `API-014`: `GET /api/v1/policies/{document}` (CAP-039, Public Legal Policies CMS)

## 2. Architectural Design & Invariants
- **Public Opportunity Search (`API-001`)**:
  - Joins `opportunities`, `opportunity_revisions`, and `organizations`.
  - Filters strictly to `opportunities.status == 'PUBLISHED'`, `opportunities.closed_at IS NULL`, and `organizations.status == 'VERIFIED'`.
  - Excludes draft, closed, paused, or unverified organization opportunities.
  - Computes `vacancies_available = max(0, capacity - occupied_count)`.
  - Supports filters: `region`, `kind`, `is_paid`, `min_hourly_pay`, `schedule_policy`, `skill_id`, `query`.
  - Stable Keyset cursor pagination over `(published_at DESC, id DESC)`.
- **Onboarding Options (`API-002`)**:
  - Persona tracks: `CANDIDATE`, `STUDENT`, `EMPLOYER`, `HOST_ORGANIZATION`, `INSTITUTION`.
  - **Stage 2 Freelance Directive**: Clearly exposes `FREELANCER` track with `is_active: False`, `stage: 2`, `status: "PLANNED"`, preserving loose-coupling extension hooks without implementing operational freelance logic in R1.
- **Static Knowledge & Legal CMS (`API-011`, `API-012`, `API-013`, `API-014`)**:
  - Versioned CMS documents with deterministic slugs.
  - Uniform 404 for unknown documents.
  - Public whitelist regex in `main.py` updated to permit guest access without bearer authentication.

## 3. Test Suites
- `backend/tests/security/test_public_discovery_api001_002.py`
- `backend/tests/security/test_public_catalog_and_cms_api011_014.py`
- `backend/tests/security/test_public_discovery_adversarial.py`
