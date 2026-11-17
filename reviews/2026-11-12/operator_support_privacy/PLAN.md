# Implementation & Verification Plan: Operator Support Queue & Privacy Request Resolution (Issue #128)

## 1. Scope & Contracts
- **Issue**: #128
- **Branch**: `feature/128-operator-support-privacy`
- **Target Branch**: `integration/r1-agent-collaboration`
- **Contracts**:
  1. `API-112`: `GET /api/v1/operator/support-tickets` (`CAP-034` / `SUPPORT`).
     - Keyset cursor pagination over `(created_at DESC, id DESC)`.
     - Filters: `status`, `category`, `assignee_id`, `priority`.
     - SLA tracking: `first_response_due_at`.
     - Access: Platform `SUPPORT` / `ADMIN` / `MODERATOR`. Non-staff: 403 `PERMISSION_DENIED`.
     - Response contract: `contract_id: "API-112"`, `capability: "SUPPORT"`.
  2. `API-113`: `POST /api/v1/operator/support-tickets/{id}/messages` (`CAP-034` / `SUPPORT`).
     - Operator replies, internal notes (`internal: bool = True` hidden from users in `API-064`), optional file attachment.
     - Status updates (`IN_PROGRESS`, `PENDING_USER`, `RESOLVED`, `CLOSED`).
     - Ticket row locking (`with_for_update()`).
     - Uniform 404 `TICKET_NOT_FOUND`.
     - Append-only audit logging: `AppendOnlyAuditStore().append_audit_event(...)`.
     - Response contract: `contract_id: "API-113"`, `capability: "SUPPORT"`.
  3. `API-114`: `POST /api/v1/operator/privacy-requests/{id}/resolve` (`CAP-035` / `PRIVACY` / `SUPPORT`).
     - Operator resolution with status `RESOLVED` / `REJECTED`.
     - Self-resolution forbidden: 403 `SELF_RESOLUTION_FORBIDDEN`.
     - Legal hold enforcement: 409 `LEGAL_HOLD_ACTIVE` on `DELETE` requests if active legal hold exists.
     - Terminal state protection: 409 `PRIVACY_REQUEST_ALREADY_RESOLVED` if already resolved/rejected.
     - Uniform 404 `PRIVACY_REQUEST_NOT_FOUND`.
     - Append-only audit logging: `AppendOnlyAuditStore().append_audit_event(...)`.
     - Response contract: `contract_id: "API-114"`, `capability: "PRIVACY"`.

## 2. Invariants & Guardrails
- **Main Freeze**: `origin/main` (`764fb98496fa40857acb07844fd09fcafa99b7d6`) is 100% frozen.
- **Database Safety**: `pg_live` untouchable; isolated port 55440 test PG exclusively used.
- **Pure R1 Scope**: Zero Stage 2 freelance logic.
- **Dual Consensus**: GitHub Copilot CLI and OpenCode verification before merge endorsement.

## 3. Test Suites
- `backend/tests/security/test_operator_support_privacy_api112_113_114.py` (Functional contract tests).
- `backend/tests/security/test_operator_support_privacy_adversarial.py` (RBAC, IDOR, anti-enumeration, legal hold, internal note concealment tests).
