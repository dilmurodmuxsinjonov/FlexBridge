# ORG-CODEX-003B — reviewed departure with an existing OWNER successor

Planned scope, not acceptance evidence. Canonical DB-027 requires an independent
reviewer, append-only ownership events and a successor or recovery before losing
the last owner. Build on merged003A only after PR42 checks and merge.

One bounded transfer outcome: a current MFA OWNER asks to relinquish only their own
OWNER grant, naming a different existing active OWNER membership in the same VERIFIED
organization. The named successor independently accepts with MFA and their own current
verified contact. A separate assigned MFA MODERATOR approves the pinned revision and
evidence. The successor already holds OWNER authority:003A first handles a new staff
successor. This workflow neither creates nor automatically approves a new OWNER grant.

Persist immutable request and revision-bound append-only consent, pin both original
OWNER grant IDs and requester security version, and recheck live account, role,
membership and contact after business locks. An expired or revoked/regranted successor
grant invalidates consent; a replaced departing grant invalidates the old request.
New evidence requires new consent. Allow target decline/withdrawal, requester cancel,
independent reject and needs-info/resubmission without revoking anything.

Final approval holds organization -> case locks, current authority/contact/evidence
locks, and atomically revokes only the pinned departing OWNER grant, inserts the
canonical event (previous_membership_id=requester, new_membership_id=successor), updates
the case and appends audit. Keep membership and all other staff grants, preserve grant
history, never revive old rows. Exact matching final replay returns the same event
without needing the departing grant to be active again, but still requires current
moderator authorization and independent assignment. The departing user may read their
own historical result with current MFA after departure. Raw contacts are not exposed.

Add migration0009 with two helper tables and integrity triggers. Preserve the existing
addition/initial-owner event proof; a separate transfer branch must permit the existing
successor grant to have a different original grantor from the reviewing moderator.
SQL proof must match the exact departing revoked grant/time, successor original active
grant, approved case/revision/latest consent/reviewer metadata. Direct DB writers remain
trusted; API verifies bearer MFA and contact HMAC. Explicitly route new case kind before
the generic operator fallback and reject forged cases without proposals.

Test actual HTTP flow and access before/after departure; wrong actor/org/role/MFA,
stale revision/grant/contact/security/evidence, original grant revocation + fresh grant,
queue/detail/evidence privacy, decline/cancel/reject/needs-info, retry/conflicts,
parallel opposite transfers and generic revoke races (at least one active OWNER),
audit/deferred-proof rollback, immutable history, second-process persistence and a
populated0008->0009 upgrade. Run affected PostgreSQL modules, complete GitHub CI and
actual read-only Copilot review on pinned source.

No manual recovery when owners are inaccessible; keep that in003C with independent
evidence and human-policy design. No live registry/contact delivery, frontend or
legal identity approval. Pilot remains false; EDU follows the ownership work.
