EDU-CODEX-001B implementation plan

Scope and decisions. Build only first-institution/first-coordinator claims and staff appointments
requested by an already-authorized coordinator. Follow the onboarding rules in v1.3 “Hisob ochish va
ulanish,” CAP-019/020/021 and PG-039, the v1.4 API-017/096/097 and DB-019/020/028–034, and the
boundaries in 05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md. The institution-authority follow-up review
is complete; native93/CI remain pending. This plan does not imply the fix is merged or pilot-ready.

 - API-017 options: require a valid signed-in session, but no existing institutional role or MFA.
Return generic requirements and agreement information only—no institution directory or private case
data.
 - API-096 intake: require current-session MFA for either bootstrap submission or an existing
coordinator’s staff request. Derive intent from the normalized registry record and the caller’s
current server-verified authority; do not accept a client role or intent as proof of authority.
 - API-097 status: return only the requester’s case, the named appointee’s appointment, or an
appointment visible to an authorized coordinator in that institution. Never expose reviewer evidence
through this endpoint.
 - Staff scope: initially allow the existing coordinator to request a TEACHER appointment. Keep
additional COORDINATOR appointments outside this package because the source does not establish
delegation rules for them.
 - NEEDS_INFO clock: retain the case’s original three-business-day first-response target; do not
reset it or treat it as re-review SLA, consent expiry, or automatic acceptance. Record each response
revision and its timestamp. Count weekdays in Tashkent; the source does not specify
holiday-calendar treatment.
 - Agreement versus appointment: appointment dates govern role authority; agreement dates and
purposes independently gate academic uses. Do not activate academic uses or infer academic
permission from an appointment.

Boundaries and flow

Implement a dedicated InstitutionOnboardingService; keep intake and reviewer authorization explicit
rather than refactoring verification into a generic workflow.

 1. API-017 serves generic authenticated options.
 2. API-096 normalizes the registry code and serializes lookup/deduplication. If the code is new,
create a pending institution, a first-coordinator appointment, and an institution verification case
without requiring a COORDINATOR grant. If it already exists, accept only a current coordinator’s
staff appointment request for that institution. If it exists but has no active authority, refuse
bootstrap and direct the caller to a separately reviewed recovery path; never create a second
institution or reopen bootstrap.
 3. Require current verified contact and private, eligible evidence owned by the submitter: clean,
non-deleted files of allowed types, plus the appointment document and any submitted
agreement/legal-basis evidence. Store contact digests, not raw contact values. Evidence and
agreement materials are review records, not platform certification of identity, signature, or legal
validity.
 4. Use DB-019/020 for case and revision evidence. A narrow, append-only appointment-revision record
should bind each case revision to its institution, named user, fixed/requested role, dates,
agreement/purpose/legal-basis snapshot, and evidence references. Preserve reviewer outcomes in
append-only audit/review history. Add an immutable acceptance record binding the named user,
verified contact and exact revision.
 5. The first coordinator and each invited staff member personally accept the exact reviewed
revision. A NEEDS_INFO resubmission increments the same case revision and retains prior evidence,
decisions and acceptances; prior acceptance cannot satisfy the new revision. A three-business-day
target never substitutes for review or consent.
 6. Grant authority only after independent approval and named-user acceptance of the approved
revision. The first coordinator cannot self-approve. Existing-coordinator staff requests require
independent review too. A reviewer must not be the requester, the appointee, or an active authority
in the institution.
 7. Add small helper APIs for the missing acceptance/inbox path: a signed-in user’s pending
institution appointments, and an appointment-accept endpoint that verifies the user and current
verified contact. Require MFA for coordinator appointment acceptance; retain baseline assurance for
teacher-only acceptance. Do not return an invitation token to the coordinator. No live delivery
provider is needed for this package.

Integrate reviewer actions with the existing assigned-reviewer dispatch: explicitly route
institution case kinds to the new service and reject unsupported or other case types. Extend
queue/detail/download handling only as needed for these cases; evidence downloads remain
moderator-only and audited. Do not send EDU cases through organization-specific approval logic.

Authorization, locking and migration

