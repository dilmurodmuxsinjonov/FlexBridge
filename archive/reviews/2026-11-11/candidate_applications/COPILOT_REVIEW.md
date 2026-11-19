# Copilot Independent Code Review: Candidate Applications & Reapply System (API-006, API-029, API-039, API-040, API-041, API-044)

## Review Metadata
- **Target**: `feature/102-candidate-applications` -> `integration/r1-agent-collaboration`
- **Contracts**: `API-006`, `API-029`, `API-039`, `API-040`, `API-041`, `API-044`
- **Capability**: `CAP-007` (`APPLY`)
- **Tables**: `DB-041` (`applications`), `DB-042` (`application_attempts`), `DB-043` (`application_events`), `DB-044` (`interviews`), `DB-046` (`offers`), `DB-035` (`opportunities`), `DB-036` (`opportunity_revisions`)
- **Reviewer**: Copilot Independent Security & Governance Reviewer
- **Verdict**: **APPROVED**

---

## 1. Governance & Boundary Analysis
- [x] **Strict IDOR Isolation**:
  * All `/me/applications` routes verify ownership: `t_apps.c.candidate_id == candidate_id`.
  * Attempting to view (`API-041`), reapply (`API-040`), or withdraw (`API-044`) another candidate's application returns uniform 404 `APPLICATION_NOT_FOUND`, preventing existence leakage.
- [x] **Eligibility Verification (`AC-001`)**:
  * Non-student candidates can apply freely to `OPEN` or `ALL_CANDIDATES` opportunities.
  * Opportunities marked `STUDENTS_ONLY` or `ACADEMIC_TRIPARTITE` require an approved student enrollment (`enrollments` table), failing with 422 `STUDENT_ENROLLMENT_REQUIRED` otherwise.
- [x] **Schedule Policy Boundaries (`AC-013`)**:
  * Evaluates schedule matching against opportunity revision shifts using deterministic 28-day window (`evaluate`).
  * In `STRICT` mode, schedule conflicts raise 422 `SCHEDULE_CONFLICT_STRICT`. In `FLEXIBLE` or `NEGOTIABLE` modes, conflicts are stored in `schedule_result` without blocking submission.

---

## 2. Implementation Correctness & State Machine Integrity
- [x] **Idempotency-Key Protection (`API-006` & `API-040`)**:
  * Missing `Idempotency-Key` header rejected with 422.
  * Exact replay by the same candidate returns the existing application and attempt idempotently.
  * Attempted replay by a different user fails with 409 `IDEMPOTENCY_KEY_REUSED`.
- [x] **24-Hour Cooldown & 3/30-Day Limits (`API-040`, CAP-007)**:
  * Reapplying within 24 hours of the previous attempt raises 429 `REAPPLY_COOLDOWN_ACTIVE`.
  * Reapplying more than 3 times within a rolling 30-day window raises 429 `REAPPLY_LIMIT_EXCEEDED`.
  * Reapplying to an active application (`SUBMITTED`, `UNDER_REVIEW`, `INTERVIEW_SCHEDULED`, `OFFERED`, `ACCEPTED`) raises 409 `APPLICATION_ACTIVE`.
- [x] **Capacity Management on Withdrawal (`API-044`)**:
  * Withdrawing an application with occupied capacity (`occupied_at`) atomically decrements `occupied_count` in `opportunities`.
  * Status transitions to `WITHDRAWN`, increments version, and appends audit event.
  * Repeat withdrawal calls are idempotent (200).

---

## 3. Query Performance & Concurrency
- [x] Keyset pagination on `API-039` orders by `(created_at desc, id desc)` using base64 encoded tuples, avoiding slow deep offset scans.
- [x] Concurrency safety: `with_for_update()` row locks on `reapply` and `withdraw` prevent double-transition race conditions.
- [x] Single-roundtrip aggregation for `API-029` summary metrics prevents N+1 query overhead.

---

## Recommendation
**APPROVED**: Code strictly complies with FlexBridge v1.4 specification (`CAP-007`), Clean Architecture, and frozen-main integration requirements. Ready for merge into `integration/r1-agent-collaboration`.