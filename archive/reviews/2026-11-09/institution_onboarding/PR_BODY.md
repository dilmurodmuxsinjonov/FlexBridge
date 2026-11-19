Institution appointment APIs previously returned501. This change implements signed-in
requirements, current-MFA first-institution/first-COORDINATOR claims and existing
coordinator requests for a named TEACHER. Independent assigned moderator approval
and exact-revision personal acceptance are both required before any grant.

Explicit revisions, private named/reviewer document views, consent expiry and
revocation preserve history. Current session/contact/security, original coordinator
grant, evidence and dates are rechecked after business locks. Nonblocking foreign
authority/contact locks return atomic409/retry. Retry receipts do not create extra
grants/audits. Recipient lookup follows scope checks to prevent contact enumeration.

Forward0011 adds four append-only proof tables and structural/history guards, closes
invalid legacy grants with audit provenance, and aborts normalized registry
collisions for reconciliation. Runtime111 tables; historical canonical94 unchanged.
Ordinary teacher-only PASSWORD sessions retain their existing assurance policy.

Validated source eadac1149ba66d8e34f77190c21f1c6211183a65 passed complete PostgreSQL
732-test CI twice: PR42672853806 in450.27s and push42672846232 attempt2 in508.64s.
Earlier startup failures occurred before jobs/tests with GitHub Internal server
error annotations and are recorded separately. Native upgrade/race/security and
affected-module evidence, independent red probes and actual read-only Copilot
reviews are in reviews/2026-11-09/institution_onboarding/HISOBOT.md. Native run
counts overlap; source review is not execution certification. Evidence-only head
checks follow independently before matching-head merge.

Current URLs still presign by key; actual provider version-pinned retrieval remains
open in #57. Content-addressed keys and DB snapshots are not provider immutability
proof. Additional coordinators, recovery, student admission/enrollment, frontend,
live identity/legal/provider certification and pilot acceptance are outside this
bounded package. Canonical registration49 explicit/83 placeholders is not acceptance.

Closes #55
