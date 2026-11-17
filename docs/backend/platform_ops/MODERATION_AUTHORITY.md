# Initial moderation authority

Initial opportunity moderation receives the authenticated ActorContext, including the
actual session ID. The API keeps its early current-platform-role check. Inside the
service UOW, the opportunity is locked before moderator_authority checks and holds the
active user, current MFA session and current MODERATOR grant/catalog rows. Revision,
self-author and DRAFT validation then precede case/action/status/audit writes.

The global sensitive-role middleware already requires MFA for MODERATOR. This change
holds that existing policy after a business-lock wait; it does not introduce a weaker
session-only guard or construct authority from a user ID and cached role names.

A completed revocation/security/account/grant change before the guard denies the
decision without partial effects. Once the guard holds authority, database changes
that revoke it wait for commit/rollback. Expiry is evaluated at post-lock authorization;
row locks cannot stop time passing later in the transaction. Parallel initial decisions
serialize on the opportunity and retain one canonical decision. A failed write/audit
rolls back the case, action and opportunity status together. Existing appeal linkage
and independent-review rules remain.

Tests use disposable native PostgreSQL, actual HTTP session revocation/MFA disabling,
independent connection locks and explicit trusted administrative SQL mutations. Session
UUID metadata is an internal authority input, not a bearer token; API dependencies
authenticate the real opaque bearer first. Direct database writers remain trusted.
These checks do not certify every API, live providers/browser/hardware/DR or pilot
readiness. No migration, endpoint or dependency is added.
