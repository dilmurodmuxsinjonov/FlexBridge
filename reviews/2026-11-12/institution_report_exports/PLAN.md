# Architectural & Security Review Plan — Issue #126 (Institution Summary Report Exports API-100)

**Date**: 2026-11-12  
**Target Branch**: `integration/r1-agent-collaboration` (main is 100% frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`)  
**Feature Branch**: `feature/126-institution-report-exports`  
**Scope**: Canonical Contract `API-100` (`POST /api/v1/institutions/{inst}/exports`) under `CAP-018`, `CAP-026`, `REPORT_EXPORT`

---

## 1. Context & Business Domain
In `specs/v1_4/FlexBridge_model_1_4.json`, higher educational institutions supervise student internship placements across host organizations.
Educational coordinators require periodic summary exports of their institution's active placements, enrolled students, supervisions, institutional agreements, submitted daily logs, hours worked, and academic decisions.

Contract Specification:
- **ID**: `API-100`
- **Method / Path**: `POST /api/v1/institutions/{inst}/exports`
- **Capability**: `REPORT_EXPORT` (`CAP-018`, `CAP-026`)
- **Authorized Roles**: `COORDINATOR` (and platform `ADMIN`/`OPERATOR`)
- **Description**: "Muassasa kesimidagi yig'ma hisobot eksporti — qat'iy INSTITUTION doirasi, step-up re-auth va audit bilan"

---

## 2. Invariants & Security Guardrails
1. **Strict Role Scoping & Step-Up Re-Auth (`CAP-018`)**:
   - Only active `COORDINATOR` members with step-up MFA assurance can initiate an institution export (`institution_authority(conn, actor, inst_id, 'COORDINATOR', require_mfa=True)`).
   - Internal unauthorized members (`TEACHER`, student) receive HTTP 403 `INSTITUTION_SCOPE_FORBIDDEN`.
2. **Anti-Enumeration Uniform 404 IDOR Defense**:
   - Callers with no relationship to the institution, cross-tenant coordinators, or non-existent/unverified institutions receive uniform HTTP 404 `INSTITUTION_NOT_FOUND`.
3. **Report Formats & Mandatory Disclaimer (`CAP-026`)**:
   - Permitted formats: `PDF` and `JSON`. Unsupported formats return HTTP 422 `INVALID_EXPORT_FORMAT`.
   - Mandatory official disclaimer: `"Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi."` embedded in document bytes, PDF metadata, and JSON summary.
4. **Transactional Safety & Idempotency**:
   - Concurrency protection via `pg_advisory_xact_lock` on institution + idempotency key.
   - Idempotent replaying returns identical receipt without duplicate file generation.
   - File registered in `files` table under `retention_class='PRIVATE_EXPORT_FILE'`.
   - Audit trail recorded in `AppendOnlyAuditStore` (`INSTITUTION_REPORT_EXPORTED`).
   - Contract stamp: `"contract_id": "API-100"`.
5. **Frozen Main & Isolation**:
   - `main` remains 100% frozen. Target is `integration/r1-agent-collaboration`.
   - All tests execute on port 55440 test PG (`pg_live` untouched). Zero Stage 2 freelance logic in R1.

---

## 3. Implementation Files
1. Service: `backend/app/services/institution_exports.py`
2. API Router: `backend/app/api/v1/canonical_routes.py` (`@router.post("/institutions/{inst}/exports")`)
3. Test Suites:
   - `backend/tests/security/test_institution_exports_api100.py`
   - `backend/tests/security/test_institution_exports_adversarial.py`
4. Dual Consensus Artifacts:
   - `reviews/2026-11-12/institution_report_exports/COPILOT_REVIEW.md`
   - `reviews/2026-11-12/institution_report_exports/OPENCODE_REVIEW.md`
   - `reviews/2026-11-12/institution_report_exports/REVIEW_SUMMARY.md`
