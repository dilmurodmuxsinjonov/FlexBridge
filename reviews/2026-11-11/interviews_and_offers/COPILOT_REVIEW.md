# GitHub Copilot Static Analysis & Review: Interviews and Offers (API-042 / API-043)

## Review Date: 2026-11-11
## Reviewer: GitHub Copilot (Automated Code Review Agent)
## Target: `backend/app/services/interviews_and_offers.py`, `backend/app/api/v1/canonical_routes.py`

### Findings and Invariant Verification:

1. **Capacity Row-Locking & Race Protection (`CAP-011` / `AC-012`)**:
   - In `respond_to_offer`, the `opportunities` row is explicitly queried with `.with_for_update()`.
   - The condition `occupied_count >= capacity` is checked inside the transaction. If exceeded, a 409 `CAPACITY_EXHAUSTED` exception is raised.
   - Atomic update of `occupied_count = occupied_count + 1` is completed before the transaction commits.
   - Concurrency tests confirm that under parallel requests for a single slot, exactly one thread succeeds (200) and the second receives 409. No over-allocation occurs.

2. **Strict IDOR Mitigation**:
   - `respond_to_interview` (`API-042`) checks that the actor is either the application's candidate or an active organization member. Otherwise, an immediate 404 is returned without disclosing resource existence.
   - `respond_to_offer` (`API-043`) strictly restricts responses to the applicant candidate (`app["candidate_id"] == cand_profile["id"]`). Foreign candidates receive 404.

3. **Status Transitions and Validation**:
   - Finalized interviews (`COMPLETED`, `CANCELLED`) cannot be modified or rescheduled (409 `INTERVIEW_ALREADY_FINALIZED`).
   - Non-host users attempting to complete interviews receive 403 `HOST_RESPONSE_ONLY`.
   - Expired offers reject response attempts with 409 `OFFER_EXPIRED`.
   - Repeat identical responses are handled idempotently (200).

4. **Audit and Events Continuity**:
   - Every state change appends to `application_events` and records via `AppendOnlyAuditStore`.

### Verdict:
- **PASS**: The implementation adheres strictly to Clean Code, SOLID principles, and TZ specification requirements.
