# EDU — source map before implementation

Planning only. Finish confirmed authority fixes #47/#48 first. No EDU runtime change
or acceptance is claimed. All paths below are relative to D:/FlexBridge.

Primary local sources:

- specs/v1_3/FlexBridge_toliq_topshiriq.md:59,67,69 describe claimed onboarding intent,
  independent platform review of formal institutional appointment, domain insufficiency,
  personal acceptance and proposed3-business-day response; NEEDS_INFO adds a revision
  to the same request and retains rejection history.
- Same document CAP-019 (~523), PG-039 (~1127), PG-040 and CAP-020/021 define institution
  authority, legal basis/agreement, exact enrollment and accepted teacher assignment.
- specs/v1_4/FlexBridge_model_1_4.json is current canonical table/API metadata. v1.4 PDF
  amendments take precedence over1.3, especially institutional exports restricted to
  current institution COORDINATOR with step-up and audit (PDF6), INV-03 composite scope
  (PDF4), private evidence quarantine (PDF7) and AC-041 separation (PDF9).
- 05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md:52-53: verified contact does not establish
  organizational authority; appointed staff/mentor/teacher accept personally.

Canonical entry points: API-017 options, API-096 appointment request, API-097 status.
DB-028 institutions,029 agreements,030 memberships,031 role grants,032 appointments,
033 invitations,019 verification cases/evidence. Student data is separate: DB-015
enrollments,034 student_supervisions; API-027/034,098-108 follow after authority intake.

Bootstrap boundary to make explicit in the implementation plan: canonical017/096/097
list COORDINATOR operation roles, while public onboarding allows a person to CLAIM
an intended role without granting it. Do not authorize a privileged role by client
choice or silently relax existing-role mutation scopes. An explicit authenticated
current-MFA self-intake helper can model unverified first-coordinator intent, with
independent assigned moderator review and named personal consent before any actual
role. Read the complete relevant sources and obtain source-plan review before choosing
the exact helper/canonical dispatch. A verified institution must not automatically
reopen bootstrap merely because its coordinator is revoked, suspended or expired.

Bounded work sequence to refine:

1. Institution identity/appointment intake, evidence and agreement/legal-basis scope;
   immutable request revisions/consent and independently reviewed first coordinator.
2. Existing-coordinator staff appointments, named contact-bound acceptance, formal
   review, expiry/revocation and preserved grant/membership history. No automatic
   staff grant on contact ownership or email domain.
3. Own enrollment intake/status with verified vs self-declared distinction, scoped
   review and end/expiry history; ordinary work rights survive enrollment loss.
4. Supervision and accepted academic assignment, purpose-bound data/review/export and
   agreement-gated official grade/signature flags. A platform PDF is not a signature.

Use transaction-bound current user/MFA/institution authority after business locks,
including current appointment dates/status/personal acceptance and exact institution
FK scope. Reuse the contact nonblocking ordering learned in #47. Keep generic review
and resubmission dispatch explicit so unrelated cases cannot acquire academic roles.
No direct-DB writer, synthetic CLEAN metadata, or manual evidence assessment is proof
of legal identity, document truth, a real institution integration or overall pilot.

Required evidence: changed-state positive/negative HTTP, grant/appointment refresh,
expiry, named acceptance/wrong contact/account, scoped history, actual SQL constraints,
concurrent retries/review/revocation and rollback, populated upgrade preservation,
native affected modules, full PostgreSQL CI and pinned source review. Inventory counts
are handler registration, not acceptance coverage. Frontend/live providers/DR remain
separate work; do not label unfinished academic services as complete.
