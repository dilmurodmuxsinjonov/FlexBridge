# feat(placements): implement placement completion requests and two-sided closure API-049 (#80)

## Summary of Changes
Implements **API-049** (`POST /api/v1/placements/{placement_id}/completion-requests`, capability: `PLACEMENT_CLOSE`):

1. **Database Migration (`0019_placement_completions.py`)**:
   - Creates `flexbridge.placement_completion_requests` with status check constraint (`PENDING_HOST`, `PENDING_CANDIDATE`, `COMPLETED`, `REJECTED`, `SUPERSEDED`), immutable basis snapshot, fingerprint, and idempotency key.
   - Upgrades `guard_placement_start()` trigger function to permit placement status return to `ACTIVE` from `COMPLETION_REQUESTED` upon rejection while preserving full academic track validation. Downgrade restores the previous guard.
2. **Schema Reflection & Storage**:
   - Registers `placement_completion_requests` in SQLAlchemy Core metadata (`backend/app/db/placement_completions.py`).
   - Updates storage migration baseline check to `'0019_placement_completions'`.
3. **Service Layer (`PlacementCompletionService`)**:
   - Row-level locking on `placements` and `placement_terms`.
   - **Authorization First**: Validates placement actor membership/appointment before terms check, preventing oracle probing by unauthorized callers.
   - **Actor-Bound Idempotency Replay**: Evaluates idempotency replay before status preconditions, ensuring safe receipt replaying on retries after placement reaches `COMPLETED` (returns 403 `IDEMPOTENCY_ACTOR_MISMATCH` on actor mismatch).
   - **Cartesian-Safe Diaries Basis**: Uses a CTE (`submitted_logs`) to isolate revision-level minutes summation, preventing minute multiplication across multiple academic and workplace reviews.
   - **Preconditions**: Rejects requests if any daily logs have unresolved `NEEDS_REVISION` (academic) or `CHANGES_REQUESTED` (workplace) reviews (409 `OPEN_LOGS_NEED_REVISION`). Requires explicit explanation if logged minutes are below `required_minutes` (422 `EARLY_COMPLETION_REASON_REQUIRED`).
   - **Two-Sided Closure**: Transitions placement to `COMPLETED` only upon mutual sign-off. Rejections invalidate prior pending requests as `SUPERSEDED`, requiring fresh bilateral approval.
4. **API Endpoint & DTO**:
   - `POST /api/v1/placements/{placement_id}/completion-requests` accepting `PlacementCompletionRequest`.
5. **Security & Regression Tests**:
   - 11 comprehensive tests in `test_placement_completion_api049.py` covering bilateral flows, early exit reasoning, open review blocking (academic and workplace), oracle probing resistance, idempotency replay, and Cartesian multiplication prevention.
   - Migration regressions updated across 6 test modules.

## Multi-Agent Review Receipts
- **GitHub Copilot CLI (`1.0.108`)**: Approved (`D:/Codex/FlexBridge-agents/copilot80_completion_review.md`).
- **OpenCode CLI (`1.18.29`)**: Verdict PASS (`D:/Codex/FlexBridge-agents/opencode80_completion_review.md`).

Closes #80
