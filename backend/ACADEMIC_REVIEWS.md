# Exact-revision academic feedback (Issue67, LOG-073)

POST `/api/v1/log-revisions/{revision}/academic-reviews` requires the original
personally named current Teacher, its exact submitted revision terms consent,
academic_assignment_id, REVIEWED or NEEDS_REVISION, optional comment (10000 chars)
and explicit idempotency_key (8..128 chars). The old
`/api/v1/internship-logs/daily-logs/{id}/academic-reviews` alias also requires
placement_id and expected_revision_id and delegates to this writer. New intent
with a changed daily-log pointer fails409; exact canonical historical revision
feedback does not review a newer draft. No official grade or actor injection.

Institution -> org -> placement/current terms -> academic scope/assignment ->
log/revision -> actor/key intent lock precedes current exact material, original
Teacher and session/global sensitive-role MFA checks. Intent serialization spans
different hosts/institutions. A session that expires during the wait cannot replay.
New feedback requires ACTIVE; original receipt replay after cancellation requires
the current academic relationship/session and causes no new decision. Changed
same-key intent or new-key duplicate revision/assignment fails409. Revocation or
reappointment cannot resurrect the original grant or reveal its receipt.

Forward0016 adds academic_review_proofs (runtime125, canonical94 unchanged).
New PUBLIC evidence pins actor/session/auth version, original grant/appointment,
terms, assignment source snapshot, submitted revision snapshot, canonical review
snapshot, fingerprint and the exact canonical receipt. Existing canonical history
is captured verbatim as closed LEGACY_IMPORT with no invented credentials/intent.
Even an imported original accepted_at needs a new explicit exact-plan consent for
new PUBLIC feedback; historical minimum read remains separate. Review/proof are
immutable and a new canonical review requires proof at commit. Review, proof,
nonce receipt and audit share one transaction; audit failure rolls them all back.

Workplace approval, placement state, official grade/signature and final academic
decision are independent. API108 and its source-supported contract and separately
durable official privilege gate remain open; existing RAM flags cannot grant it.
This unit adds no attachment sharing, candidate diary authority, completion,
amendment/export/frontend/provider/legal/DR or pilot acceptance. Native staff/
document metadata and alternate populated upgrade databases are trusted fixtures,
not live identity/legal certification. Evidence and failed stages are preserved
in reviews/2026-11-10/academic_reviews; matching-head full CI is required before merge.
