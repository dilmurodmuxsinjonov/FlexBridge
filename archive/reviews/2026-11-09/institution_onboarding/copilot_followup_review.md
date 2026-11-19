The duplicate-claim and omitted-end-date findings are closed in the current source. A repeat claim
checks current moderator authority and reviewer independence, then returns the existing case state
without updating its timestamp or writing another audit event—even for the reviewer’s own terminal
case. RevisionInput preserves field omission via model_dump(exclude_unset=True); the service carries
forward omitted appointment and agreement end dates, while explicit null creates an unbounded
proposal that still requires new review and acceptance.

The recipient lookup is behind the intended boundary. Staff intake checks current coordinator
authority, eligible owned materials, and the requester’s verified contact before resolving the
target contact. An ungranted first claimant therefore gets the same scope denial for registered and
missing targets. The lock sequence also appears consistent with the documented order;
foreign-user/contact locks are nonblocking, so I found no new lock cycle in this path. This is a
source review, not a fresh database-lock verification.

I found no concrete remaining regression introduced by these fixes within the requested scope. The
conditional presigned-GET version-binding limitation remains open as Issue #57: metadata comparison
and content-addressed keys do not attest provider immutability or version-pinned reads. It remains
an integration gate, not a demonstrated public privilege escalation; no live-provider or pilot claim
is warranted.

