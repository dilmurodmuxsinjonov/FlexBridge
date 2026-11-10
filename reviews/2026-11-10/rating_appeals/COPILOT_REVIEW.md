# GitHub Copilot CLI Code Review: Rating Appeals (API-058 / CAP-028 / DB-067 / AC-025)

**Reviewer**: GitHub Copilot CLI `1.0.109`  
**Date**: 2026-11-10  
**Target Branch**: `integration/r1-agent-collaboration`  
**Feature Branch**: `feature/90-rating-appeals`  
**Scope**: `canonical_routes.py`, `user_ratings.py`, `test_rating_appeals_api058.py`, `test_rating_appeals_adversarial.py`  
**Verdict**: **APPROVED** (Confidence: 10/10)

---

### 1. Specification & Contract Conformance
- **Canonical Route**: `POST /api/v1/ratings/{id}/appeals` accurately mounted with `status_code=201`.
- **Capability Compliance**: Matches `CAP-028` (`RATING_APPEAL`) and `AC-025` (`RAT-05`).
- **Target Resolution**: Resilient lookup resolving either `rating_submissions.id` or `rating_revisions.id`.
- **Payload Schema**: Pydantic model `RatingAppealPayload` enforces string boundaries (10 to 4000 chars) and extra fields ignored.

### 2. Security & Access Control
- **Party Authority ("Baho tomoni")**: Strictly validates that the actor is `target_user_id`, `rater_id`, active member of `target_org_id` with management role, or platform `MODERATOR`.
- **Anti-Retaliation & Independent Review**:
  - `resolve_rating_appeal` guarantees reviewer is independent (`reviewer != appellant` and `reviewer != rater`), enforcing AC-028 (`APPEAL_REVIEWER_CONFLICT`).
- **14-Day Boundary**: Calculates elapsed time against `published_at`, `publish_after`, or `submitted_at` with strict timezone-awareness.
- **Fail-Closed Auditing**: Calls `AppendOnlyAuditStore` to persist audit records for all dispute submissions and resolutions.

### 3. Database & Transaction Integrity
- **Transactional Atomicity**: All state mutations (`rating_appeals`, `moderation_cases`, `rating_submissions`, and `rating_aggregates`) occur within a single database transaction.
- **Unique Constraint Adherence**: Avoids violating `one_placement_rating` or `one_user_aggregate`.
- **No Direct Mutation on Frozen Tables**: All writes adhere to migration `0020_placement_exports` baseline.

### 4. Test Quality & Coverage
- Comprehensive suite of 15 tests covering normal execution, unauthenticated calls, expired windows, third-party rejections, idempotent replays, conflicting attempts, $n < 5$ score withholding, and reviewer conflict scenarios.
- All 15 tests pass green in 85.74s; full domain passes 29/29 tests in 153.43s.

**Conclusion**: Ready for merge into `integration/r1-agent-collaboration`.
