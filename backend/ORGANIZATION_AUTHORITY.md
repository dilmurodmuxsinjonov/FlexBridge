# Organization authority and transaction ordering

An early MFA preflight can reject an invalid request quickly. It cannot authorize a
later transaction: a completed logout or security change may occur while the request
waits for its organization lock.

Organization registration, verification submission/resubmission, profile edits,
membership revocation, private join detail/download, invitation creation/acceptance/
replay/revocation and member creation/approval therefore recheck current authority
inside their business transaction. Registration takes the tax-key advisory lock and
the existing organization row lock before this check; other paths take the organization
and applicable target locks. The shared guard locks the active user before the current
MFA session, matching security-management order. Current scoped membership, grant and
catalog rows are held where an existing organization role is required. Invitation
acceptance also holds current inviter authority; the recipient needs their own MFA
and verified contact, without a staff role they have not yet received.

If session revocation or security rotation commits before the authority boundary, the
business operation is denied without partial effects. If the operation acquires the
authority locks first, revocation waits for its commit or rollback. Expiry is checked
at authorization; these locks do not stop wall-clock time. Nested calls share the same
database transaction. Audit failures roll back the business effect as well.

The member governance services accept the real ActorContext, including its session;
they do not reconstruct authority from a caller-provided user ID. Bootstrap/pending
representative and invitation flows retain their existing role rules. No historical
grant is reactivated and no MFA policy or database migration is introduced here.

Tests use disposable PostgreSQL databases and real HTTP session revocation/MFA-disable
operations. Administrative grant changes use explicit trusted SQL fixtures. A synthetic
URL-signing adapter establishes whether a private download reaches signing, without
claiming a live storage integration. Direct database writers remain trusted.

Initial opportunity moderation has a separately reproduced race tracked in #48.
Other application domains and live providers/browser/DR/pilot acceptance are outside
this bounded fix; passing these tests does not establish overall pilot readiness.
