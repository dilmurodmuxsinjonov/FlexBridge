# GitHub Copilot CLI Code Review: API-055 Task Entry Evidence Attachment

- **Tool**: GitHub Copilot CLI 1.0.109 (copilot-runtime)
- **Date**: 2026-11-10T21:25:47Z
- **Branch**: `feature/86-log-entry-evidence`
- **Target Branch**: strictly `integration/r1-agent-collaboration`
- **Subject Files**:
  * `backend/app/services/internship_logs.py`
  * `backend/app/api/v1/canonical_routes.py`
  * `backend/tests/security/test_log_evidence_api055.py`
  * `backend/tests/security/test_log_evidence_adversarial.py`

---

## Verbatim Findings & Remediation

### Finding 1: Concurrency Lock Contention & Superseded Revision Protection
- **Category**: DataIntegrityFailure
- **Severity**: MEDIUM | Confidence: 9/10
- **Problem**: The initial attachment flow checked that the revision was `DRAFT` while locking only the task-entry row (`with_for_update(of=t_te)`). A concurrent `API-056` submission path locks `daily_logs` and `log_revisions`, creating a window where evidence could be attached to a finalized revision or to a superseded draft revision.
- **Remediation**:
  1. Updated the query in `attach_task_evidence_api_055` to lock all three entities simultaneously: `.with_for_update(of=(t_dl, t_rev, t_te))`.
  2. Added an explicit check ensuring the task entry belongs to the current active revision:
     ```python
     if entry_row["current_revision_id"] != entry_row["revision_id"]:
         raise InternshipLogScopeError(
             "SUPERSEDED_REVISION_IMMUTABLE",
             "Cannot attach evidence to a superseded revision task entry",
             status_code=409,
         )
     ```
  3. Added adversarial test `test_superseded_revision_task_entry_rejected_409` verifying 409 rejection when attempting to attach evidence to superseded task entries.

### Finding 2: Unrecognized Evidence Visibility Values & Metadata Disclosure
- **Category**: BrokenAccessControl
- **Severity**: MEDIUM | Confidence: 8/10
- **Problem**: The evidence listing query initially filtered only `HOST_ONLY` against academic users and `ACADEMIC_ONLY` against host users. Non-standard or historical visibility tokens (such as `PRIVATE_HOST_EVIDENCE` stored in `test_academic_records.py:78`) could pass through to academic reviewers, disclosing file metadata.
- **Remediation**:
  1. Refactored the role filtering logic to be strictly fail-closed:
     ```python
     v = (r["visibility"] or "").upper().strip()
     if role in ("HOST", "MENTOR") and v in ("ACADEMIC_ONLY", "ACADEMIC_CONFIDENTIAL"):
         continue
     if role in ("TEACHER", "COORDINATOR") and v not in ("HOST_AND_ACADEMIC", "ACADEMIC_ONLY", "PUBLIC", "ALL_PARTIES"):
         continue
     ```
  2. Academic reviewers now only receive evidence explicitly designated for academia (`HOST_AND_ACADEMIC`, `ACADEMIC_ONLY`, `PUBLIC`, `ALL_PARTIES`). All other tokens (including `HOST_ONLY`, `PRIVATE_HOST_EVIDENCE`, and arbitrary values) are strictly hidden.
  3. Verified empirically in `test_stakeholder_visibility_segregation` with a real `PRIVATE_HOST_EVIDENCE` database record.

---

## Final Verdict: APPROVED
All identified edge cases and concurrency vulnerabilities were successfully resolved and empirically proven by automated regression tests against PostgreSQL 17 test cluster.
