# Plan: Candidate Applications & Reapply System (API-006, API-029, API-039, API-040, API-041, API-044 / CAP-007)

## Metadata
- **Issue**: [#102](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/102)
- **Branch**: `feature/102-candidate-applications`
- **Base Integration Branch**: `integration/r1-agent-collaboration`
- **Frozen Main Invariant**: strictly preserved (`764fb98496fa40857acb07844fd09fcafa99b7d6`)
- **Capability**: `CAP-007` (`APPLY`)
- **Contracts**:
  * `API-006`: `POST /api/v1/opportunities/{id}/applications`
  * `API-029`: `GET /api/v1/me/applications/summary`
  * `API-039`: `GET /api/v1/me/applications`
  * `API-040`: `POST /api/v1/me/applications/{id}/reapply`
  * `API-041`: `GET /api/v1/me/applications/{id}`
  * `API-044`: `POST /api/v1/me/applications/{id}/withdraw`

---

## Architecture & Security Plan
1. **API-006 (Initial Application)**:
   - Mandatory `Idempotency-Key` header with repeat replay cache.
   - Eligibility enforcement: non-students apply without barriers (`AC-001`), `STUDENTS_ONLY` / `ACADEMIC_TRIPARTITE` requires approved student enrollment (`DB-015`).
   - Schedule matching snapshot: evaluates against active opportunity revision shifts. In `STRICT` mode, conflicts raise 422 `SCHEDULE_CONFLICT_STRICT` (`AC-013`).
   - Atomic transaction creates `applications` (status `SUBMITTED`, version `1`), `application_attempts` (`attempt_no=1`, immutable profile snapshot, schedule result), and `application_events` (`INITIAL_APPLICATION`).
   - Unique `(candidate_id, opportunity_id)` constraint respected; duplicate active applications rejected with 409 conflict.

2. **API-029 (Applications Summary Metrics)**:
   - Aggregates status counters (`submitted`, `under_review`, `interview_scheduled`, `offered`, `accepted`, `rejected`, `withdrawn`, `expired`).
   - Joins `interviews` and `offers` count strictly bounded to candidate's own applications.

3. **API-039 (List Applications)**:
   - Stable keyset cursor pagination over `(created_at, id)` with ownership validation.
   - Optional `status` filter.
   - Returns enriched opportunity summary, current attempt number, and schedule outcome.

4. **API-040 (Reapply Workflow)**:
   - Cooldown guard: at least 24 hours must have passed since the previous attempt (`429 REAPPLY_COOLDOWN_ACTIVE`).
   - Rolling rate limit: maximum 3 attempts within any rolling 30-day window (`429 REAPPLY_LIMIT_EXCEEDED`).
   - Terminal state prerequisite: active applications cannot be reapplied; must be in `REJECTED`, `WITHDRAWN`, or `EXPIRED`.
   - Increments `attempt_no`, records new snapshot, transitions status back to `SUBMITTED`, increments version, appends `APPLICATION_REAPPLIED` audit.

5. **API-041 (Application Detail)**:
   - Returns full attempt history (`application_attempts`), lifecycle event timeline (`application_events`), active interview, and active offer.
   - Strict IDOR isolation: unauthorized candidates receive uniform 404.

6. **API-044 (Withdraw Application)**:
   - Candidate withdraws application: transitions status to `WITHDRAWN`.
   - Idempotent repeat returns 200.
   - If capacity was occupied (`occupied_at`), atomically decrements `occupied_count` in `opportunities`.
   - `ACCEPTED` applications cannot be self-withdrawn (409 conflict).
