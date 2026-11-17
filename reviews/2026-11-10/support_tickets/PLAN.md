# Implementation & Verification Plan: User Support Tickets & Messaging (API-063 / API-064 / CAP-033 / DB-080 / DB-081 / AC-032)

## 1. Goal
Implement canonical contracts:
- `API-063`: `GET /api/v1/me/support-tickets` (List personal support tickets) and `POST /api/v1/me/support-tickets` (Create ticket with initial message).
- `API-064`: `POST /api/v1/support-tickets/{id}/messages` (Post response message to ticket) and `GET /api/v1/support-tickets/{id}/messages` (Fetch conversation thread).
Under capability `CAP-033` (`SUPPORT`), database tables `DB-080` (`support_tickets`) and `DB-081` (`support_messages`), and acceptance criteria `AC-032` (`OPS-03`).

## 2. Invariants & Scope
1. **Ownership & Access Control**:
   - Requesters can only view, create, and append messages to tickets they authored (`requester_id == actor.user_id`).
   - Platform staff with `SUPPORT` or `ADMIN` roles can view and respond to any ticket.
   - Third parties without authority are rejected with HTTP 403 Forbidden (`SUPPORT_TICKET_FORBIDDEN`).
2. **Internal Note Segregation (`DB-081` / AC-032)**:
   - Non-staff requesters can NEVER set `internal = True`. Any attempt by non-staff to set internal note is rejected or forced to `False`.
   - Requesters querying messages NEVER receive records where `internal == True` ("Internal note foydalanuvchi eksportiga chiqmaydi").
3. **SLA Deadlines (`first_response_due_at`)**:
   - Based on priority: `URGENT` (4h), `HIGH` (12h), `NORMAL` (24h), `LOW` (48h).
4. **State Machine & Status Transitions**:
   - Ticket initial status: `OPEN`.
   - When requester appends message: status updates to `PENDING_SUPPORT`.
   - When support staff appends public message: status updates to `PENDING_USER`.
   - Resolved tickets reject new messages unless explicitly reopened (or automatically set back to `OPEN`/`PENDING_SUPPORT`).
5. **Append-Only Auditing**:
   - Records `SUPPORT_TICKET_CREATED`, `SUPPORT_MESSAGE_POSTED` in `audit_events` via `AppendOnlyAuditStore`.

## 3. Verification Plan
- Unit and contract tests: `backend/tests/security/test_support_tickets_api063_064.py` (8 tests).
- Adversarial and security tests: `backend/tests/security/test_support_tickets_adversarial.py` (6 tests).
- Combined regression: `test_contracts.py` + privacy + notification preferences + ratings domain.
- Database: Isolated test DB (`127.0.0.1:55440`), zero mutations on `pg_live`.
- Target branch: `integration/r1-agent-collaboration`. Main strictly frozen.
