# Issue55 — reviewed institution onboarding

Implementation starts from merged PR54, main85dbb0e. That gate's final evidence
head873efea passed complete675 CI twice,427.55s/550.06s; exact-head merge closed53.
Source code remains2c3f2e1. Final CI metadata/log extracts are retained here so the
old source-pinned report need not trigger another evidence-only CI loop.

Read MANBA_VA_DOIRA.md as the historical source map, the actual read-only Copilot
architecture review/prompt/exit, ONBOARDING_DECISIONS.md and
IMPLEMENTATION_SEQUENCE.md as Codex's implementation boundaries. The planner did
not run tests or certify source/identity/legality/pilot. Its snapshot said native93
was pending at review time; PR54 subsequently passed and merged as recorded above.

Current package: canonical017/096/097 plus required named inbox/consent/resubmission
and reviewer helpers; first COORDINATOR or an existing coordinator's TEACHER request;
revision-bound approval and personal acceptance before any grant; forward runtime
migration and history preservation. No additional coordinator delegation, recovery,
student admission/enrollment/supervision/export/grade, frontend or live provider.
Do not expose a new real grant before the complete success/denial/race/migration
tests, pinned source review and full CI validate it. This branch is not acceptance.
