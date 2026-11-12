# Package Implementation Plan: Operator Security Operations (Issue #132)

## 1. Overview & Objective
Complete canonical implementation of Package 3: Operator Audit, Security Operations, and DR Governance (`API-118`, `API-119`, `API-120`, `API-122`, `API-123`, `API-124` / `CAP-036`, `CAP-037`, `CAP-038`), bringing FlexBridge canonical contracts coverage to 132/132 (100.0%).

## 2. Contracts in Scope
1. **API-118 (`GET /api/v1/operator/audit-events`)**:
   - Query append-only audit event history with keyset cursor pagination over `(occurred_at DESC, id DESC)`.
   - Filters: `actor_id`, `action`, `object_type`, `object_key`, `start_date`, `end_date`, `limit`, `cursor`.
   - Role enforcement: `ADMIN` or `AUDITOR` platform role required. Non-staff receives 403 `PERMISSION_DENIED`.
   - Stamped Contract: `"contract_id": "API-118"`.

2. **API-119 (`POST /api/v1/operator/access-requests`)**:
   - Break-glass emergency privileged role grant with mandatory dual-control approval (`independent_approver_id != caller`).
   - Self-approval attempt strictly denied with 403 `SELF_APPROVAL_FORBIDDEN`.
   - Duration capped at 240 minutes (4 hours); excessive duration returns 422 `INVALID_DURATION`.
   - Emits `BREAK_GLASS_ROLE_GRANTED` into `audit_events`.
   - Stamped Contract: `"contract_id": "API-119"`.

3. **API-120 (`POST /api/v1/operator/users/{id}/revoke-sessions`)**:
   - Immediate emergency revocation of all active sessions for target user.
   - Uniform 404 IDOR defense for nonexistent user UUIDs (`USER_NOT_FOUND`).
   - Emits `USER_SESSIONS_EMERGENCY_REVOKED` into `audit_events`.
   - Stamped Contract: `"contract_id": "API-120"`.

4. **API-122 (`POST /api/v1/operator/incidents`)**:
   - Declare operational incident with severity (`P1`, `P2`, `P3`, `P4`) and assign incident commander.
   - Nonexistent commander returns 404 `COMMANDER_NOT_FOUND`.
   - Emits `OPERATIONAL_INCIDENT_DECLARED` into `audit_events`.
   - Stamped Contract: `"contract_id": "API-122"`.

5. **API-123 (`GET /api/v1/operator/restore-runs`)**:
   - Query disaster recovery restore runs and measure RPO/RTO against target SLA (RPO <= 24h, RTO <= 4h).
   - Stamped Contract: `"contract_id": "API-123"`.

6. **API-124 (`GET /api/v1/operator/analytics`)**:
   - Query operational platform analytics, dedup efficiency, verified start metrics, and outbox queue health.
   - Stamped Contract: `"contract_id": "API-124"`.

## 3. Operational & Security Constraints
- Target integration branch: `integration/r1-agent-collaboration`.
- Frozen `main` branch (`764fb98496fa40857acb07844fd09fcafa99b7d6`): Zero mutations.
- Isolated test PostgreSQL port: `127.0.0.1:55440`. Live production DB `pg_live` untouched.
- Pure R1 scope: Zero Stage 2 freelance code.
- Zero Customer PII leakage across all audit and analytics endpoints.
