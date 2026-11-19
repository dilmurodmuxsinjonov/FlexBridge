# FlexBridge 1.4 — Candidate Academic Enrollments (HEMIS), Verification Status & Availability Calendar Exceptions Hub Forensic Audit Report (FB-184)

**Audit Date**: 2026-11-15  
**Auditor**: Antigravity Autonomous Master Execution & Principal Systems Technologist  
**Milestone**: FB-184 (Issue #184)  
**Branch**: `feature/184-candidate-enrollments-exceptions-hub` (targets `integration/r1-agent-collaboration`)  
**Freeze Status**: `origin/main` strictly FROZEN at commit `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md); zero mutations to main.  
**Database Isolation**: Target database strictly PgBouncer at `127.0.0.1:5432/flexbridge` with `prepare_threshold=None`; ZERO queries or mutations to `pg_live`.

---

## 1. Executive Summary

Milestone FB-184 delivers candidate higher education enrollment management (HEMIS integration, academic status tracking, enrollment lifecycle termination) and date-specific availability schedule exceptions (exams, holidays, and schedule adjustments) across 5 Next.js 16 BFF endpoints and interactive UI components in `/nomzod`.

All 10 verification phases passed 100% GREEN against live Docker staging containers with zero regressions across the regression test suite.

---

## 2. Canonical Contracts & BFF Architecture

| Canonical Contract | HTTP Method & Path | Canonical Capability | Operational Roles | BFF Endpoint | Status |
|---|---|---|---|---|---|
| **API-027** | `POST /api/v1/me/enrollments` | `CAP-004` / `CAP-012` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/enrollments` | **VERIFIED (201 Created)** |
| **API-034** | `GET /api/v1/me/enrollments` | `CAP-004` / `CAP-017` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/enrollments` | **VERIFIED (200 OK)** |
| **API-034 Detail** | `GET /api/v1/me/enrollments/{id}` | `CAP-004` / `CAP-017` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/enrollments/[id]` | **VERIFIED (200 OK)** |
| **API-027 End** | `POST /api/v1/me/enrollments/{id}/end` | `CAP-004` / `CAP-012` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/enrollments/[id]/end` | **VERIFIED (200 OK, ENDED/WITHDRAWN)** |
| **API-036** | `PUT /api/v1/me/availability/exceptions` | `CAP-005` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/availability/exceptions` | **VERIFIED (200 OK)** |
| **Institutions Catalog** | `GET /api/bff/candidate/institutions` | `PUBLIC_INFO` | `CANDIDATE`, `STUDENT` | `/api/bff/candidate/institutions` | **VERIFIED (200 OK)** |

---

## 3. UI/UX Implementation Details (`/nomzod`)

1. **Tab 4: `ENROLLMENTS` ("Talabalik & Oliy Ta'lim / HEMIS")**:
   - **4 Telemetry Metrics Cards**:
     1. *Talabalik Holati*: Active student status badge (`VERIFIED`, `DECLARED`, `PENDING`, `ENDED`).
     2. *Biriktirilgan OTM*: Higher education institution name and region.
     3. *HEMIS ID / Talaba Kodi*: Student reference code with HEMIS v3.2 indicator.
     4. *Ta'lim Dasturi*: Degree and major specification (e.g., "Dasturiy Injiniring (Bakalavr)").
   - **Yangi OTM Birikishi (Talabalik Arizasi) Form (API-027)**:
     - Institution dropdown (TATU, SamDU, O'zMU, TDTU, TDIU, or custom UUID input).
     - Program and degree input with validation.
     - Start and end date range selectors.
     - HEMIS student reference and justification textarea.
     - Automated UUID idempotency key generator.
   - **Mening Talabalik Hujjatlarim & OTM Birikishlari Table (API-034)**:
     - Formatted table/cards with status badges (`VERIFIED` [Emerald], `PENDING` [Amber], `IN_REVIEW` [Blue], `ENDED` [Zinc]).
     - Action button for "O'qishni yakunlash" triggering the end enrollment modal.
   - **End Enrollment Modal**:
     - Mandatory >= 15-character justification validation.
     - Effective end date picker.
     - Interactive confirm and cancel controls.

2. **Tab 3: `AVAILABILITY` Upgrade (API-036 Exceptions)**:
   - Preserves recurring weekly schedule (Mon-Sun) with O'zR MK 118-modda 8-hour daily limit enforcement.
   - Adds "Sana Bo'yicha Maxsus Kunlar & Imtihon Istisnolari (API-036)" section:
     - Date picker for specific calendar dates.
     - Status type selector (`AVAILABLE` vs `UNAVAILABLE` e.g. for exam days).
     - Time range inputs with automatic minute conversion.
     - Dynamic exceptions list with remove action.
     - Single-click "Istisnolarni Saqlash (API-036)" committing batch exceptions to backend.

---

## 4. Verification Evidence & Test Results

### Dedicated Staging Suite (`scripts/test_candidate_enrollments_exceptions_staging.py`):
- **Phase 1: Unauthenticated Access Rejection**: All 6 endpoints returned HTTP 401 `AUTH_REQUIRED`.
- **Phase 2: Anti-CSRF Origin Guard Rejection**: All mutating endpoints returned HTTP 403 `CSRF_ORIGIN_MISMATCH` on forged Origin headers.
- **Phase 3: Database Fixtures Setup**: Users, candidates, and institutions verified via PgBouncer.
- **Phase 4: Candidate Authentication**: Both users logged in via `/api/auth/login` and sessions elevated to MFA assurance.
- **Phase 5: API-027 Submit Student Enrollment**: HTTP 201 Created with contract_id `API-027`.
- **Phase 6: API-027 Idempotent Repeat**: Identical payload and idempotency key returned identical enrollment ID.
- **Phase 7: API-034 List & Detail**: Verified list and detail views with matching program and institution data.
- **Phase 8: End Enrollment Lifecycle**: Short reason (<15 chars) rejected with 422; valid reason marked enrollment `ENDED` / `WITHDRAWN`.
- **Phase 9: API-036 Put Availability Exceptions**: Replaced date exceptions and verified calendar merge via `GET /api/bff/candidate/availability`.
- **Phase 10: Negative Authorization & Cross-Candidate Isolation**:
  - Unverified institution rejected with HTTP 404 `ENROLLMENT_INSTITUTION_UNAVAILABLE`.
  - Foreign candidate denied detail access with HTTP 404 (IDOR anti-enumeration defense).
  - Foreign candidate denied end enrollment action with HTTP 404 (isolation defense).

**Result**: 10/10 Phases 100% GREEN.
