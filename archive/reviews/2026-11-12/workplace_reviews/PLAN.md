# Implementation & Security Review Plan: Workplace Reviews & Mentor Review Queue (`API-090`, `API-091`, `API-092`)

## 1. Overview & Context
- **Issue**: #118
- **Branch**: `feature/118-workplace-reviews-mentor-queue`
- **Target Branch**: `integration/r1-agent-collaboration`
- **Target Contracts**:
  - `API-090`: `GET /api/v1/me/mentor-review-queue` (`CAP-021`, `CAP-023`, `LOG_MENTOR`)
  - `API-091`: `GET /api/v1/log-revisions/{revision}/workplace` (`CAP-021`, `CAP-023`, `LOG_MENTOR`)
  - `API-092`: `POST /api/v1/log-revisions/{revision}/workplace-reviews` (`CAP-021`, `CAP-023`, `LOG_MENTOR`)
- **Core Invariants & Rules**:
  - `AC-028` / `SEC-01`: Self-review strictly forbidden (`candidate.user_id == actor.user_id` returns 403 `SELF_REVIEW_FORBIDDEN`).
  - `AC-016`: Daily logs and mentor reviews apply exclusively to educational `placements` (`INTERNSHIP`), never to `job_engagements`.
  - Scoping: `API-090` returns only submitted daily logs for the mentor's own active and accepted assignments (`mentor_assignments.mentor_user_id == actor.user_id`, `accepted_at IS NOT NULL`, `revoked_at IS NULL`). Zero cross-mentor leakage.
  - Anti-Enumeration: `API-091` returns uniform 404 `LOG_REVISION_NOT_FOUND` to unassigned mentors, cross-tenant callers, or unauthenticated users.
  - Concurrency: `API-092` acquires atomic row locks via `with_for_update()` on `log_revisions` and `daily_logs`. Re-reviewing or reviewing non-submitted revisions returns 409 `SUBMITTED_REVISION_REQUIRED` or `REVISION_ALREADY_REVIEWED`.
  - Evidence Privacy: Only evidence marked `HOST_AND_ACADEMIC` or `HOST_ONLY` is returned to workplace mentors; `ACADEMIC_ONLY` evidence is concealed.
  - Audit Trail: Immutable append to `AppendOnlyAuditStore` (`WORKPLACE_LOG_REVIEWED`) and `workplace_log_reviews`.
  - Response Receipt: All responses stamped with explicit `contract_id` ("API-090", "API-091", "API-092").

## 2. Database Schema Usage
- `flexbridge.mentor_assignments`: `id`, `placement_id`, `membership_id`, `organization_id`, `accepted_at`, `revoked_at`.
- `flexbridge.mentor_assignment_proofs`: `assignment_id`, `origin`, `mentor_user_id`, `mentor_grant_id`.
- `flexbridge.placements`: `id`, `candidate_id`, `organization_id`, `status`, `current_terms_id`.
- `flexbridge.daily_logs`: `id`, `placement_id`, `local_date`, `current_revision_id`, `version`.
- `flexbridge.log_revisions`: `id`, `daily_log_id`, `revision`, `terms_id`, `author_id`, `day_type`, `summary`, `total_minutes`, `status`, `submitted_at`.
- `flexbridge.log_task_entries`: `id`, `revision_id`, `plan_task_id`, `result_text`, `minutes`.
- `flexbridge.log_evidence`: `id`, `entry_id`, `file_id`, `visibility`.
- `flexbridge.workplace_log_reviews`: `id`, `revision_id`, `mentor_assignment_id`, `decision`, `comment`, `decided_at`, `placement_id`.
- `flexbridge.audit_events`: Append-only audit events table.

## 3. Implementation Steps
1. Service module: `backend/app/services/workplace_reviews.py`
   - `list_mentor_review_queue`: Retrieves pending submitted daily logs for mentor's active assignments, computes `due_at` / escalation status, returns keyset paginated items.
   - `get_workplace_log_revision_detail`: Uniform 404 IDOR check; retrieves revision metadata, tasks, time, and visible evidence.
   - `submit_workplace_review`: Atomic lock, self-review check, revision state verification, idempotency handling, insertion into `workplace_log_reviews`, revision status transition, and audit logging.
2. Route mounting in `backend/app/api/v1/canonical_routes.py`:
   - `@router.get("/me/mentor-review-queue")` -> `API-090`
   - `@router.get("/log-revisions/{revision}/workplace")` -> `API-091`
   - `@router.post("/log-revisions/{revision}/workplace-reviews")` -> `API-092`
3. Testing Suite:
   - `backend/tests/security/test_workplace_reviews_api090_091_092.py`: Unit and contract flow tests.
   - `backend/tests/security/test_workplace_reviews_adversarial.py`: Adversarial edge case tests (unauthenticated, self-review 403, cross-mentor IDOR 404, non-submitted state 409, duplicate review 409, concurrency race).
4. Dual Consensus Verification:
   - Run GitHub Copilot CLI and OpenCode static security audits.
   - Compile findings and review receipts.
