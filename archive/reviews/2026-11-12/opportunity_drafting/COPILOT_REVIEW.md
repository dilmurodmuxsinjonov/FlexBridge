# GitHub Copilot CLI Review: Opportunity Drafting, Terms, and Schedule Configuration

## Review Date: 2026-11-12
## Reviewer: GitHub Copilot CLI 1.0.109 (GPT-6 Luna Model Engine)
## Target Branch: `feature/114-opportunity-drafting-and-revisions`
## Base Target: `integration/r1-agent-collaboration`

### 1. Architectural & Contract Conformance
- **API-078 (`PUT /api/v1/opportunities/{id}/draft` / `CAP-016`)**:
  * Successfully validates core parameters (`title`, `description`, `region`, `work_mode`, `eligibility`, `capacity`, `contract_type`, `program_required`).
  * Enforces `capacity > 0` and `capacity >= occupied_count` with clean 422 and 409 responses.
  * Preserves immutability of published opportunities: only `DRAFT` status is modifiable; published/closed opportunities return 409 `OPPORTUNITY_NOT_DRAFT` (`AC-008`).
  * Enforces uniform 404 `OPPORTUNITY_NOT_FOUND` against foreign organizations, avoiding information disclosure.
  * Verified contract stamp: `"contract_id": "API-078"`.
- **API-079 (`PUT /api/v1/opportunities/{id}/draft/terms` / `CAP-016`)**:
  * Strictly enforces the labor invariant: `PART_TIME` opportunities must be paid (`is_paid == True`). An attempt to set `is_paid = False` on part-time is rejected with 422 `UNPAID_PART_TIME_FORBIDDEN`.
  * Validates salary bounds: `salary_min > 0`, `salary_max >= salary_min` if present, `salary_period in ('HOUR', 'MONTH')`, and `salary_basis in ('GROSS', 'NET')`.
  * Date range logic: `end_date >= start_date` enforced; nullable `end_date` supported for indefinite part-time arrangements (`AC-013`).
  * Verified contract stamp: `"contract_id": "API-079"`.
- **API-080 (`PUT /api/v1/opportunities/{id}/draft/schedule` / `CAP-016`)**:
  * Configures `schedule_policy` (`STRICT`, `NEGOTIABLE`, `FIXED`) and `shift_match_mode` (`ALL_SHIFTS_IN_GROUP`, `ANY_SHIFT_IN_GROUP`).
  * Enforces non-overlapping shift intervals within each `(group_code, weekday)` pair (`INV-02`), preventing schedule ambiguity.
  * Atomically replaces shifts in `opportunity_shifts` within a single database transaction.
  * Verified contract stamp: `"contract_id": "API-080"`.

### 2. Security & Role Isolation Analysis
- **Role Scoping (`OWNER`, `HR`, `HOST_COORDINATOR`)**:
  * Caller must hold an active org role in the owning organization.
  * `HOST_COORDINATOR` role is strictly restricted to `INTERNSHIP` opportunities; editing `PART_TIME` returns 403 `HOST_COORDINATOR_INTERNSHIP_ONLY`.
- **IDOR & Multi-Tenant Defense**:
  * Any request from an unauthenticated user or user belonging to a different tenant returns uniform 404 `OPPORTUNITY_NOT_FOUND`, preventing resource enumeration attacks.
- **Stage 2 Freelance Directive**:
  * Opportunities kind is strictly restricted to `PART_TIME` and `INTERNSHIP`. Zero freelance logic in R1.

### 3. Empirical Test Results
- `backend/tests/security/test_opportunity_drafts_api078_079_080.py`: 4/4 PASSED
- `backend/tests/security/test_opportunity_drafts_adversarial.py`: 7/7 PASSED
- Total: 11/11 tests PASSED (100% green on isolated PostgreSQL port 55440).
- Regressions (`test_public_discovery_api001_002.py`, `test_organization_dashboard_api068.py`, `test_public_catalog_and_cms_api011_014.py`): 21/21 PASSED.

### Verdict
- **APPROVED**: Zero P1 or P2 defects observed. Fully compliant with canonical specifications and system invariants.
