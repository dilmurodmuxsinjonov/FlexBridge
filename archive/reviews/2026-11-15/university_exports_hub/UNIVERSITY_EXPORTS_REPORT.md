# FlexBridge 1.4 University Report Exports, Supervisions & Academic Agreements Hub Report (FB-170)

- **Date**: 2026-11-15
- **Issue**: [#170](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/170)
- **Branch**: `feature/170-university-exports-agreements-hub`
- **Target Integration**: `integration/r1-agent-collaboration`
- **Frozen Main Invariant**: Preserved at `764fb98496fa40857acb07844fd09fcafa99b7d6` (zero mutations to `main`).
- **Target DB**: Strictly PgBouncer on `127.0.0.1:5432/flexbridge` with `prepare_threshold=None`; ZERO queries to `pg_live`.

---

## 1. Executive Summary & Canonical Contracts Delivered

In this phase, we delivered the comprehensive **University Summary Report Exports, Supervisions & Academic Agreements Hub** in the University Portal (`/university` Tab 4: `exports` / "Hisobotlar va Shartnomalar"), fully wiring Next.js 16.4.6 BFF endpoints to backend canonical contracts:

1. **`API-100` (`POST /api/v1/institutions/{inst}/exports`)**:
   - Official institution summary report generation with export receipt.
   - Formats supported: `PDF` and `JSON`.
   - Mandatory anti-counterfeit legal disclaimer: `"Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi."`
   - Scoped aggregation metrics: `total_students_enrolled`, `total_supervisions`, `total_active_agreements`, `total_placements`, `placements_by_status`, `total_submitted_logs`, `total_logged_hours`, `total_academic_conclusions`.
   - Concurrency & security: Advisory-locked transaction idempotency (`pg_advisory_xact_lock`), step-up MFA assurance (`session.assurance == 'MFA'`), `COORDINATOR` role grant verification, and uniform 404 anti-enumeration IDOR defense.

2. **`API-098` (`GET /api/v1/institutions/{inst}/supervisions`)**:
   - Scoped student supervision listing under active institution oversight (`ACADEMIC_VIEW`).
   - Verifies verified student enrollment, agreement binding, coordinator appointment grant, and active supervision status.

3. **`API-101` (`GET /api/v1/institutions/{inst}/academic-agreements`)**:
   - Lists active institution-employer partnership agreements with authorized purpose sets (e.g. `ENGINEERING_INTERNSHIP`) and validity periods.

---

## 2. Component & Architecture Additions

### A. Next.js BFF Layer
- `frontend/src/app/api/bff/university/institutions/[inst]/exports/route.ts`:
  - Enforces session authentication (`AUTH_REQUIRED`), Anti-CSRF Origin Guard (`CSRF_ORIGIN_MISMATCH`), strict format validation (`PDF` / `JSON`), and strictly typed Pydantic `extra="forbid"` payload `{ idempotency_key, format, include_details }`.
- `frontend/src/app/api/bff/university/institutions/[inst]/supervisions/route.ts`:
  - Proxies `GET /api/v1/institutions/{inst}/supervisions`, supporting keyset pagination (`limit`, `after`).
- `frontend/src/app/api/bff/university/institutions/[inst]/agreements/route.ts`:
  - Proxies `GET /api/v1/institutions/{inst}/academic-agreements`.

### B. TypeScript Client Library (`frontend/src/lib/api.ts`)
- Added strongly-typed interfaces: `InstitutionExportSummary`, `InstitutionExportReceipt`, `StudentSupervisionItem`, `AcademicAgreementItem`.
- Added SDK functions: `generateInstitutionExport`, `fetchInstitutionSupervisions`, `fetchInstitutionAcademicAgreements`.

### C. University Portal UI (`frontend/src/app/university/page.tsx`)
- Added 4th navigation tab: `exports` ("Hisobotlar va Shartnomalar").
- **Official Report Generator Card**:
  - Format selector (`PDF` vs `JSON`).
  - Checkbox toggle for including detailed student-level log appendices.
  - One-click export trigger with loading state and error handling.
  - Live Receipt display: Anti-counterfeit disclaimer badge, download URL link with expiration timestamp, idempotency status, and real-time aggregate KPI metrics cards.
- **Student Supervisions Card**:
  - Shows student list, enrollment ID, supervision purpose, and active status badge.
- **Academic Agreements Card**:
  - Shows organization ID, contract status, and agreement ID.

---

## 3. Verification & Test Evidence

### A. Dedicated Staging Verification Suite (`scripts/test_university_exports_staging.py`)
All 10 test phases executed against the live Docker staging stack (`flexbridge-r1-frontend-1` and PgBouncer `127.0.0.1:5432`):
- **Phase 1**: Unauthenticated rejection (HTTP 401 AUTH_REQUIRED) across all 3 BFF routes -> **PASS**.
- **Phase 2**: Anti-CSRF Origin Guard rejection (HTTP 403 CSRF_ORIGIN_MISMATCH) on report export -> **PASS**.
- **Phase 3**: DB Fixtures Setup via PgBouncer with `supervision_origins` SHA-256 fingerprint constraint -> **PASS**.
- **Phase 4**: University Coordinator login via `/api/auth/login` and session elevation to `'MFA'` -> **PASS**.
- **Phase 5**: Coordinator generates PDF export via BFF (API-100), receipt and summary KPIs verified -> **PASS**.
- **Phase 6**: Coordinator generates JSON export & verifies advisory-locked idempotency replay -> **PASS**.
- **Phase 7**: Negative validation: invalid format 'XML' rejected (HTTP 422) -> **PASS**.
- **Phase 8**: Coordinator inspects student supervisions list via BFF (API-098) -> **PASS**.
- **Phase 9**: Coordinator inspects active academic agreements via BFF (API-101) -> **PASS**.
- **Phase 10**: IDOR anti-enumeration defense for unauthorized institution (404 status) -> **PASS**.

**Result**: 10/10 phases passed (100% GREEN).
