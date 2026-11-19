The default branch still runs the prototype that accepted probe-specific inputs. This baseline replaces those runtime exceptions with PostgreSQL-backed sessions, scoped grants, financial transactions, private file scanning, and the tested IAM/candidate/organization packages.

It adds online Alembic migrations through 0005, pinned dependencies, PostgreSQL CI, a publication hygiene gate and a Git-blob manifest. The twelve prototype test files are preserved byte-for-byte with their SHA-256 manifest and replaced by SQL-backed regressions; this does not claim the old 39 tests are unchanged.

An actual read-only Copilot CLI review found a generic OWNER-grant bypass. Both creation and approval now allow only explicit staff roles, including rejection of legacy pending OWNER requests; the API also requires MFA. Five additional HTTP/SQL regression cases cover this and verify that password-only financial sessions are blocked. The review and Codex assessment are committed under reviews/2026-11-08/github_sync/.

Validation: 198 local PostgreSQL baseline tests plus 6 targeted peer-review tests passed. Both GitHub checks on final commit 131c72b succeeded, exercising the complete 203-test snapshot. Native API and populated-upgrade evidence is preserved under reviews/. published_source_manifest.json identifies the normalized Git blobs.

Release limits: pilot_ready remains false, 87 canonical endpoints remain 501, frontend/live provider/DR acceptance is incomplete. The known operational retention/appeal persistence gap is tracked separately in #37; no live credential rotation or production deployment is claimed.

Closes #35.
