# Issue61 - candidate self-service current-session authority

Planning/reproduction only, after PR60 acceptance/merge. Pinned source370d9c3.
Codex independently reproduced5 writes and2 private reads; subsequent same-feature
caller audit also found2 legacy availability-add POST routes. Combined9 actual
HTTP/PG denial assertions failed17.20s with200/201 responses. Writes changed actual
candidate business rows/audit; private reads returned own candidate data after actual
logout200. Writes held actual candidate-profile row; old plain-read GETs used an
actual profile-table lock. CV data is trusted fixture metadata, not scanning or
public corruption. No anonymous/cross-user exploitation claim.

Earlier response-only5 failed10.01s, post-state5 failed9.35s, reads2 failed7.45s
and legacy2 failed7.35s overlap the combined9; they are not additional unique count.
No errors/skips in combined9. Holder PID pg_blocking_pids is observed, no separately
traced HTTP backend PID. Snapshot excludes IAM logout audit; compares candidate
business/audit only. Some response JSON also contains candidate_id for writes;
private_response true is interpreted as disclosure proof only for the2 GET probes.

The initial actual read-only Copilot exit0 review assessed the original7-path plan.
It is not a certificate that legacy callers could be excluded. Codex expanded scope
to9 and requested a narrow follow-up for the2 legacy routes/return snapshot behavior;
the actual follow-up completed exit0 and confirmed both legacy callers and the
post-commit response-read risk. It is source analysis, not test/SHA certification. Keep actual prompt/output/status.
No model/SHA/execution/pilot certification by the agent. Codex owns implementation;
no61 source change yet and no public API disabled as a substitute for completion.

Next: actualActorContext through all9 human paths (5 canonical writes,2 private reads,
2 legacy adds); profile/file business locks then existing account_authority current
session/sensitive assurance. READ COMMITTED profile SHARE guard for private reads;
internal schedule/matching read_snapshot unchanged. Render write return data while
still within guarded transaction. Preserve exact own candidate/file binding, active
skills/verification invalidation, CV explicit versions, interval/EXCLUDE/date and
AVAILABLE_EXTRA alias, matching snapshot/query counts. Update actual-session direct
fixtures; no actorless human fallback. Full security/positive/rollback/snapshot/CI/
review/evidence and current handoff before acceptance. Generic catalog/applications/
other domains explicit separate scope, not silently claimed fixed. Pilotfalse.
