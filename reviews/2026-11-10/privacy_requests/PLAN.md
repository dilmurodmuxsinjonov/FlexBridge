# Implementation & Verification Plan: User Privacy Requests (API-062 / CAP-032 / DB-082 / DB-084 / AC-031)

## 1. Goal
Implement canonical endpoint `POST /api/v1/me/privacy-requests` (API-062) and query endpoint `GET /api/v1/me/privacy-requests` under capability `CAP-032` (`PRIVACY`), database tables `DB-082` (`privacy_requests`), `DB-084` (`legal_holds`), `DB-083` (`retention_policies`), and acceptance criteria `AC-031` (`OPS-02`).

## 2. Invariants & Scope
1. **Ownership & Scope**: Authenticated user submits and queries their own privacy requests (`user_id == actor.user_id`).
2. **Request Kinds**:
   - `EXPORT`: Machine-readable data portability export.
   - `DELETE`: Right to erasure / account data deletion.
   - `RECTIFY`: Data rectification and correction.
3. **Statutory Fulfillment SLA (`due_at`)**:
   - `due_at = created_at + timedelta(days=30)` (30-day statutory response window).
4. **Legal Hold Enforcement (`DB-084` / AC-031)**:
   - For `DELETE` requests, the service verifies if any active `legal_holds` exist for `user_id == actor.user_id` where `released_at IS NULL` and `expires_at > now()`.
   - If an active legal hold exists, data erasure cannot proceed; the request is rejected with HTTP 422 Unprocessable Entity (`LEGAL_HOLD_ACTIVE`).
5. **Anti-Duplication / Concurrent Request Protection**:
   - If a request with the same `kind` is already in `PENDING` or `IN_PROGRESS` status for this user, reject with HTTP 409 Conflict (`PRIVACY_REQUEST_ALREADY_PENDING`).
6. **Append-Only Auditing**:
   - Records `PRIVACY_REQUEST_CREATED` in `audit_events` via `AppendOnlyAuditStore`.

## 3. Verification Plan
- Unit and contract tests: `backend/tests/security/test_privacy_requests_api062.py` (8 tests).
- Adversarial and security tests: `backend/tests/security/test_privacy_requests_adversarial.py` (6 tests).
- Full regression suite: `test_contracts.py` + notification preferences + ratings domain.
- Database: Isolated test DB (`127.0.0.1:55440`), zero mutations on `pg_live`.
- Target branch: `integration/r1-agent-collaboration`. Main strictly frozen.
