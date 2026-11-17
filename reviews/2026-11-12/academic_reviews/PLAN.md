# Implementation & Security Review Plan: Academic Reviews & Teacher Review Queue (`API-105`, `API-106`, `API-107`)

## 1. Overview & Context
- **Issue**: #120
- **Branch**: `feature/120-academic-reviews-teacher-queue`
- **Target Branch**: `integration/r1-agent-collaboration`
- **Target Contracts**:
  - `API-105`: `GET /api/v1/me/academic-review-queue` (`ACADEMIC_VIEW` / `TEACHER`, `COORDINATOR`)
  - `API-106`: `GET /api/v1/log-revisions/{revision}/academic` (`ACADEMIC_VIEW` / `TEACHER`, `COORDINATOR`)
  - `API-107`: `POST /api/v1/log-revisions/{revision}/academic-reviews` (`LOG_ACADEMIC` / `TEACHER`)
- **Core Invariants & Rules**:
  - `AC-028` / `SEC-01`: Self-review strictly forbidden (`candidate.user_id == actor.user_id` returns 403 `SELF_REVIEW_FORBIDDEN`).
  - `AC-016`: Daily logs and reviews apply exclusively to educational `placements` (`INTERNSHIP`), never to `job_engagements`.
  - Scoping: `API-105` returns only submitted daily logs for the teacher's own active and accepted assignments (`academic_assignments.teacher_membership_id -> institution_memberships.user_id == actor.user_id`, `accepted_at IS NOT NULL`, `revoked_at IS NULL`). Zero cross-teacher leakage.
  - Anti-Enumeration: `API-106` returns uniform 404 `LOG_REVISION_NOT_FOUND` to unassigned teachers, cross-institution callers, or unauthenticated users.
  - Evidence Privacy: Only evidence marked `HOST_AND_ACADEMIC` or `ACADEMIC_ONLY` is returned to teachers; `HOST_ONLY` evidence is concealed.
  - Concurrency & DB Trigger: `API-107` acquires atomic row locks via `with_for_update()` on `log_revisions`, `daily_logs`, and `placements`. Decisions (`REVIEWED`, `NEEDS_REVISION`) are persisted in `academic_log_reviews` without mutating submitted immutable `log_revisions`.
  - Orthogonality: Academic review is independent of workplace mentor approval (`DB-060`: "workplace approval o‘rnini bosa olmaydi").
  - Audit Trail: Immutable append to `AppendOnlyAuditStore` (`ACADEMIC_LOG_REVIEWED`) and `academic_log_reviews`.
  - Response Receipts: Explicit `contract_id` stamps ("API-105", "API-106", "API-107").

## 2. Database Schema Usage
- `flexbridge.academic_assignments`: `id`, `placement_id`, `teacher_membership_id`, `supervision_id`, `institution_id`, `accepted_at`, `revoked_at`.
- `flexbridge.institution_memberships`: `id`, `institution_id`, `user_id`, `status`, `revoked_at`.
- `flexbridge.placements`: `id`, `candidate_id`, `organization_id`, `institution_id`, `status`, `current_terms_id`.
- `flexbridge.daily_logs`: `id`, `placement_id`, `local_date`, `current_revision_id`.
- `flexbridge.log_revisions`: `id`, `daily_log_id`, `revision`, `terms_id`, `author_id`, `day_type`, `summary`, `total_minutes`, `status`, `submitted_at`.
- `flexbridge.log_task_entries`: `id`, `revision_id`, `plan_task_id`, `result_text`, `minutes`.
- `flexbridge.log_evidence`: `id`, `entry_id`, `file_id`, `visibility`.
- `flexbridge.workplace_log_reviews`: `id`, `revision_id`, `decision`, `comment`, `decided_at`.
- `flexbridge.academic_log_reviews`: `id`, `revision_id`, `academic_assignment_id`, `decision`, `comment`, `decided_at`, `placement_id`.
- `flexbridge.audit_events`: Append-only audit store.

## 3. Implementation Steps
1. Service module: `backend/app/services/academic_reviews.py`
   - `list_teacher_review_queue`: Retrieves pending submitted daily logs for teacher's active assignments, excludes already reviewed logs, keyset cursor pagination over `(submitted_at ASC, id ASC)`.
   - `get_academic_log_revision_detail`: Uniform 404 IDOR check; retrieves revision metadata, tasks, time, visible evidence (`HOST_AND_ACADEMIC`, `ACADEMIC_ONLY`), and previous review history.
   - `submit_academic_review`: Atomic lock, self-review check, revision state verification, idempotency handling, insertion into `academic_log_reviews`, and audit logging.
2. Route mounting in `backend/app/api/v1/canonical_routes.py`:
   - `@router.get("/me/teacher-review-queue")` -> `API-105` (also supporting `/me/academic-review-queue`)
   - `@router.get("/log-revisions/{revision}/academic")` -> `API-106`
   - `@router.post("/log-revisions/{revision}/academic-reviews")` -> `API-107`
3. Testing Suite:
   - `backend/tests/security/test_academic_reviews_api105_106_107.py`: Unit and contract flow tests.
   - `backend/tests/security/test_academic_reviews_adversarial.py`: Adversarial edge case tests (unauthenticated, self-review 403, cross-teacher IDOR 404, non-submitted state 409, duplicate review 409, invalid decision 422, unassigned teacher 404).
4. Dual Consensus Verification:
   - Run GitHub Copilot CLI and OpenCode static security audits.
   - Compile findings and review receipts.
