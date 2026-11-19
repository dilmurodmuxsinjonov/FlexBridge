# AUTH-CODEX-002 — current authority through organization mutations

Confirmed local probe on ef4a94b: API075 membership revoke pauses after transient MFA
preflight; the same user's actual DELETE /me/sessions/{id} completes200; the paused
membership revoke then completes200 and changes the staff member to REVOKED. The
new negative regression fails (initial_junit.xml). This is a previously authenticated
in-flight request surviving session revocation, not anonymous access. No real user data.

Fix the remaining organization mutation paths so session/account/scoped authority is
checked after business locks and held through commit, consistent with the existing
authority.py helpers used by appeals and ownership flows. A revocation completed before
that authority boundary must block the mutation. If the mutation holds authority first,
revocation may wait until its commit; the ordering must be explicit and atomic.

Read-only review organizations.py, invitations.py, governance.py and their API wrappers
to identify related unprotected mutation paths. Preserve organization-first business
lock order and user-before-session authority order, scope/independence/last-owner checks,
existing history and rollback semantics. No arbitrary ActorContext role/session forgery
or bypass to make tests green. Keep this separate from bounded continuity PR46.

Acceptance: changed-state HTTP repro becomes blocked; actual session revocation and
account-security change while waiting for business locks; current scoped role grant
revocation and commit serialization; no partial memberships/grants/cases/audit; existing
org/invitation/ownership/appeal/IAM regressions and complete PostgreSQL CI; pinned read-only
review. Record exact affected methods and residual scope rather than claiming every API
fully hardened. Pilot remains false. Continue EDU after this confirmed security fix.
