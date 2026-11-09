Private download authorization currently compares stored metadata but signs GET by key.
A disposable localhost MinIO probe observed that a trusted provider-admin same-key
replacement changes the bytes returned by an already issued URL, while explicit
VersionId retrieval keeps the original. This is not a demonstrated public overwrite
or authentication exploit.

This draft currently records the reproduction, implementation plan and read-only
Copilot planning review. No0012 or application fix exists yet. The next change must
separate bucket/VersionId/ETag provenance, pin source scan/private GET, preserve
legacy proof and accepted roles without guessed backfill, and prove fail-closed
provider/readiness behavior with real S3 integration and existing authority tests.

Also records the user's Windows tooling request and exact Antigravity handoff.
Project .venv installed successfully (pip check0, native smoke3 passed8.51s). Docker
and WSL installers are publisher/hash verified, but installation is incomplete:
VMP/WSL features are disabled, Docker installer exit1, WSL MSIX needs administrator,
and native elevation launch was canceled. The reviewable setup script parses;
no system branch success, automatic reboot or Docker engine readiness is claimed.
ANTIGRAVITY_HANDOFF.md lists exact current state, commands and ordered next work.

PR56 was merged12cd307 after final4ffbe96 complete732 CI passed twice383.64s/463.87s;
its source-pinned report remains separate. Runtime is still0011/111 tables and
canonical49 explicit/83 placeholders. Pilot remains false. This draft is not ready
to merge until Issue57 implementation, actual provider/PG regression, pinned peer
review and complete latest-head CI are finished.

Closes #57
