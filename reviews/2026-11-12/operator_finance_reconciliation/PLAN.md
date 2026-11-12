# Implementation & Verification Plan: Operator Finance & Reconciliation (Issue #130)

## 1. Scope & Contracts
- **Issue**: #130
- **Branch**: `feature/130-operator-finance-reconciliation`
- **Target Branch**: `integration/r1-agent-collaboration`
- **Contracts**:
  1. `API-115`: `GET /api/v1/operator/reconciliation` (`CAP-030` / `REFUND` / `FINANCE`).
     - Keyset pagination and date window filters (`start_date`, `end_date`, `provider`, `discrepancy_only`).
     - Discrepancy detection: `amount_mismatch`, `status_discrepancy`, `missing_gateway_attempt`, `gateway_discrepancy`.
     - Zero Customer PII: Strictly no customer names, emails, phone numbers, or card data.
     - RBAC: Platform `FINANCE` / `ADMIN`. Non-staff: 403 `PERMISSION_DENIED`.
     - Response contract: `contract_id: "API-115"`, `capability: "FINANCE"`.
  2. `API-117`: `GET /api/v1/operator/finance-summary` (`CAP-038` / `FINANCE_REPORT` / `FINANCE`).
     - Financial accounting summary across date windows.
     - Aggregates: `cash_received_uzs`, `recognized_revenue_uzs`, `deferred_revenue_uzs`, `refunded_amount_uzs`, `net_revenue_uzs`, `active_subscriptions_count`.
     - Breakdown by service entitlement plans.
     - RBAC: Platform `FINANCE` / `ADMIN`. Non-staff: 403 `PERMISSION_DENIED`.
     - Response contract: `contract_id: "API-117"`, `capability: "FINANCE_REPORT"`.

## 2. Invariants & Guardrails
- **Main Freeze**: `origin/main` (`764fb98496fa40857acb07844fd09fcafa99b7d6`) is 100% frozen.
- **Database Safety**: `pg_live` untouched; isolated port 55440 test PG exclusively used.
- **Pure R1 Scope**: Zero Stage 2 freelance logic.
- **Dual Consensus**: GitHub Copilot CLI and OpenCode verification before merge endorsement.

## 3. Test Suites
- `backend/tests/security/test_operator_finance_reconciliation_api115_117.py` (Functional contract tests).
- `backend/tests/security/test_operator_finance_adversarial.py` (RBAC, PII leakage audit, invalid date ranges, discrepancy detection).
