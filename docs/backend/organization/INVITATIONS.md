# Organization invitations (ORG-CODEX-002)

Deploy migration `0005_org_invitations` before API/worker. Runtime remains 99 tables;
no new dependency is needed. The migration adds explicit role/channel/target pins,
inviter scope FK and token-digest uniqueness. Accepted legacy history is preserved;
old pending tokens with no explicit role/contact contract are revoked and need reissue.

This package implements organization invitations. Institution invitations, ownership
transfer/recovery and delivery through a live SMS/email provider remain separate work.

## Create an explicit invitation

`POST /api/v1/organizations/{org}/invitations` (`API-074`, HTTP 201) requires the
organization's current OWNER and MFA, and VERIFIED organization status:

```json
{"channel":"EMAIL","destination":"person@example.test","role_code":"HR"}
```

Channels are PHONE/EMAIL and use existing IAM contact normalization. Roles are
HR, HOST_COORDINATOR, MENTOR or explicitly BILLING. OWNER/platform roles are rejected;
self-invitation is rejected. The response returns `id`, `role_code`, `expires_at`,
one opaque `token` and a relative `preview_path`. The token has 256 bits of random
entropy and expires in 24 hours. Only purpose-bound HMAC digests are stored, not
the raw token or destination. Do not put the returned token in application logs.

The response is a shareable API link, not a claim that an SMS/email was sent.
Creating the same organization/contact/role invitation again supersedes its pending
predecessor. Different explicit roles remain separate invitations and acceptances.
Creation is limited to 20 requests per user/hour; acceptance to 30 per user/10 minutes.

If the contact already belongs to a verified account, that user/contact record is
pinned. A recycled phone bound to a different account cannot inherit the old link.
For a previously unknown contact, the account must establish its verified contact
through IAM before accepting. This uses current authoritative IAM contact records;
it does not integrate with a carrier registry or certify a person's legal identity.

## Preview and accept

`GET /api/v1/invitations/{token}` (`API-024`) is anonymous and returns only public
organization ID/name, explicit role, expiry and login/MFA requirements. It never
returns the destination, target user/contact IDs or evidence. Expired, revoked,
superseded and already accepted links return a generic 404.

`POST /api/v1/invitations/{token}/accept` (`API-025`) takes `{}` and requires login
with MFA. The actor's current verified contact must match the invitation and any
existing target pins. The inviter must still be an active OWNER of that exact
VERIFIED organization. Arbitrary actor/role/status fields in the body are rejected.

Acceptance serializes on the organization row and invitation row, activates one
scoped membership and grants only the named role. Two concurrent acceptances create
one membership/grant. A retry by the same actor returns the existing ACTIVE state;
it does not grant again. Such no-effect retries may succeed after token expiry if
the already accepted membership/grant remain active. Another actor cannot replay it.

Revoked membership/grants are never restored by an old pending/accepted link. A
fresh invitation issued after revocation may explicitly reactivate only its named
role; inactive legacy grants for other roles are not revived. Existing ACTIVE roles
are retained. The old session reads current SQL scope on its next request.

## Revoke

`POST /organizations/{org}/invitations/{id}/revoke` takes
`{"reason":"Cancel this staff invitation"}` (15–2000 characters). It requires OWNER/MFA
of that organization. It is idempotent for pending links; an accepted link must be
handled through membership revoke (API-075).

Membership revocation also invalidates pending invitations issued by that member
or targeting their account/current contacts. Independently revoked inviter OWNER
grants are rechecked on preview/accept, even without an invitation-row update.
The existing last-owner guard continues to apply.

## Token handling and deployment

The canonical contract places the token in the URL. Private responses are no-store
and no-referrer. The outer ASGI middleware masks that path segment before Uvicorn
access logging, including response errors and oversized-body handling. Native HTTP
testing verifies that the raw token is absent from Uvicorn's captured log.
Configure equivalent redaction at any edge proxy/gateway; external proxy logs and
browser UI/history are not certified by this backend-only test.

A leaked link alone does not grant membership: matching verified contact, account,
MFA and current inviter authority are also required. Initial OWNER creation continues
to use independent documentary verification, not an invitation.
