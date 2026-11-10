# LOG-071 - scoped institutional lists and review queue

Codex owns the source/tests/docs in this unit on feature/65-internship-admission,
from publisheddf87515. Read-only Copilot plan review exited0; its numbered P1/P2
items describe risks for the still-unimplemented queues, not findings that these
absent handlers already leak data. No source changes were delegated to another AI.
Full df87515 CI42743318591/42743326614 remains in progress as observed07:38 local.

Primary authority: source1.4 model DB029/034/052 and canonical098/099/105;
source1.3 CAP020/021, PG040/041/042 and api_kontraktlari.csv. Purpose is an opaque
exact agreement-enabled value; no test-literal policy whitelist. Do not grant
institution-wide student access from a role label. Self diary access through a
different academic role is forbidden. Candidate job/application/payroll/private
verification evidence stay outside these list projections.

1. API098 lists current exact supervisions. A coordinator owns that responsibility
   under its original current public grant or a current explicit public binding;
   a teacher needs the personally accepted original current assignment. Scope is
   per enrollment/purpose; optional filters only narrow it. Return identifiers,
   minimal student identity, purpose and coordinator-responsibility timestamp.
2. API099 lists unbound pending academic-required placements with the latest
   personal student choice ACROSS institutions, current verified own enrollment
   and exact current request plan. A plan edited before school binding requires
   a fresh student choice; service and SQL binding must enforce that too. Current
   MFA coordinator is required. Minimal agreement/purpose and eligible-teacher
   paged helper sources make API101/102 usable without exposing documents or IDs
   from trusted test setup. Already-bound reassignment stays a separate own-scope
   view/assignment lifecycle, not an institution-wide queue bypass.
3. API105 lists SUBMITTED current diary revisions under active exact academic
   scope, current coordinator purpose or original personal teacher acceptance for
   the revision's terms. Exclude self-view and drafts. Return revision/log/placement
   identifiers, day, revision/submission time and minimal student/purpose metadata;
   no summary/task/evidence/payroll details. API106 detailed view and107/108 actions
   are the next unit; queue registration cannot accept those contracts.
4. Lists lock the institution before actual current account/session/scoped grants.
   Global queue first derives/sorts institution hints, locks them, then authorizes
   and constrains final current SQL eligibility to those IDs. No late business lock.
   Current scope predicates apply to page rows AND cursor anchors. Read material
   eligibility is evaluated in the final SQL statement; do not claim that ordinary
   READ COMMITTED list reads freeze all external administrative changes forever.
5. Before enabling private coordinator views, append distinct source-derived local
   notices for actual public supervision creation and new placement binding. Use
   the immutable origin/binding for recipient and exact historical coordinator/
   purpose; creation has no placement. Atomic outbox/audit, fenced inbox/ack,
   minimal projections and own no-store read retain existing inbox policy. No
   email/SMS/legal identity or consent is invented for imported history.

Acceptance: real HTTP positive and teacher PASSWORD controls; other students/
institutions/current teacher without personal consent; source purpose/enrollment/
original grant/regrant/current agreement loss; latest school change/stale plan;
self-view, drafts and foreign cursors; >100 keyset coverage; committed session/
authority changes after actual institution waits; no partial notice/audit effects,
source mismatch/fence/worker rollback. Preserve every genuine failure and correct
fixtures without weakening proof. Also audit ambiguous imported primary teacher
history before new views rely on it. Current source review, matching-head full CI,
journals/handoff and explicit unfinished full R1 scope precede any merge.
