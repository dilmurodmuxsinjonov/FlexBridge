# Current academic lists and coordinator notices (LOG-071)

Current follow-up to publisheddf87515 on feature/65-internship-admission.
Codex owns source/tests/docs; read-only Copilot plans/source opinions are separate
from test execution. PR66 remains draft, accepted main0013/114. Current draft
migration remains0015/124, canonical94 unchanged. No live database migration.

- API098 GET `/institutions/{inst}/supervisions` lists current exact enrollment/
  purpose responsibilities owned under the original current public coordinator
  grant or explicit current binding. Teacher scope instead requires personally
  accepted original current assignment and exact current terms, including accepted
  pending placements. Optional enrollment_id/purpose filters narrow scope. The
  minimal row has supervision/enrollment/institution IDs, student name, purpose,
  coordinator responsibility timestamp and a scoped assignment metadata link.
- The linked GET `/student-supervisions/{id}/academic-assignments` exposes only
  own current-scope placement/plan and teacher nomination metadata. Coordinators
  can discover IDs for revoke/replacement; teachers see their own personally
  accepted current assignment. This is not diary content or an institution-wide
  placement history. Expired-scope cleanup remains possible by known ID via103;
  broader expired-scope cleanup discovery is still follow-on work.
- API099 GET `/institutions/{inst}/assignment-queue` requires current formal MFA
  coordinator authority and lists only unbound pending academic-required requests.
  It uses the latest personal student school choice across ALL institutions,
  current verified own enrollment and the current plan. Changing the plan before
  binding requires a new school request in the service and SQL binding guard.
  Paged `/academic-agreements` and `/academic-teachers` helpers in that institution
  supply minimal current options, with no appointment/evidence documents or legal
  basis. Nomination still enforces the per-placement no-self-assignment rule.
- API105 GET `/me/academic-review-queue` lists current SUBMITTED diary revision
  metadata under an ACTIVE exact academic binding. Coordinator purpose or the
  named original teacher's personal consent for that revision's terms is required.
  Self-view through another role, drafts, other students/institutions and stale
  parent scopes are excluded. No summary, task, evidence, application or payroll
  fields are projected. Detailed API106 and107/108 actions remain next work.

All lists use bounded keyset pages with current-scope cursor anchors and no-store
HTTP responses. A role label alone never opens student records. Ordinary teacher
PASSWORD remains valid unless current sensitive-role policy requires MFA. A real
late coordinator grant after initial account authorization reproduced an unwanted
200 (1failed10.89s); a second current policy check after scoped-role pinning closes
the interval. Corrected overlapping initial6passed38.56s. Global queue derives and
sorts own-role institution hints before institution locks and actual authorization;
its final query is restricted to those locked scopes, without late business locks.
Current actor/session/scoped authority is held through response. Parent eligibility
is evaluated by the final READ COMMITTED query; this does not claim that every
external administrative parent row is frozen forever.

SUPERVISION_COORDINATOR_NOTICE is a distinct local topic for actual public
supervision creation and new placement binding. Creation has no placement. Origin/
binding proof derives the exact enrolled student, historical coordinator/purpose
and minimal own enrollment link. Source creation/binding, proof, notice and audit
commit or roll back together; the fenced worker atomically inserts inbox and ack.
Historical delivery survives later author logout without resurrecting current
authority. No imported personal intent, email/SMS delivery or legal identity is
invented. Worker defaults/compose include this local topic; identity worker stays
separate. Current extended rollback/fence/source mismatch tests remain in progress.

Native first five HTTP/notice controls passed33.90s. Read-only9-file source review
exited0/no actionable reviewed P1/P2. Expanded authority/cursor/>100/notice and
populated legacy controls are separate; do not relabel these as a full current
suite. Ambiguous imported primary teacher probe failed during invalid fixture
setup because the existing canonical one_current_teacher unique index already
blocks a second accepted primary. It was corrected to verify that protection and
preserve the valid imported primary, without a redundant or weaker SQL guard.

Publisheddf87515 full CI42743318591/42743326614 passed1015 twice549.23s/740.08s.
That accepted check evidence predates this queue code. Full current
matching-head CI/review/source pin, more lifecycle/cleanup controls, detailed
academic view/review/decisions, completion/amendments/reports/frontend/providers/
legal/DR and the original full R1 goal remain open. Pilot is not ready.

## LOG-071 current publication evidence

Current queue source/config9-file review exited0/no actionable reviewed P1/P2;
launch scope stayed byte-identical. Native authority/cursor/>100/legacy selection
21passed139.56s. Separate coordinator notice5passed41.18s. Broad current integration
57 cases:56passed1failed363.15s; stale-fence fixture set lease_until=now() although
worker requires strict lease_until<now(). Explicitly expired test lease timestamps
replace that boundary assumption in all three notice families; production worker
semantics stay unchanged. Corrective all three notice groups15passed73.87s. These
are overlapping stages, not a fabricated complete native green. Preserve the raw
failed stage. Current matching-head full CI still required before merge.

Full parentdf87515 CI1015 twice549.23s/740.08s is captured separately and predates
this queue source. Current draft registration67 explicit65 placeholders of132 is
registration only. No new table/dependency/live migration;0015/124, canonical94,
accepted main0013/114.106 minimum academic detail,107/108 review/decision and all
remaining R1 work stay open. Source/index receipt: source_academic_views_manifest.json.
