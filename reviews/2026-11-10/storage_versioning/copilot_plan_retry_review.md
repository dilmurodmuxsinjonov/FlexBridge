Yes. Explicit version IDs paired with ETags, no ETag inference, fail-closed legacy reads,
version-pinned quarantine/downloads, and live versioning readiness form a coherent minimal fix for
the overwrite issue.

 1. Scan fencing needs a precise invariant. In the reviewed service, apply_scan only checks that the
row is still SCANNING. That does not distinguish a stale worker from a retry or newer scan that is
also SCANNING. Require an attempt/generation fence and assert that stale results cannot publish
CLEAN or replace the current private reference. Also cover retries that leave an unreferenced
private version after a write succeeds but result application fails.
 2. Preserve accepted history explicitly. The plan says accepted authority/history must not be
revoked, but the legacy-read restriction could make historical evidence inaccessible. Assert that
existing accepted roles, decisions, snapshots, and continuity remain intact, while legacy evidence
cannot support new approvals/activations without a newly pinned revision. Don’t rewrite old
snapshots or treat missing provenance as a rejection of the historical decision.
 3. Prove the full reference is bound end-to-end. Assert that HEAD requires a nonempty, non-null
VersionId and records its ETag; scan reads that exact version with the recorded ETag; and private
GET signing includes the exact private VersionId. Missing, null, or mismatched provider references
must never result in CLEAN or a key-only download.
 4. Tie readiness to the tested provider state. Assert readiness is true only when the bucket
reports versioning Enabled, and false when versioning is suspended, absent, or unavailable. The
localhost integration should exercise those states, not just verify that the application can reach
the bucket.
