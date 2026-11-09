Owner file operations previously trusted middleware authentication and passed only
user IDs to services. After an actual file-row wait, a completed logout could still
be followed by202/SCANNING and an enqueued scan. This draft passes the actual
ActorContext through upload initiation, completion and owner download and rechecks
current account/session/auth version/expiry and the existing sensitive-role MFA
policy inside the transaction, before provider work and through commit.

Completion/download acquire the owned file row first; initiation authorizes before
presigning/inserting. The existing onboarding account_authority policy is extracted
unchanged into authority.py. Ordinary PASSWORD/current sensitive MFA, owner-only
scope, exact storage versions, source/lease fencing and recorded-intent asynchronous
scanning remain. There is no user-ID-only compatibility bypass. Candidate/CV and
other self-service authority are an explicit separate audit scope.

Pinned old-source15 denial probes failed19.27s (actual sessions and SQL waits for
completion/download; service-entry barrier for initiation). The first15 run includes
3 invalid self-grant fixture failures, retained separately with the DB check intact.
Initial new27 native passed36.60s, including reverse actual logout waits, current
PASSWORD/MFA controls, forged-session rejection and provider rollback. Affected
storage/EDU72 native passed102.01s, including actual MinIO logout-to-worker-CLEAN;
pinned source review and full latest-head CI remain required. Overlapping counts
are not added. Synthetic HEAD/presign is not actual S3 proof; AV doubles in actual
storage cases remain explicit. Evidence reviews/2026-11-10/files_authority.

PR58 merged04ffd42 after final408b3cd complete757 CI passed375.77s/507.07s. This
package adds no migration/canonical handler: runtime0012/111, canonical94 and49
explicit/83 placeholders. Antigravity handoff/current journals are updated. Official
freshclam update and a separate actual benign-PDF local antivirus adapter smoke
passed; no service/detection/full-pipeline certification is claimed. Docker/WSL
admin installation remains incomplete. No pilot or live-provider acceptance claim.

Closes #59
