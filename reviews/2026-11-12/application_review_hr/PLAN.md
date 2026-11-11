# Application Review & HR Transitions Plan: API-082, API-083, API-084

## Target Capability: CAP-008 / APPLICATION_HR
## Target Issue: #116
## Target Branch: feature/116-application-review-hr-transitions
## Integration Base: integration/r1-agent-collaboration

### 1. Canonical Contracts & Specifications:
- `API-082`: `GET /api/v1/opportunities/{id}/applications`
  * Description: "Boshqa e’lon nomzodlari ochilmaydi" (Zero cross-opportunity leak).
  * Access: Staff of the opportunity's organization (`OWNER`, `HR`, `HOST_COORDINATOR`).
  * Role Boundary: `HOST_COORDINATOR` only allowed for `INTERNSHIP` opportunities (403 `HOST_COORDINATOR_INTERNSHIP_ONLY` on `PART_TIME`).
  * IDOR Protection: Foreign tenants or unauthenticated callers get uniform 404 `OPPORTUNITY_NOT_FOUND`.
  * Pagination: Keyset pagination on `(created_at DESC, id DESC)`, cursor support, limit 1..100.
  * Filters: optional `status` filter.
  * Response: `{"contract_id": "API-082", "opportunity_id": ..., "items": [...], "limit": ..., "has_more": ..., "next_cursor": ...}`.

- `API-083`: `POST /api/v1/applications/{id}/transition`
  * Description: "Audit va allowed transition" (State machine transitions with event logging).
  * Access: Staff of the opportunity's organization (`OWNER`, `HR`, `HOST_COORDINATOR`).
  * Role Boundary: `HOST_COORDINATOR` only allowed for `INTERNSHIP` (403 on `PART_TIME`).
  * IDOR Protection: Foreign tenants get uniform 404 `APPLICATION_NOT_FOUND`.
  * State Machine:
    - Allowed transitions:
      * `SUBMITTED` -> `REVIEWING`, `REJECTED`
      * `REVIEWING` -> `SHORTLISTED`, `INVITED_TO_INTERVIEW`, `OFFER_PENDING`, `REJECTED`
      * `SHORTLISTED` -> `INVITED_TO_INTERVIEW`, `OFFER_PENDING`, `REJECTED`
      * `INVITED_TO_INTERVIEW` -> `OFFER_PENDING`, `REJECTED`
      * `OFFER_PENDING` -> `REJECTED`
    - Disallowed transitions return 409 `INVALID_APPLICATION_TRANSITION`.
    - Terminal states (`REJECTED`, `WITHDRAWN`, `ACCEPTED`) return 409 `APPLICATION_TERMINAL_STATE`.
  * Capacity Release Invariant:
    - If transitioning to `REJECTED` and application has `occupied_at IS NOT NULL` and `released_at IS NULL`:
      * Atomically decrement `opportunities.occupied_count` (`max(0, occupied_count - 1)`).
      * Stamp `applications.released_at = now()`.
  * Event Append & Audit:
    - Insert record into `flexbridge.application_events` (`application_id`, `actor_id`, `from_status`, `to_status`, `reason`, `occurred_at`).
    - Append audit event via `AppendOnlyAuditStore`.
  * Response: `{"contract_id": "API-083", "application_id": ..., "from_status": ..., "to_status": ..., "version": ..., "transitioned_at": ...}`.

- `API-084`: `GET /api/v1/applications/{id}/hr`
  * Description: "Aynan attemptdagi minimal snapshot" (Minimal snapshot at attempt time).
  * Access: Staff of the opportunity's organization (`OWNER`, `HR`, `HOST_COORDINATOR`).
  * Role Boundary: `HOST_COORDINATOR` only allowed for `INTERNSHIP` (403 on `PART_TIME`).
  * IDOR Protection: Foreign tenants get uniform 404 `APPLICATION_NOT_FOUND`.
  * Content: Applicant profile snapshot, attempt metadata, schedule match score, timeline events from `application_events`.
  * Response: `{"contract_id": "API-084", "application_id": ..., "opportunity_id": ..., "candidate_id": ..., "status": ..., "attempt": {...}, "events": [...]}`.

### 2. Architecture & Service Design:
- New service: `backend/app/services/application_hr.py`
  * Implements `ApplicationHRService` class.
  * `list_opportunity_applications(actor, opportunity_id, status=None, limit=20, cursor=None)`
  * `transition_application_status(actor, application_id, to_status, reason=None)`
  * `get_application_hr_detail(actor, application_id)`
- Routes mounted in:
  * `backend/app/api/v1/opportunities.py`:
    `@router.get("/{id}/applications")` -> `API-082`
  * `backend/app/api/v1/canonical_routes.py`:
    `@router.post("/applications/{id}/transition")` -> `API-083`
    `@router.get("/applications/{id}/hr")` -> `API-084`
- Remove placeholder route generation for `API-082`, `API-083`, `API-084`.

### 3. Verification Plan:
- `backend/tests/unit/test_application_hr_api082_083_084.py`:
  * Contract schema tests for API-082, API-083, API-084.
  * Successful flow: list applications, transition through state machine, retrieve HR snapshot.
  * Keyset cursor pagination test.
  * Capacity release test on rejection.
- `backend/tests/security/test_application_hr_adversarial.py`:
  * Uniform 404 IDOR test on cross-tenant opportunity and application.
  * Candidate caller token rejected (403 or 404).
  * `HOST_COORDINATOR` forbidden on `PART_TIME` opportunity (403).
  * Invalid state transitions rejected with 409.
  * Terminal state modifications rejected with 409.
  * Concurrency test with `with_for_update()`.
- Run regressions across opportunities, candidate applications, engagements.
