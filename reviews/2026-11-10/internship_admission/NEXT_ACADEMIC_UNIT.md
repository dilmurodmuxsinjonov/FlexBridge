# Required continuation after the current host draft

This is an ordered engineering handoff. Step1 records the current host follow-up;
the remaining academic steps are unfinished, not accepted functionality.
Keep Issue65/PR66 open until current acceptance requirements are actually met.

1. LOG-068 implements host intake/nomination retry receipts, scoped pagination
   beyond100 and transactional in-app viewer notices. Same-key/changed-key/alias/
   rollback tests and105-resource pages passed at their recorded stages. Native
   SQL calendar probe reproduced the server-date defect (1failed3passed19.85s),
   then explicit Asia/Tashkent rewrite4passed21.63s. Copilot found insufficient
   predicate-drift checking; actual drift probe1failed18.38s -> exact full-predicate
   check/function comparison ->9 corrective UTC tests passed121.47s. Final broad
   UTC/source acceptance is recorded separately; do not add overlapping stages.
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
   exact scoped appointment/grant. Re-reading actual source corrected the earlier
   note: existing create and `_locked_academic_assignment` ALREADY lock institution
   before placement. Reconcile these callers when adding organization between them;
   do not apply the old erroneous placement-first description as an instruction.
   Academic host ACTIVATE must derive the bound institution before org/placement
   locks, detect a binding changed across the hint read and retry safely. Never
   acquire an institution lock after organization/placement. General host-only
   code does not need an institution lock.
6. Extend the database start predicate and runtime host ACTIVATE to the real
   academic proofs; preserve legacy historical decisions without inventing new
   approvals. No fake post-upgrade LEGACY_IMPORT fixture or UID fallback. Replace
   `academic_fixture`'s old UID confirmation and raw track/accepted-field setup
   with a valid actual-session pending -> school bind -> teacher accept -> host
   start flow. Captured full85065b1 CI has63 academic fixture failures plus3 diary
   integration failures (66failed901passed twice); exact metadata is retained.
   Calendar behavior has since been corrected; do not relabel that earlier CI
   green or remove any academic positive control.
7. Verify positive general/academic flows, current-role/side/private evidence,
   academic-required denials, wrong enrollment/placement/supervision/teacher,
   authority waits and both revocation serialization orders, regrant/replay/
   concurrent accept/start/revoke, atomic audit rollback and populated upgrades.
   Re-run complete current CI and inspect exact head/reviews before any merge.

API088 completion/dispute, amendment, full diary candidate authority/retrospective
policy, reports/exports, frontend, provider/live/legal/DR acceptance remain R1 work.
This handoff does not narrow the full active project goal to host admission.
