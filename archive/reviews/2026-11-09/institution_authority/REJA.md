# EDU-CODEX-001A — current institutional authority gate

Prerequisite to reviewed institution onboarding. No new institution role-intake or
grant endpoint is exposed in this package. Finish current human-money PR52 first.

Source1368ee5 independent proof:8 failed/1 valid control passed,17.77s. Actual authenticated
GET /auth/me still reports COORDINATOR and existing require_institution authorizes it
after appointment expiry/future start/revocation/nonacceptance, membership nonacceptance,
or appointment user/institution mismatch. A wrong PLATFORM FINANCE catalog row in the
institutional grant table leaks a FINANCE label, although platform finance authority
is not obtained. This does not prove a real data write or anonymous/public grant exploit;
setup/admin mutations are trusted SQL fixtures. The first9 failed18.35s were a fixture
name-argument collision, corrected without changing runtime and retained separately.

Bounded implementation:

1. One shared effective-institution-role query for auth.roles_for, require_institution
   and transaction guards: active user/verified institution, accepted active/nonrevoked
   membership, nonrevoked grant with INSTITUTION COORDINATOR/TEACHER catalog scope,
   linked ACTIVE personally accepted appointment for the same user/institution, with
   valid_from <= Tashkent business date <= optional valid_to. Reject invalid legacy
   links at read/authorization time without deleting or rewriting history. Keep ordinary
   candidate/work rights. Do not make a nullable legacy case link into fabricated review.
2. Actual current session at touched academic write boundaries, after consistent business
   locks. COORDINATOR mutations keep existing MFA policy; ordinary TEACHER session
   behavior is preserved. Reuse/extract the existing user-before-session authority
   primitive without weakening finance/ownership MFA guards. Current target TEACHER
   role is required when creating an academic assignment; foreign-user locks must not
   recreate the contact-rebind deadlocks from #47 (NOWAIT/retry where needed).
3. Existing academic assignment create/revoke and academic review service/API wrappers
   use actual ActorContext. Require accepted current institutional scope and existing
   assignment/supervision/placement bindings. Forbid teacher self-assignment/self-review
   per source separation rule. Keep shared workplace-review behavior separate; do not
   claim the complete academic agreement/enrollment/export/grade workflow implemented.

No new public privileged role flag, optional sessionless compatibility bypass or
runtime test exception. No migration is needed merely to filter effective authority;
structural grant-write constraints and immutable onboarding proofs belong to the later
onboarding migration. Canonical94/runtime107 remain unless concrete source requires
otherwise. Retain imported trusted metadata/history; it is not legal identity/document
certification. Source requirements: v1.3 task59/67/69/CAP019/PG039 and v1.4 model/schema,
with amendments controlling scope. Agreements govern their academic purposes separately
from appointment lifetime; do not block staff's own renewal/status solely on agreement
expiry. Do not conflate proposed3-business-day response SLA with consent expiry.

Acceptance: corrected old invalid-role probes; genuine valid/date-boundary and ordinary
teacher password-session controls; all links/scope/status/accepted flags; actual HTTP
academic effects denied on stale roles/current actor changes; actual row waits and
opposite commit serialization; independent teacher target and no self-review; rollback,
history and valid replacement grants; affected IAM/billing/ownership/academic modules,
complete PostgreSQL CI and pinned source review. Date authority is evaluated at its
post-lock boundary, not frozen through commit. Pilotfalse. After this gate, implement
API017/096/097 and named reviewed appointment onboarding as EDU-CODEX-001B.
