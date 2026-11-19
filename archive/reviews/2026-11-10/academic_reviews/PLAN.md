# Issue67: exact revision academic feedback (API107)

API106 read has its own PR68 and matching-head CI. This next slice adds API107
and tightens the older daily-log alias to the same guarded writer. Full R1 and
Issue67/API108 remain open. No official grade, signature, workplace approval or
placement completion is inferred from academic feedback.

New decisions REVIEWED/NEEDS_REVISION only, actual personally named original
teacher with accepted exact plan consent, explicit revision/nonce/fingerprint,
immutable current session/auth-version/grant/appointment/revision/source evidence.
No UID fallback. The alias requires expected_revision_id and rejects stale current
pointers for new intent. Exact canonical revision can name a retained submitted
record; an old receipt can replay without making the newer pointer reviewed.

Institution -> org -> placement/current terms -> supervision/enrollment/agreement
-> assignment -> log/revision business locks precede current actual authority.
Sensitive-role MFA is rechecked after role waits. Durable actor/key intent lock
also serializes different placements and precedes current authority checks, so
session expiry during that wait cannot replay a receipt. Current parent/teacher/session checks precede
receipt lookup; new feedback requires ACTIVE placement. Replaying an old accepted
receipt after cancellation records no new decision. Revoked relationship/session
cannot replay. Changed same-key intent conflicts; new-key duplicate revision/
assignment conflicts. Review, proof, nonce receipt and audit commit together.

Forward0016 preserves every existing academic review byte-for-value and captures
only its original canonical row as LEGACY_IMPORT, with no invented human consent.
Legacy capture closes immediately. New PUBLIC proof verifies exact current source,
session, original teacher, revision and terms, including an explicit personal
academic_assignment_consents row even for imported assignments. An old accepted_at
alone cannot authorize new PUBLIC feedback. The receipt must equal the complete
canonical review snapshot, including comment/timestamps. Canonical review requires proof at
commit. Both records are immutable. Canonical94 remain unchanged, runtime125 tables.

Evidence required: actual HTTP positive/negative/replay/concurrent/stale-pointer/
current authority and wait revocation, audit rollback, direct SQL immutability/
proof failures, populated upgrade and transactional failure rollback. Preserve
failed test stages, scope-pinned read-only Copilot review, source hashes and exact
full CI before acceptance. Trusted staff/document metadata and administrative
future-amendment pointer simulation do not certify live identity or public amendment.

API108 needs source-supported conclusion semantics and a separate durable privileged
policy for official grade/signature. RAM feature flags cannot authorize that work.
Attachment sharing/scan intake, candidate diary authority, completion/amendments,
exports/frontend/providers/legal/DR/UAT/performance and full R1 remain outstanding.