Use the current institution-authority predicate and actual-session guard within the same transaction
as sensitive reads/writes. Recheck active user, current session/MFA where required, verified
institution, accepted membership, matching user/institution appointment, appointment status and
validity dates, and non-revoked grant. Do not trust role labels cached in ActorContext or separate
an authorization check from the write it protects. Revocation or suspension must take effect on
subsequent requests; a previously verified institution with lost authority must not regain
bootstrap.

For concurrency, follow existing organization and contact patterns: advisory transaction lock on the
normalized registry key, then lock/re-read the institution and case; use a fixed institution →
case/appointment/invitation → membership/grant order. For contact binding, pin a known target user
with NOWAIT before a try-advisory contact lock, re-read the contact, and abort/retry on change or
contention. Apply the current user-before-session locking rule in the transaction-bound session
guard. Never wait on contact rebinding while holding another user’s authority lock.

Add one forward Alembic migration (next revision after 0010_owner_continuity.py) and update both
checked-in v1.4 SQL copies and FlexBridge_model_1_4.json/API contracts. Keep the migration narrow:
add the immutable EDU revision/acceptance records, any needed uniqueness/indexes, and constraints
linking grants, memberships, appointments and role scope. Backfill only relationships that can be
proven; preserve malformed legacy rows but revoke their effective grants rather than deleting
history. Preflight normalized registry-code collisions and stop for explicit reconciliation—never
auto-merge institutions. Add constraints in a staged/NOT VALID manner where necessary, reconcile
legacy rows, then validate. Do not introduce runtime fixture bypasses.

File ownership and sequence

 1. Schema/API contract: specs/v1_4/FlexBridge_model_1_4.json, both FlexBridge_1_4_schema.sql
copies, and the next backend/alembic/versions/ migration. Define case kinds, revision/acceptance
records, constraints, API-017/096/097 behavior, and helper contracts together.
 2. Service and API: new backend/app/services/institution_onboarding.py and
backend/app/api/v1/institution_onboarding.py; register the router in backend/app/main.py. Add
explicit EDU dispatch to the existing reviewer API path in backend/app/api/v1/organizations.py (or a
small dedicated dispatcher), keeping organization-only handlers scoped to organization case kinds.
Add explicit API-017/096/097 handlers to canonical_routes.py or the new router so they cannot fall
through to authenticated 501 placeholders.
 3. Authorization integration: reuse backend/app/db/institution_scope.py and
backend/app/services/authority.py; touch auth.py, dependencies.py or the predicate only if the
existing authorization follow-up requires wiring—not as a broad refactor. Keep
agreement-purpose/date checks separate and do not implement academic-use endpoints here.
 4. Tests: add backend/tests/security/test_institution_onboarding.py; extend
test_institution_authority.py or contract tests only for changed behavior. Use the existing
Alembic/PostgreSQL test setup.

Native PostgreSQL coverage and failure modes

Cover concurrent normalized-registry claims; existing institution with active coordinator versus
known institution with no active authority; no bootstrap on authority loss; MFA required for
privileged submitters but not teacher-only reads/acceptance; domain-only, wrong-user/contact,
changed-contact and ineligible-file rejection; assigned independent reviewer and explicit rejection
of other case types; no self-approval; no grant before both approval and exact-revision acceptance;
NEEDS_INFO history/reacceptance; idempotent acceptance; Tashkent appointment boundary dates;
agreement-purpose/date checks independent from appointment dates; immediate revoke on subsequent
requests; and legacy migration behavior for duplicate normalized registry codes and mismatched
grants.

Critical failure modes to guard against are a canonical 501 fallback, client-selected authority,
check-then-write races, stale contact binding, reviewer-dispatch leakage, evidence/status IDOR,
broad reviewer visibility in API-097, stale acceptance after revision changes, and treating named
acceptance as identity certification. The source does not establish what constitutes legally
sufficient identity or platform authority to certify an institution’s legal status; keep that
boundary explicit rather than inventing it. Student enrollment, academic assignment, supervision,
exports, grades, frontend work and live providers remain out of scope.

