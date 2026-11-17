# Organization onboarding (ORG-CODEX-001)

Run `alembic upgrade head` before deploying API/worker; use the current head listed
in README. Migration `0004_org_onboarding` introduced this package (99 runtime tables)
and adds normalized tax-ID
uniqueness, immutable organization verification submissions and five ORG role-catalog
entries. It creates no privileged users, memberships or grants. A MODERATOR must be
provisioned independently through the deployment administration process.

Mutations and operator review require a current MFA session. Ordinary authenticated
candidates can start onboarding; the OWNER/HOST intent in the canonical role matrix
does not give them a verified role. Pending memberships never grant organization rights.
Private organization/operator responses are no-store, with bounded request bodies.

## Submit an organization

`POST /api/v1/organizations` (`API-065`, HTTP 202):

```json
{"tax_id":"123456789","legal_name":"Example legal company","public_name":"Example",
 "region":"Tashkent","file_ids":["YOUR_CLEAN_PDF_UUID"],
 "evidence_note":"Evidence of authorized representation","membership_role":"HR"}
```

Use the existing private file upload/scan pipeline first. One to five distinct, own,
nondeleted CLEAN PDFs are required; the note is 15–4000 characters. Client-supplied
status, owner, reviewer and role grants are rejected. `website` accepts HTTP(S) URLs;
the backend does not fetch them.

Tax-ID normalization removes spaces/hyphens and preserves leading zeros. The API
accepts 3–32 ASCII digits as a bounded identifier format; this is not an official
STIR-format/registry validation claim. The reviewer must check the actual evidence.
An advisory lock and a unique expression index serialize concurrent duplicates.

For a new identity, the response contains `organization_id`, `membership_id` and
`case_id`; membership is PENDING_VERIFICATION, with no OWNER grant. A repeated request
by that same member returns the existing IDs. It does not overwrite organization data.

For an existing verified organization, a new applicant receives only a
PENDING_APPROVAL join request. `membership_role` explicitly selects HR,
HOST_COORDINATOR, MENTOR or BILLING (default HR); OWNER is not selectable here.
Even a verified organization with no active owner stays out of bootstrap and needs
the separate administrative ownership-recovery process. A competing first-owner
case cannot install another owner after one bootstrap approval has committed.

`GET /organizations/{id}/verification` (`API-067`) returns the actor's own cases,
revisions, reasons, target due dates and membership status. It never lists another
applicant's private case. `GET /organizations/{org}/capabilities` (`API-072`) returns
separate capability statuses to a current member/applicant without granting those rights.

## Independent review and evidence

- `GET /operator/verification-cases` (`API-109`) lists the moderator's assigned,
  open ORG cases. `?unassigned=true` exposes only the metadata needed to claim work;
  `limit` is 1–100. Non-ORG cases remain outside this queue's implemented scope.
- `POST /operator/verification-cases/{id}/claim` assigns an open case atomically.
  The actor needs a live PLATFORM MODERATOR grant and MFA. The requester, any person
  with an organization membership record, and a different assigned reviewer cannot claim it.
- `GET /operator/verification-cases/{id}` returns organization details, immutable
  submissions and evidence only to that assigned moderator while IN_REVIEW.
- `GET /operator/verification-cases/{id}/files/{file_id}/download` checks the same
  current authority, case/evidence linkage and the file's current CLEAN/ownership/deletion
  state. It returns a 60-second signed URL and records authorization in audit.
- `POST /operator/verification-cases/{id}/decide` (`API-110`):

```json
{"decision":"APPROVE","expected_revision":1,
 "reason":"Independent documentary verification completed"}
```

Decisions are APPROVE, REJECT or NEEDS_INFO; reason is 15–2000 characters.
Only the assigned independent moderator can decide. A stale revision or replay
returns 409. Approval rechecks the requester's active account/membership, scope and
current evidence. The business effect, decision, ownership event/grant and audit
share one transaction and organization lock.

The initial representative approval activates the requested membership as OWNER
and marks the organization VERIFIED. It grants neither JOB_EMPLOYER nor INTERNSHIP_HOST.
Prior decision reasons/revisions remain in append-only audit and immutable submissions.

NEEDS_INFO allows `POST /organizations/{id}/verification` (`API-066`) with the same
`case_id`, its `kind`, new `file_ids` and `evidence_note`. Only the original requester
can resubmit; revision increments. Existing profile-change proposals stay unchanged
when evidence is revised. A REJECT is final for that case; appeal/recovery is separate.
The due-date target is two weekdays, skipping weekends. No holiday calendar or SLA
guarantee is implied.

## Separate capabilities and material changes

An active OWNER or HOST_COORDINATOR submits a capability with API-066:

```json
{"kind":"JOB_EMPLOYER","file_ids":["YOUR_CLEAN_PDF_UUID"],
 "evidence_note":"Evidence supporting employer capability"}
```

Use INTERNSHIP_HOST for the other capability. Each gets its own independently
assigned case. No active capability or duplicate pending case is silently replaced.
Approval activates only that capability. Publish/resume requires VERIFIED organization
status and an ACTIVE capability backed by an APPROVED case for that same organization
and capability, in addition to the existing role, moderation, entitlement and quota checks.
An older VERIFIED label or paid entitlement alone therefore no longer permits publish;
existing installations must obtain/provision the separately reviewed capability proof.

`GET /organizations/{id}/public` (`API-008`) is anonymous for VERIFIED organizations.
It returns public name, region, description, website and valid capability badges.
It returns no tax ID, legal name, private evidence, membership or reviewer identifiers.

`PATCH /organizations/{org}` (`API-071`) accepts legal/public name, region,
description and website plus evidence. It requires OWNER and MFA. All changes are
held in an ORG_PROFILE_CHANGE case; stored/public fields change only after approval.
Tax ID and verification status are not editable through this endpoint.

## Existing-organization join and revocation

An OWNER with MFA can inspect a pending self-join request at
`GET /organizations/{org}/membership-requests/{id}` and obtain its linked document
through the matching `/files/{file_id}/download` helper. Access closes when that
request leaves PENDING_APPROVAL. It never grants access to unrelated files/CVs.
The existing `POST /organizations/{org}/members/{id}/approve` validates current
evidence and grants only the explicitly requested role. This path does not bypass
the existing self-approval rule. OWNER-created staff requests still need a different
OWNER's approval. Canonical memberships API-073 is restricted to OWNER.

`POST /organizations/{org}/memberships/{id}/revoke` (`API-075`) takes a reason.
It locks the organization, checks OWNER scope and protects the last active owner.
Two concurrent self-revocations leave an active owner. Membership and its grants
are revoked together; the next scoped request with the old bearer fails. Unrelated
account access/sessions remain governed by the existing IAM rules.

Contact-bound 24-hour staff invitations are documented in `INVITATIONS.md` (ORG-CODEX-002).
Adding/replacing owners and ownership recovery remain the next ORG package.
This onboarding package supplies no tax-registry integration,
human identity guarantee, real deployment verification or frontend.

## Existing installations

The normalized unique index intentionally fails if legacy organizations collide after
normalization. No rows are merged, rewritten or deleted. Review those records and
take a backup before a separately authorized correction. A role-catalog scope conflict
also fails explicitly rather than changing an existing role's scope.
