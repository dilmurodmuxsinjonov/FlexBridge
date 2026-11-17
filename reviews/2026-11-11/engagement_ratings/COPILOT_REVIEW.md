# GitHub Copilot Static Analysis & Review: Engagement Ratings (API-047 / API-048)

## Review Date: 2026-11-11
## Reviewer: GitHub Copilot CLI 1.0.109 (Automated Code Review Agent)
## Target: `backend/app/services/user_ratings.py`, `backend/app/services/placement_admission.py`, `backend/app/api/v1/canonical_routes.py`

### Findings and Invariant Verification:

1. **AC-024 Bilateral Double-Blind Evaluation Semantics (`CAP-027` / `AC-024`)**:
   - In `submit_engagement_rating_api_047`, the `job_engagements` row is locked with `.with_for_update()`, preventing unblinding race conditions.
   - When the first party (candidate or employer) submits, their rating is held in `PENDING_BLIND` status with `publish_after = now + 14 days`.
   - When the peer party submits, both submissions atomically transition to `PUBLISHED` status with `publish_after = now()`.
   - Aggregate ratings are recomputed atomically upon unblinding, respecting the $n \ge 5$ privacy threshold under `AC-023`.

2. **Anti-Spoofing and Uniform 404 IDOR Protection**:
   - Actor roles are resolved strictly via verified server-side identity: `applications.candidate_id` -> `candidate_profiles.user_id` and `opportunities.organization_id` -> `org_memberships`.
   - Third-party candidates and foreign employers attempting to rate or inspect unassociated engagements receive uniform 404 `ENGAGEMENT_NOT_FOUND`, preventing resource existence probing.
   - Self-rating is impossible due to database check constraint `CHECK (target_user_id IS NULL OR target_user_id <> rater_id)`.

3. **Lifecycle Guard & Idempotency**:
   - Non-completed engagements (`ACTIVE`, `PENDING_START_CONFIRMATION`, etc.) are rejected with 409 `ENGAGEMENT_NOT_COMPLETED`.
   - Identical re-submissions return 200 with `idempotent_replay: true`.
   - Conflicting score modifications return 409 `RATING_ALREADY_SUBMITTED`.

4. **API-048 Placement Acceptance Contract Conformance**:
   - `_consent` in `placement_admission.py` attaches `"contract_id": "API-048"` to candidate acceptance receipts while maintaining full backward compatibility.

### Verdict:
- **PASS**: Meets all architectural, clean code, cryptographic, and security requirements. Zero P1/P2 defects found.
