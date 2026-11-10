# Codex disposition of OpenCode source opinion

OpenCode actually returned exit0 using requested opencode/nemotron-3.5-lightning-free
on the pinned three-file read-only bundle. Its six findings are retained verbatim
in opencode_proof_source_review.md. This is an opinion, not six demonstrated defects.
No production guard has been weakened to follow it.

1. **Reject:** expiry between decision and commit must reject the transaction;
   current-at-commit authority is the explicit contract. Multiple real clock reads
   do not explain loss of a still-valid savepoint. The genuine savepoint positive
   already passed in corrected11-case native selection (32.43s).
2. **Reject:** a previously captured decided_at does not become a future timestamp
   merely because commit is delayed. There is a separate deferred current-authority
   predicate. The cited service lines506–510 do not exist in this source snapshot.
   Actual expiry at commit remains an independently executed test requirement.
3. **Reject:** pg_current_xact_id returns the top-level xid8 inside subtransactions,
   unlike the original xmin child-xid defect. PostgreSQL17 primary docs state this:
   https://www.postgresql.org/docs/17/functions-info.html . Actual native tests also
   observe a different child xmin and the correct top stamp, reject old audit reuse,
   override forged stamps, and successfully commit a genuine savepoint change.
4. **Reject:** UNIQUE(prior_event_id) deliberately forbids forks. BEFORE guard
   requires the same flag and prior.version+1; a misordered chain is rejected.
   Reordering committed immutable history is outside the contract, not a repair API.
5. **Reject:** receipt comparison is semantic JSONB equality and exact timestamp
   equality. Actual HTTP positives insert and return the receipt, compare it with
   the stored JSON, then replay identically after logout/new actual MFA login and
   after a later version. The assertion that every insert fails contradicts this
   native evidence. New malformed receipt/digest tests are being run separately.
6. **Reject:** closing LEGACY_IMPORT capture immediately is an explicit requirement.
   Existing legacy origins stay LEGACY_IMPORT; a new genuine ADMIN event can certify
   their current ordinary state without rewriting the origin. The populated-upgrade
   and legacy-current-event tests exercise this. Arbitrary late imported origins
   would violate the required provenance boundary.

No finding was accepted as a demonstrated P1/P2. This disposition does not certify
the complete implementation or pilot. Full corrected native tests, independent
final source review and matching-head CI are still required before integration.
