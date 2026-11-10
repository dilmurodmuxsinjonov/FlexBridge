# GitHub Copilot CLI Code Review: API-052 Single Placement Report Export

**Tool**: GitHub Copilot CLI 1.0.108 (copilot-runtime 0.1.2.0)  
**Date**: 2026-11-10T19:28:06Z  
**Branch**: `feature/82-placement-report-exports`  
**Target**: `integration/r1-agent-collaboration`  
**Subject**: Placement Report Export Implementation (`backend/app/services/placement_export.py`, `backend/alembic/versions/0020_placement_exports.py`, `backend/app/db/placement_exports.py`, `backend/tests/security/test_placement_exports_api052.py`, `backend/tests/security/test_placement_exports_adversarial.py`)  

---

### Verbatim Output from GitHub Copilot CLI

I’ll review the specified implementation against its surrounding API, schema, and security/audit patterns, then report only actionable findings with file and line references.

Several gaps appear in the export path beyond the requested tests; I’m checking the governing contract and existing file/audit lifecycle before finalizing severity and evidence.

**Verdict: REQUEST_CHANGES.** The host-owner precedence is implemented correctly: `resolve_export_actor` checks the candidate, then host organization authority, then mentor assignment. The findings below are independent blockers or gaps.

**Critical**
- **Storage failure becomes false success** — `backend/app/services/placement_export.py:240-274`. Any storage write or presign exception is swallowed; the code substitutes a fake test bucket/reference or `storage.local` URL, then records the file as `CLEAN` and returns a receipt. A failed export must fail explicitly, not claim that a private, clean file exists.

**Required**
- **PDF contains no report** — `backend/app/services/placement_export.py:221-237`. The PDF generator adds a blank page and metadata, but never renders the summary. The default PDF export therefore produces an empty report.
- **API-052 re-authentication is missing** — `backend/app/services/placement_export.py:120`. `account_authority` is called without `require_mfa=True`; for ordinary actors it verifies only the current session, not fresh re-authentication. The API-052 contract calls for re-auth.
- **Idempotency replay can return unusable receipts** — `backend/app/services/placement_export.py:122-137, 275-305`; `backend/app/adapters/storage.py:91-94`. Replays return the stored receipt without checking `expires_at` or renewing its URL. The URL is signed for 60 seconds, while the receipt claims 24-hour validity; later replays can return expired links, and replays after export expiry can refer to retained/deleted content.
- **Concurrent requests can fail with 500 and orphan files** — `backend/app/services/placement_export.py:122-137, 240-307`; `backend/alembic/versions/0020_placement_exports.py:28-30`; `backend/tests/security/test_placement_exports_adversarial.py:416-440`. Concurrent requests can both miss the initial lookup and write files; the unique index then rejects one insert, with no conflict recovery, leaving an unhandled database error and potentially an orphaned object. The test only requires one `201` and permits the other requests to fail.
- **Export metadata outlives the stated file retention** — `backend/alembic/versions/0020_placement_exports.py:11-22`; `backend/app/services/placement_export.py:279-305`. `summary_snapshot` and `receipt` retain candidate/report data, but the 24-hour expiry is neither enforced on replay nor used to purge these rows. The `PRIVATE_EXPORT_FILE` policy covers the file, not this persisted copy of its contents.
- **JSON object is stored with PDF content type** — `backend/app/adapters/storage.py:87-89`; `backend/app/services/placement_export.py:213-219, 248-267`. `write_private` always sends `application/pdf`, even when the file row and response identify JSON. Pass the selected MIME type through to storage.

**Consider / Optional**
- **`include_reviews` has no effect** — `backend/app/services/placement_export.py:101-109`. It changes the request fingerprint but not the summary or generated content; either implement the option or remove it from the request.
- **Academic conclusion lookup lacks a supporting index** — `backend/app/services/placement_export.py:166-177`. It filters `academic_decision_proofs` by `placement_id` and sorts by `created_at`; the migration defines no index for that access pattern. This becomes a full-table scan and sort as proof rows grow.
- **Broad authority exception handling obscures failures** — `backend/app/services/placement_export.py:34-38, 82-86`. Catch only expected authorization-denial errors so unexpected failures are not treated like ordinary “not authorized for this role” results.

The parameterized diary aggregation and format validation look sound, and the migration’s placement/idempotency indexes cover its main lookup. The concurrency test does not establish that all same-key requests return the same successful receipt.
