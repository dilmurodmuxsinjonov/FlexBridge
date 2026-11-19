# OpenCode 1.18.29 Code Review — Issue #120 (Academic Reviews & Teacher Review Queue)

**Date**: 2026-11-12  
**Target Branch**: `integration/r1-agent-collaboration`  
**Feature Branch**: `feature/120-academic-reviews-teacher-queue`  
**Reviewer**: OpenCode 1.18.29 Autonomous Review Engine  
**Status**: **APPROVED (100% Pass)**

---

## 1. Scope & Invariants Assessed
- Canonical Contracts:
  * `API-105`: `GET /api/v1/me/academic-review-queue` (with canonical alias `/api/v1/me/teacher-review-queue`) under `CAP-024` (`ACADEMIC_VIEW`)
  * `API-106`: `GET /api/v1/log-revisions/{revision}/academic` under `CAP-024` (`ACADEMIC_VIEW`)
  * `API-107`: `POST /api/v1/log-revisions/{revision}/academic-reviews` under `CAP-022` (`LOG_ACADEMIC`)
- Cross-Domain Isolation:
  * Dual-track review independence: Teacher academic reviews (`academic_log_reviews`) are completely orthogonal to workplace mentor reviews (`workplace_log_reviews`). Neither overwrites or replaces the other (`DB-060`).
  * Database trigger `fn_guard_log_revisions()` immutability: Submitted daily log revisions remain strictly immutable; decisions are recorded exclusively in `academic_log_reviews` with cryptographic proofs in `academic_review_proofs`.
  * Evidence visibility scoping: Teachers strictly access only evidence with `visibility IN ('HOST_AND_ACADEMIC', 'ACADEMIC_ONLY')`; employer-confidential evidence (`HOST_ONLY`) is concealed.
  * Self-review prohibition (`AC-028` / `SEC-01`): Verified that candidates cannot review their own submissions (403 `SELF_REVIEW_FORBIDDEN` / `REVISION_AUTHOR_FORBIDDEN`).
  * Anti-enumeration IDOR prevention: Unassigned teachers and cross-institution callers receive uniform 404 `LOG_REVISION_NOT_FOUND` / `ACADEMIC_REVISION_NOT_FOUND`.
  * Cache security: `IAMHTTPMiddleware` enforces `Cache-Control: no-store`, `Pragma: no-cache`, `Referrer-Policy: no-referrer` across all teacher review paths.

---

## 2. Test Verification
- `backend/tests/security/test_teacher_review_queue_alias.py`: 1/1 passed.
- `backend/tests/security/test_academic_views.py`: 5/5 passed.
- `backend/tests/security/test_academic_records.py`: 9/9 passed.
- `backend/tests/security/test_academic_reviews.py`: 27/27 passed.
- **Total Suite**: 42/42 tests passed 100% green against isolated PostgreSQL (port 55440); `pg_live` untouched.

---

## 3. Consensus Recommendation
Code, security invariants, middleware configuration, and test coverage meet production standards. Ready for squash-merge into `integration/r1-agent-collaboration`.
