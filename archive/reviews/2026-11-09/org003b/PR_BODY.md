An OWNER can request departure from only their own OWNER role, naming another existing OWNER in the same verified organization. The successor must consent with MFA and a current verified contact, then an independently assigned MFA moderator reviews the exact evidence revision. Approval revokes the source OWNER grant and commits canonical previous/successor history, case and audit atomically. Membership and other staff roles remain.

Both original OWNER grants are pinned. Revoke/regrant requires a new request; old intent cannot revive. Cancellation, decline, rejection, needs-info/resubmission and current authority/contact/evidence checks prevent premature departure. A former owner can read their own receipt with MFA without regaining organization authority. The existing initial/additional-owner proof function keeps its meaning; a separate transfer proof validates this event shape.

Validation on284b29783d13d4a95bbb35223ded92de7cca82c4:

- New native PostgreSQL HTTP/security34 tests and history6 tests passed; migration smoke1 passed.
- Opposite concurrent departures and ordinary revoke races leave one active OWNER. Audit/event/deferred-proof failures roll back revocation.
- Actual revoke/invite/independently reviewed regrant lifecycle tests require a new transfer request for either participant's replacement grant.
- Populated0008-to-0009 upgrade passed:103-to-105 tables, existing proof function and ownership/grant history preserved.
- Final eight affected native PostgreSQL modules:160 passed, zero failures/errors/skips, one framework warning,566.41 seconds including disposable database cleanup.
- Both complete337-test GitHub CI runs passed (42525017488/42525078474). Read-only pinned Copilot code review completed exit0 with no confirmed defect; coverage limits are recorded in the assessment. Source manifest, inventory and final JUnit are retained in the review folder.

Direct database writers are trusted. TestClient and synthetic role/contact/CLEAN-file metadata do not establish legal identity, live delivery, browser or production readiness. Inaccessible-owner recovery stays in003C. Canonical inventory remains46 explicit handlers and86 placeholders out of132; helper routes do not change this count. Pilot remains false.

Closes #43
