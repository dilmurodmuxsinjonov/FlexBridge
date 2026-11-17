# Architectural Plan — Issue #122 (Organization Entitlements API-070 & Billing Overview API-093)

**Date**: 2026-11-12  
**Target Branch**: `integration/r1-agent-collaboration`  
**Feature Branch**: `feature/122-org-entitlements-billing`  
**Scope**: Canonical Contracts `API-070` and `API-093` under `CAP-025`, `CAP-026`, `DB-080`, `DB-081`, `DB-082`

---

## 1. Context & Business Domain
In `specs/v1_4/FlexBridge_model_1_4.json`, organizations that publish job/internship opportunities purchase tariff plans (`POST /api/v1/organizations/{org}/orders` — API-094) and pay invoices (`POST /api/v1/billing/payments/attempts`).
Upon payment capture, the system grants a `service_entitlements` record with:
- `service_kind`: Plan code (e.g. `PRO_POST_TIER_1`, `ORG_STANDARD`)
- `quota`: Total remaining post credits (decremented upon publishing new opportunities)
- `concurrent_active_limit`: Maximum simultaneously published opportunities
- `starts_at` / `ends_at`: Time-bounded validity period

Two canonical contracts remain to expose this billing status to organization managers:
1. `API-070` (`GET /api/v1/organizations/{org}/entitlements`):
   - Spec purpose: "Billing/ownerga muddat va kvota"
   - Cap: `BILLING`
   - Allowed roles: `OWNER`, `BILLING`
2. `API-093` (`GET /api/v1/organizations/{org}/billing`):
   - Spec purpose: "Plan/post, snapshot va ishlatilgan huquq"
   - Cap: `BILLING`
   - Allowed roles: `OWNER`, `BILLING`

---

## 2. Invariants & Security Boundaries
1. **Strict Role Scoping (`CAP-025`, `CAP-026`)**:
   - Only users with active `OWNER` or `BILLING` membership roles in the target organization may query entitlements or billing.
   - Non-billing roles (`HR`, `MENTOR`, `HOST_COORDINATOR`, regular candidates) receive HTTP 403 `FORBIDDEN_SCOPE`.
2. **Anti-Enumeration Uniform 404 IDOR Defense**:
   - Callers with no relationship to the organization or cross-tenant outsiders receive uniform 404 `ORGANIZATION_NOT_FOUND`.
3. **Usage & Quota Aggregation**:
   - Queries `opportunities` table in the same transaction to compute currently active published vacancies (`status = 'PUBLISHED' AND (expires_at IS NULL OR expires_at > now())`).
   - Computes total published posts count (`published_at IS NOT NULL`).
   - Computes remaining days (`max(0, (ends_at - now()).days)`).
4. **Append-Only Immutability**:
   - Read-only endpoints; zero mutations to orders, invoices, or entitlements.
5. **Frozen Main & Isolation**:
   - `main` remains 100% frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`.
   - All tests execute on port 55440 test database (`flexbridge_test`); `pg_live` untouched.
   - Zero freelance logic in R1.

---

## 3. Implementation Steps
1. Add `get_organization_entitlements` and `get_organization_billing_overview` to `BillingQuotaService` in `backend/app/services/billing.py`.
2. Mount endpoints in `backend/app/api/v1/canonical_routes.py`:
   - `@router.get("/organizations/{org}/entitlements")` -> `API-070`
   - `@router.get("/organizations/{org}/billing")` -> `API-093`
3. Implement test suites:
   - `backend/tests/security/test_billing_entitlements_api070_093.py`
   - `backend/tests/security/test_billing_entitlements_adversarial.py`
4. Run tests against port 55440 and verify 100% green.
5. Produce Copilot CLI and OpenCode consensus review artifacts.
6. Commit, push branch, create PR #123, monitor CI, squash-merge, and record LOG-109.
