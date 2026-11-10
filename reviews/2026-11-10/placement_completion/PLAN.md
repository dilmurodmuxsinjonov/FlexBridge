# API-049 Placement Completion Requests & Two-Sided Closure Plan

## 1. Context & Objectives
- Capability: `PLACEMENT_CLOSE` / contract: `API-049` (Issue #80).
- State Machine: Candidate requests completion or confirms host completion; Host (Owner/Mentor/Coordinator) requests completion or confirms candidate completion.
- Final state: `COMPLETED` when both sides have provided affirmative sign-offs.
- Invalidation: If either party submits `REJECT_COMPLETION`, earlier pending sign-offs become `SUPERSEDED`, and placement returns to `ACTIVE`, requiring fresh bilateral approval.
- Preconditions:
  - Placement status must be `ACTIVE` or `COMPLETION_REQUESTED`.
  - Zero open `NEEDS_REVISION` or `CHANGES_REQUESTED` daily log reviews across academic and workplace tracks.
  - Logged minutes must meet `required_minutes`, or an explicit `early_reason` must be provided.
- Concurrency & Security:
  - Authorization check executed first to prevent oracle probing of terms or placement state.
  - Idempotency replay evaluated before status preconditions so client retries after completion return the stored receipt.
  - CTE isolation in `get_placement_diaries_basis` to prevent Cartesian multiplication of minutes across multiple reviews.
  - Row-level locking on `placements` and `placement_terms`.
