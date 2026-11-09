# Required continuation after the current host draft

This is an ordered engineering handoff, not implemented/accepted functionality.
Keep Issue65/PR66 open until current acceptance requirements are actually met.

1. Finish host retry receipts for intake and nomination, pagination beyond100,
   and a durable candidate notification identifying each newly nominated viewer and
   exact scope. Add the matching actual HTTP/concurrency/rollback tests. Existing
   nonce receipts cover versioned consent, plan and host decisions only.
   Inspect the old `fn_validate_log_submission` CURRENT_DATE guard against the new
   explicit Asia/Tashkent service/start dates. Native Windows PostgreSQL currently
   uses local timezone; Linux/UTC boundary behavior needs actual verification and
   correction if it differs. Do not infer cross-timezone correctness from the
   existing native positives.
2. Add academic admission proof, not an exception to the ACTIVE guard. A pending
   placement must bind an exact current verified enrollment, institution, formal
   coordinator appointment/grant, active agreement/purpose/legal basis and student
   supervision. Original opportunity revision determines academic-required; the
   client cannot relabel a normal placement as academic or waive required proof.
3. Bind the named teacher's original current formal appointment/grant in immutable
   assignment proof; implement actual personal acceptance through API051. Teacher
   PASSWORD remains valid unless the existing current sensitive-role policy says
   otherwise. Revocation/new appointment must not resurrect an old assignment.
4. Make student supervision and teacher assignment creation reachable before
   ACTIVE. The existing `_academic_binding` requires ACTIVE and cannot be used as
   an admission alias. Source API098/099/101/102/103/104/105 roles and projections
   must be checked in the model/spec before registering handlers. Registration
   does not prove every method/decision branch or full institutional workflow.
5. Reconcile all overlapping academic lock paths before adding institution locks:
   derive institution scope first, then institution -> organization -> placement ->
   supervision/enrollment/agreement/assignment/material -> current account/session ->
   exact scoped appointment/grant. Existing `_locked_academic_assignment`, old
   academic creation/revoke/review and binding methods currently acquire placement
   first; a new institution-first writer could otherwise create an inversion.
   Host-only code must never acquire an institution lock after placement.
6. Extend the database start predicate and runtime host ACTIVATE to the real
   academic proofs; preserve legacy historical decisions without inventing new
   approvals. No fake post-upgrade LEGACY_IMPORT fixture or UID fallback. Replace
   `academic_fixture`'s old UID confirmation and raw track/accepted-field setup
   with a valid actual-session pending -> school bind -> teacher accept -> host
   start flow. The captured affected integration run currently has1 such fixture
   failure and47 passes; do not mark it green or remove the positive control.
7. Verify positive general/academic flows, current-role/side/private evidence,
   academic-required denials, wrong enrollment/placement/supervision/teacher,
   authority waits and both revocation serialization orders, regrant/replay/
   concurrent accept/start/revoke, atomic audit rollback and populated upgrades.
   Re-run complete current CI and inspect exact head/reviews before any merge.

API088 completion/dispute, amendment, full diary candidate authority/retrospective
policy, reports/exports, frontend, provider/live/legal/DR acceptance remain R1 work.
This handoff does not narrow the full active project goal to host admission.
