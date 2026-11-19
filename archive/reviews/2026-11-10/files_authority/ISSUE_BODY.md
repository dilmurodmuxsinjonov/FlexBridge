Current owner file services receive user IDs instead of the actual ActorContext.
On pinned afd343ab749a1a2131172e662769ff8fb2369d2c, an independently executed HTTP /
native PostgreSQL regression failed: upload completion waited on the actual file
row (pg_blocking_pids observed), actual DELETE session returned200, then releasing
the file row still let the stale request return202, set SCANNING and enqueue1 scan.

This is an already-authenticated in-flight revocation issue, not anonymous access,
foreign ownership, a public metadata-forgery or real scanning/provider exploit.
Storage HEAD/presign are explicit test doubles; tokens, logout and SQL wait are actual.
The file's owner and version references remain valid. The source-pinned regression
is preserved separately from Issue57's version-binding/native acceptance evidence.

After PR58, audit the three owner file methods/callers: upload intent, completion
and owner download. Require the actual current session/account and existing global
sensitive-role MFA policy at the transaction authorization boundary after business
locks, held through commit/signing as appropriate. Preserve owner-only scope,
ordinary PASSWORD policy, current version binding, lease/source fencing, provider
failure rollback and short URLs. No user-id-only/sessionless compatibility bypass.
Consider adjacent CV/candidate self-service actor-id-only paths separately so scope
is explicit; do not silently claim they are fixed with this bounded file package.

Test real logout/security/expiry interleavings, reverse serialization, role arrival
and current assurance, valid controls, replay/state errors and rollback. Preserve
native wait evidence, actual scoped storage integration and source/CI review.
No pilot claim. PR58's storage work does not certify file-session authority.
