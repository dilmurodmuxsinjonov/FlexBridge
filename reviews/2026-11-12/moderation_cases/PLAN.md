# Architectural Plan — Issue #124 (Abuse Reporting & Moderation Cases API-007)

**Date**: 2026-11-12  
**Target Branch**: `integration/r1-agent-collaboration`  
**Feature Branch**: `feature/124-moderation-cases-api007`  
**Scope**: Canonical Contract `API-007` under `CAP-034` / `DB-078`

---

## 1. Context & Business Domain
In `specs/v1_4/FlexBridge_model_1_4.json`, users across the platform (candidates, students, mentors, organization staff) need a trusted reporting mechanism to submit complaints, abuse reports, scam notices, or policy violations against published opportunities, organizations, rating submissions, or uploaded files.

Canonical Contract `API-007` (`POST /api/v1/moderation-cases`):
- **Capability**: `CAP-034` (`REPORT_ABUSE`)
- **Database Table**: `flexbridge.moderation_cases` (`DB-078`)
- **Target Fields**: Exactly one of `opportunity_id`, `organization_id`, `rating_id`, or `file_id` (enforced by `CHECK (num_nonnulls(opportunity_id, organization_id, rating_id, file_id) = 1)`).
- **SLA Computation**: `due_at` calculated from severity:
  - `CRITICAL`: 24 hours
  - `HIGH`: 48 hours
  - `MEDIUM`: 72 hours
  - `LOW`: 168 hours (7 days)

---

## 2. Invariants & Security Boundaries
1. **Authentication & Rate Limiting**:
   - Only authenticated actors can file moderation cases (`ActorContext` required).
   - Rate limiting applied per actor (`moderation-report` bucket: 30 reports/hour) to mitigate harassment or denial-of-service spam.
2. **Target Entity Validation & Anti-Enumeration Defense**:
   - The targeted entity must exist in the database (verified within the transaction).
   - Non-existent targets return uniform 404 (`OPPORTUNITY_NOT_FOUND`, `ORGANIZATION_NOT_FOUND`, `RATING_NOT_FOUND`, `FILE_NOT_FOUND`).
3. **Idempotent Replay**:
   - If a reporter submits a duplicate report for the same target and category while an active case is already `OPEN` or `IN_REVIEW`, the service returns the existing case with `is_idempotent_replay: true` to prevent spam duplicates and queue flooding.
4. **Audit Trail**:
   - Every newly submitted moderation case is permanently recorded in `flexbridge.audit_events` via `AppendOnlyAuditStore` with `action="MODERATION_CASE_REPORTED"`.
5. **Frozen Main & Isolation**:
   - `main` remains 100% frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`.
   - All tests execute on port 55440 test database (`flexbridge_test`); `pg_live` untouched.
   - Zero freelance logic in R1.

---

## 3. Implementation Steps
1. Create `ModerationCasesService` in `backend/app/services/moderation_cases.py`.
2. Mount endpoint `POST /api/v1/moderation-cases` in `backend/app/api/v1/canonical_routes.py` with `CreateModerationCaseRequest` (forbidding extra fields).
3. Implement test suites:
   - `backend/tests/security/test_moderation_cases_api007.py` (contract & persistence verification).
   - `backend/tests/security/test_moderation_cases_adversarial.py` (adversarial, validation, and boundary verification).
4. Run tests against port 55440 and verify 100% green.
5. Produce Copilot CLI and OpenCode consensus review artifacts.
6. Commit, push branch, create PR targeting `integration/r1-agent-collaboration`.
