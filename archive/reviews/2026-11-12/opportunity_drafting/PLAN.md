# Plan: Opportunity Drafting, Terms Validation, and Shift Schedule Configuration (Issue #114)

## Target Scope
- **Issue**: #114 (`https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/114`)
- **Contracts**:
  * `API-078`: `PUT /api/v1/opportunities/{id}/draft` (`CAP-016`, `JOB_PUBLISH`)
  * `API-079`: `PUT /api/v1/opportunities/{id}/draft/terms` (`CAP-016`, `JOB_PUBLISH`)
  * `API-080`: `PUT /api/v1/opportunities/{id}/draft/schedule` (`CAP-016`, `JOB_PUBLISH`)
- **Target Branch**: `feature/114-opportunity-drafting-and-revisions`
- **Base Branch**: `integration/r1-agent-collaboration`
- **Frozen Main SHA**: `764fb98496fa40857acb07844fd09fcafa99b7d6` (100% untouched)
- **Database Scope**: Isolated PostgreSQL on port 55440 (`pg_live` untouched)

## Key Technical Specifications

### 1. `API-078`: `PUT /api/v1/opportunities/{id}/draft`
- **Payload**:
  * `title`: str (1..200 chars)
  * `description`: str (1..10000 chars)
  * `region`: str (optional, defaults to empty or existing)
  * `work_mode`: `ONSITE` | `HYBRID` | `REMOTE`
  * `eligibility`: `ALL_CANDIDATES` | `STUDENTS_ONLY` | `ACADEMIC_TRIPARTITE`
  * `capacity`: int (>= 1, must be >= `occupied_count`)
  * `contract_type`: `LABOR_PART_TIME` | `INTERNSHIP_AGREEMENT` | `ACADEMIC_TRIPARTITE`
- **Access Control & Invariants**:
  * Requester must be active member of owning organization with role `OWNER`, `HR`, or `HOST_COORDINATOR`.
  * `HOST_COORDINATOR` role restricted to `INTERNSHIP` opportunities (403 `HOST_COORDINATOR_INTERNSHIP_ONLY`).
  * Non-owning organizations or missing opportunities return uniform 404 `OPPORTUNITY_NOT_FOUND`.
  * Status must be `DRAFT` (409 `OPPORTUNITY_NOT_IN_DRAFT` / `PUBLISHED_REVISION_IMMUTABLE` per `AC-008`).
  * Atomically updates `opportunities` (`capacity`) and working `opportunity_revisions` (`title`, `description`, `region`, `work_mode`, `eligibility`, `contract_type`).
  * Returns `{"contract_id": "API-078", "opportunity_id": ..., "revision_id": ..., ...}`.

### 2. `API-079`: `PUT /api/v1/opportunities/{id}/draft/terms`
- **Payload**:
  * `is_paid`: bool
  * `salary_min`: Optional[Decimal]
  * `salary_max`: Optional[Decimal]
  * `currency`: str (default "UZS")
  * `salary_period`: Optional[str] (`HOUR` | `MONTH`)
  * `salary_basis`: Optional[str] (`GROSS` | `NET`)
  * `start_date`: date
  * `end_date`: Optional[date]
  * `program_required`: Optional[str]
- **Access Control & Invariants**:
  * `PART_TIME` opportunities must be paid (`is_paid == True`); unpaid part-time rejected with 422 `PART_TIME_MUST_BE_PAID`.
  * If `is_paid == True`: `salary_min >= 0`, `salary_period in ('HOUR', 'MONTH')`, `salary_basis in ('GROSS', 'NET')`. If `salary_max` is provided, `salary_max >= salary_min`.
  * If `end_date` is provided: `end_date >= start_date`. For `PART_TIME`, `end_date` may be null (`AC-013`).
  * Only editable while `opportunities.status == 'DRAFT'` (409 on published/closed).
  * Returns `{"contract_id": "API-079", "opportunity_id": ..., "revision_id": ..., ...}`.

### 3. `API-080`: `PUT /api/v1/opportunities/{id}/draft/schedule`
- **Payload**:
  * `schedule_policy`: `STRICT` | `NEGOTIABLE`
  * `shift_match_mode`: `ALL` | `ANY`
  * `shifts`: list of shift dicts:
    - `weekday`: int (1..7)
    - `start_minute`: int (0..1440)
    - `end_minute`: int (0..1440, > start_minute)
    - `group_code`: str (default "GROUP_A")
    - `timezone`: str (default "Asia/Tashkent")
- **Access Control & Invariants**:
  * Validates shift bounds and non-overlapping shifts within the same `(group_code, weekday)` enforcing `INV-02` / `excl_opportunity_shifts_no_overlap`.
  * Overlapping shifts in same group reject with 409 `OVERLAPPING_OPPORTUNITY_SHIFT`.
  * Atomically replaces shifts in `opportunity_shifts` for the current draft revision.
  * Updates `opportunity_revisions` (`schedule_policy`, `shift_match_mode`).
  * Returns `{"contract_id": "API-080", "opportunity_id": ..., "revision_id": ..., "shifts_count": ...}`.

## Test Matrix
1. Unit & Contract Verification (`test_opportunity_drafts_api078_079_080.py`):
   - Successfully update draft core metadata (API-078).
   - Successfully update draft terms with valid salary matrix (API-079).
   - Successfully update draft schedule with valid shift intervals (API-080).
   - Contract stamps verified on all responses.
2. Security & Adversarial Suite (`test_opportunity_drafts_adversarial.py`):
   - IDOR: Non-owning organization receives uniform 404 `OPPORTUNITY_NOT_FOUND`.
   - Role isolation: Member without HR/Owner/HostCoordinator role receives 403 `FORBIDDEN`.
   - Host coordinator barrier: `HOST_COORDINATOR` attempting to update `PART_TIME` draft rejected with 403 `HOST_COORDINATOR_INTERNSHIP_ONLY`.
   - Immutability (`AC-008`): Updating draft on `PUBLISHED` opportunity returns 409 `OPPORTUNITY_NOT_IN_DRAFT`.
   - Part-time unpaid rejection (`CAP-016`): Setting `is_paid=False` on `PART_TIME` returns 422 `PART_TIME_MUST_BE_PAID`.
   - Shift overlap rejection (`INV-02`): Overlapping intervals in same group return 409 `OVERLAPPING_OPPORTUNITY_SHIFT`.
   - Capacity bounds: `capacity < occupied_count` returns 422/409.
3. Regressions:
   - Run `test_public_discovery_api001_002.py`, `test_organization_dashboard_api068.py`, `test_opportunity_details_api005.py`.
