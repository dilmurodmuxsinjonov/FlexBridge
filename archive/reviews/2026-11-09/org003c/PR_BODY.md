Existing active staff can request OWNER continuity only for themselves with MFA, their verified contact and clean owned evidence. A separately assigned MODERATOR recommends; a different assigned COMPLIANCE account must independently approve before any grant. One transaction commits the new OWNER grant, canonical history, immutable quorum decision, case, recovery tracking and audit. Existing OWNER/member/staff grants remain.

Fixed revision1 and exact original staff/roster/reviewer grant identities prevent stale intent revival after revoke/regrant. Stale authority/consent closes pending tracking and case together. Owner objection and applicant withdrawal compete with approval under the same locks. Generic verification/resubmission cannot act on these cases; account recovery status/reset explicitly require ACCOUNT_ACCESS.

Validation:

- 56 new native PostgreSQL tests passed across flow/security/history/transaction modules, including actual revoke/invite/reviewed-regrant lifecycles, two-review quorum, parallel retries/competing closures and late/deferred-proof rollback.
- Fresh0010 and populated0009-to-0010 upgrade passed:105-to-107 runtime tables, old predicate/transfer proof and grant/history preservation.
- An initial submit-response KeyError was fixed by reading the persisted case row. Its failure JUnit is retained; tests and SQL guards were not weakened.
- The fa40e54 baseline passed263 combined native tests and both complete393-test CI runs. Copilot then found stale matching POST receipts skipped closure; three new regression cases reproduced the defect. The original green runs did not cover those cases.
- ef4a94b closes stale matching replays under org/case/authority locks. Post-fix native9 tests passed, including replay, terminal reviewer outcomes, reset-proof isolation and parallel full flow. Both final complete401-test CI runs passed (42534534532/42534538671,219.40s/257.95s). Follow-up read-only Copilot review found no concrete replay/outcome defect; Codex verified the pinned tree and CI separately. The263 native baseline is reported separately from the final patch subset.

Human reviewers assess authority evidence; software does not certify legal identity, actual inaccessibility or document truth. Direct database writers are trusted. TestClient/synthetic contact/file metadata and second-process service reads are not live delivery/browser transport evidence. Zero-active-owner/no-staff/manual same-account recovery, providers/UI/DR and pilot acceptance remain open. Canonical inventory remains46 explicit/86 placeholders of132.

Separate confirmed residual: old API075 organization membership revoke can outlive a completed session revocation after its transient MFA preflight. A new failing HTTP regression is recorded in #47; this bounded continuity change does not resolve it.

Closes #45
