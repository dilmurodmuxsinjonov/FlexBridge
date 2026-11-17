# Implementation & Verification Plan: User Notification Preferences (API-059 / CAP-031 / DB-085 / DB-011 / AC-030)

## 1. Goal
Implement canonical endpoint `PUT /api/v1/me/notification-preferences` and query endpoint `GET /api/v1/me/notification-preferences` under capability `CAP-031` (`NOTIFICATION`), database tables `DB-085` (`notification_preferences`) and `DB-011` (`consent_events`), and acceptance criteria `AC-030` (`OPS-01`).

## 2. Invariants & Scope
1. **Ownership & Scope**: Authenticated user updates their own notification settings (`user_id == actor.user_id`).
2. **Channel & Purpose Categorization**: Supports channels `EMAIL`, `SMS`, `PUSH`, `WHATSAPP` and purposes `TRANSACTIONAL`, `SECURITY`, `MARKETING`.
3. **Mandatory Critical Delivery Guard ("Transactional/marketing alohida", AC-030)**:
   - Users cannot disable `TRANSACTIONAL` notifications across all channels (at least 1 channel must remain enabled).
   - Users cannot disable `SECURITY` notifications across all channels.
   - Disabling across all channels is rejected with 422 Unprocessable Entity (`TRANSACTIONAL_NOTIFICATION_CANNOT_BE_DISABLED`).
4. **Legal Consent Tracking (`DB-011`)**:
   - Marketing preference mutations automatically record immutable legal consent events in `consent_events` (`action='GRANTED'` or `'REVOKED'`).
   - Links `consent_event_id` in `notification_preferences`.
5. **Defaults Merging**: `GET /api/v1/me/notification-preferences` returns stored preferences merged with default system preferences.
6. **Append-Only Auditing**: Records `NOTIFICATION_PREFERENCES_UPDATED` in `audit_events`.

## 3. Verification Plan
- Unit and contract tests: `test_notification_preferences_api059.py` (8 tests).
- Adversarial and boundary tests: `test_notification_preferences_adversarial.py` (6 tests).
- Regression suite: `test_contracts.py` (16 tests) + ratings domain (18 tests). Total 48 tests.
- Database: Isolated test DB (`127.0.0.1:55440`), zero mutations on `pg_live`.
- Target branch: `integration/r1-agent-collaboration`. Main strictly frozen.
