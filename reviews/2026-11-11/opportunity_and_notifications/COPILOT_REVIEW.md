# Copilot Independent Code Review: Opportunity Details (API-005) & Notification Inbox (API-031)

## Review Metadata
- **Target**: `feature/100-opportunity-details-and-notifications` -> `integration/r1-agent-collaboration`
- **Contracts**: `API-005`, `API-031`
- **Capabilities**: `CAP-001` (`PUBLIC_OPPORTUNITY_DETAILS`), `CAP-031` (`NOTIFICATIONS_INBOX`)
- **Tables**: `DB-035` (`opportunities`), `DB-036` (`opportunity_revisions`), `DB-037` (`opportunity_skills`), `DB-038` (`opportunity_shifts`), `DB-021` (`organizations`), `DB-087` (`notifications`), `DB-085` (`outbox_events`)
- **Reviewer**: Copilot Independent Security & Governance Reviewer
- **Verdict**: **APPROVED**

---

## 1. Governance & Boundary Analysis
- [x] **Public & Authenticated Dual Path (`API-005`)**: `optional_actor_context` safely yields `None` for unauthenticated guests while verifying active session and assurance if credentials are provided. Invalid Bearer tokens fail early with 401 `AUTH_REQUIRED`.
- [x] **Draft Opportunity Isolation**: `PUBLISHED` and `CLOSED` opportunities are public. Non-published statuses (`DRAFT`, `PENDING_MODERATION`) enforce owning organization authority (`OWNER`, `HR`, `HOST_COORDINATOR`) or platform authority (`ADMIN`, `MODERATOR`). Non-authorized users receive uniform 404 `OPPORTUNITY_NOT_FOUND` preventing information leakage.
- [x] **User Notification Isolation (`API-031`)**: Notification queries strictly bound to `n.c.user_id == actor.user_id`. Reading actions enforce row ownership (`n.c.user_id == actor.user_id`) with `with_for_update` row locks, returning 404 on cross-user manipulation attempts.

---

## 2. Implementation Correctness & Idempotency
- [x] **API-005 Response Integrity**: Correctly calculates `vacancies_available = max(0, capacity - occupied_count)` and surfaces linked skills and shifts.
- [x] **API-031 Keyset Pagination**: Keyset cursor pagination over `(created_at, id)` with `cursor_query` anchor verification ensures stable forward navigation and terminates cleanly with `next_after=None`.
- [x] **Read Marking Idempotency**: `POST /api/v1/me/notifications/{id}/read` leaves already-read notifications unmodified and returns the existing `read_at` timestamp without duplicate audit events.
- [x] **Payload Privacy**: Outbox events without verified schema parsers never leak internal payload dictionaries.

---

## 3. Query Performance & Concurrency
- [x] Indexed queries prevent N+1 queries. Single relational round-trips used for all lookups.
- [x] Row-level locking on read status update prevents race conditions under concurrent client requests.

---

## Recommendation
**APPROVED**: No P1/P2 issues detected. Code is compliant with FlexBridge specification v1.4, clean architecture, and frozen-main integration requirements.
