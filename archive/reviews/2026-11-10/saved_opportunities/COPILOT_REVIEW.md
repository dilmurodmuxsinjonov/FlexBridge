# Copilot Independent Code Review: Candidate Saved Opportunities (API-004, API-037, API-038)

## Review Metadata
- **Target**: `feature/98-saved-opportunities` -> `integration/r1-agent-collaboration`
- **Contracts**: `API-004`, `API-037`, `API-038`
- **Capabilities**: `CAP-006` (`SAVE_JOB`)
- **Tables**: `DB-040` (`saved_opportunities`), `DB-035` (`opportunities`), `DB-036` (`opportunity_revisions`)
- **Reviewer**: Copilot Independent Security & Governance Reviewer

---

## 1. Governance & Boundary Analysis
- [x] **Account Authority**: Calls `account_authority(conn, actor)` verifying active account and unrevoked session under database row-locks.
- [x] **Candidate Context**: `candidate_id_for(actor)` strictly prevents non-candidate or privileged organization-only accounts from manipulating saved opportunities (403 `CANDIDATE_PROFILE_REQUIRED`).
- [x] **Cross-Candidate Access**: When a caller passes an explicit `candidate_id`, `owns_candidate(actor.user_id, target_cand_uuid)` ensures strict ownership; spoofing attempts trigger 403 `CANDIDATE_ACCESS_DENIED`.
- [x] **Cross-Candidate Deletion**: Callers attempting to delete an item belonging to another candidate receive 403 `SAVED_OPPORTUNITY_ACCESS_DENIED`, leaving the victim's saved opportunity untouched.

---

## 2. Implementation Correctness & Idempotency
- [x] **Idempotent Save (`API-004`)**: Default repeated POST requests for an already saved opportunity return the existing row (HTTP 200) without duplicating rows or violating unique constraint `(candidate_id, opportunity_id)`.
- [x] **Toggle Capability**: Spec `Toggle idempotent` is fully honored via `toggle=True`: deletes existing row or creates new row with accurate `saved` boolean flag.
- [x] **Closed Opportunity Status Preservation (`API-037`)**: Retains `opportunity.status` (`CLOSED`, `ARCHIVED`) and computes `is_closed` boolean indicator per `CAP-006` rule ("yopilganini arxiv belgisi bilan ko'rsatish").
- [x] **Repeat Deletion (`API-038`)**: Unsaving non-existent or previously deleted rows returns HTTP 204 No Content (`repeat204`).

---

## 3. Query Performance & Anti-N+1
- [x] Single relational SQL query joining `saved_opportunities` with `opportunities` and outer joining `opportunity_revisions` retrieves all required details in a single roundtrip with indexed primary keys and bounded pagination (`limit <= 100`).

---

## 4. Audit Trail Verification
- [x] `AppendOnlyAuditStore` logs `OPPORTUNITY_SAVED` and `OPPORTUNITY_UNSAVED` to `flexbridge.audit_events` with caller `actor_id` and metadata.

---

## Recommendation
**APPROVED**: No P1/P2 vulnerabilities detected. Code adheres strictly to FlexBridge architectural guidelines and frozen-main policy.
