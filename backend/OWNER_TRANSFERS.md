# Reviewed OWNER departure

This bounded flow lets an existing OWNER relinquish only their own OWNER role after
another existing OWNER accepts the succession and an independently assigned moderator
approves the evidence. A new staff successor first completes OWNER_ADDITIONS.md.
Recovery for inaccessible owners remains unimplemented. This is not pilot acceptance.

1. Current MFA OWNER sends `POST /api/v1/organizations/{org}/owner-transfers` with
   `Idempotency-Key`, `target_membership_id`, owned clean PDF `file_ids` and an
   `evidence_note`. The target must be a different active OWNER in that VERIFIED org.
2. The named successor finds their requests at `GET /api/v1/me/owner-transfers` and
   reads `GET /api/v1/owner-transfers/{id}`. With current MFA, they send `POST .../consent`
   with strict integer `expected_revision`, `decision: ACCEPT` and their own current
   verified `contact_id`. Consent lasts at most24h. DECLINE has no contact field and
   closes the request; it can withdraw consent before a final decision.
3. An unrelated current MFA MODERATOR claims the ordinary verification case, reviews
   its scoped evidence and `owner_transfer` detail, and decides through canonical
   API110. No participant or organization member may review. NEEDS_INFO requires
   `POST .../resubmit` by the original owner and fresh consent to the new revision.
   The requester may `POST .../cancel` with a reason before final approval.
4. APPROVE checks the exact departing and successor grant IDs, active users and
   memberships, requester security version, current consent/contact, verified org and
   clean owned evidence again under locks. One SQL transaction revokes only the
   departing OWNER grant, records the canonical previous/successor ownership event,
   decides the case and appends audit. Membership and other staff roles remain.

Grant replacement never revives a prior transfer. Both original grants are pinned in
the immutable proposal, so revoking/regranting either requires a new proposal. A new
verified contact or successor security version can require renewed consent while the
original grants remain unchanged. Payloads cannot choose actor, grant, role or approval.

Matching request retries return a receipt after departure with current MFA; they do
not repeat the mutation. The original participants can read their historical result
with current MFA. Other organization access still requires current roles. Assigned
moderator retries return the same event with current moderator authority. Queues and
details expose no raw contacts, HMAC digests or session/grant proof identifiers.

Migration0009 adds two helper tables (runtime105, canonical94 unchanged). Proposal and
consent rows and ownership/evidence history are immutable. Events with no previous
membership retain the existing initial/addition SQL proof. Events with a previous
membership use a dedicated transfer proof, including exact revoked source timestamp
and original active successor grant; no new OWNER grant is inserted. Organization
locks serialize approval, opposite departures and ordinary membership revocation.

SQL guards enforce relational integrity. Direct database writers are trusted; actual
opaque bearer/MFA checks and contact HMAC belong to the API. Synthetic fixtures and
TestClient tests do not verify registry identity, live contact delivery, browser flows,
production provisioning or disaster recovery. Validation results are recorded separately
under reviews/2026-11-09/org003b as they complete.
