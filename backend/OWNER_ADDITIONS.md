# Independently reviewed additional owners

ORG-CODEX-003A supports adding OWNER to an existing active staff membership in the same
VERIFIED organization. A new person first uses the ordinary staff invitation workflow.
Staff invitations, generic membership approval and generic verification submission still
cannot grant OWNER. Atomic transfer and recovery remain ORG-CODEX-003B work.

An existing current-MFA OWNER submits:

```text
POST /api/v1/organizations/{org}/owner-requests
Idempotency-Key: a-new-request-key
```

The strict JSON body contains `target_membership_id`, 1–5 distinct owned CLEAN PDF
`file_ids`, and a 15–4000-character `evidence_note`. Actor, target account and requested
OWNER role come from current authority and membership records. Clients cannot supply
approval, actor or role flags. The response is202/WAITING_CONSENT and grants no authority.
The proposal is bound to the exact requester OWNER grant. If that grant ends, a later
OWNER regrant cannot authorize the old proposal: cancel it and create a new request.
Same-request retries return the existing proposal; changed payloads conflict. Only one
unresolved proposal per target is accepted by the service under the organization lock.

The named target signs in with MFA and reads `GET /api/v1/me/owner-requests` (bounded
UUID pagination) or `GET /api/v1/owner-requests/{id}`. Post to its `/consent` helper with
`expected_revision`, `decision: ACCEPT`, and a current verified `contact_id` belonging
to that account. The server records an immutable consent event bound to the target,
proposal revision, security version and contact binding. Consent lasts24 hours. The
requester cannot accept for the target. Contact control is not legal identity proof.

`decision: DECLINE` has no contact field and closes the pending request, including
withdrawal of earlier pending consent. It cannot revoke an already approved OWNER grant.
Consent is also bound to the exact active staff grant used by the target. Revoking that
grant invalidates its consent even after a fresh staff invitation/regrant. The target can
give fresh consent to the still-pending proposal. Contact replacement/revocation, target security changes, expiry or new evidence require
fresh valid consent. A target may renew consent to the same pending revision. Contact
values, bindings, session identifiers and security versions are not returned in the API.

After consent, the existing operator verification queue exposes the case. A different
current-MFA MODERATOR claims it through `/operator/verification-cases/{id}/claim` and
reads its assigned evidence through the existing detail/download helpers. The requester,
target and anyone with organization membership history cannot review. API-110's `/decide`
accepts APPROVE, REJECT or NEEDS_INFO with a strict integer `expected_revision` and reason.
An explicit owner-specific branch checks consent and grants; adding a case kind to the
generic queue alone never grants authority.

APPROVE rechecks current requester OWNER authority, target staff/account, current contact,
revision and consent after business locks. It preserves other staff roles and inserts a
new OWNER grant, canonical ownership event, case decision and immutable audit in one SQL
transaction. Current user/session/platform/scope rows are held through commit. Revocation
and approval therefore serialize. Repeated matching approvals return the original event.
Approval status is proposal history; current access always uses live scoped grants.

NEEDS_INFO permits the original current OWNER to post new evidence to
`/owner-requests/{id}/resubmit`, with `expected_revision`. Target and organization cannot
change. The revision increments and returns WAITING_CONSENT; older consent/evidence remain
in history. A requester security change invalidates the old proposal: cancel and create
a new request using a new key. A changed requester grant has the same effect. `/cancel`
takes a 15–2000-character reason and requires
the original current-MFA OWNER. Rejection, decline and cancellation never grant OWNER.

Migration0008 adds immutable proposal/consent tables (runtime103, canonical94 unchanged),
protects verification evidence and ownership history from UPDATE/DELETE, and replaces
unconditional role uniqueness with a unique index for active grants. Revoked grants stay
unchanged; regrant creates a new row. Ownership events require a matching independently
approved case/grant at commit. A duplicate historical ownership event for a case or an
unexpected old constraint fails migration; records are not silently rewritten/deleted.
Destructive downgrade is unsupported; use reviewed forward recovery.

The SQL event guard checks relational case/grant/consent shape, active moderator metadata
and organization independence. Opaque bearer authentication, the actual acting MFA session
and the purpose-bound contact HMAC are enforced by the API's transaction-bound guards.
Direct database writers remain trusted; the trigger does not authenticate an HTTP caller
or independently verify the application HMAC. Restricted production database credentials
remain a separate deployment requirement. SQL constraints are not a legal identity guarantee.

Private responses use no-store and bounded bodies. Evidence and role/contact fixture
metadata used in tests do not certify a human reviewer, registry lookup, live delivery,
browser UI or production provisioning. No automatic contact notification is claimed.
`pilot_ready` remains false.
