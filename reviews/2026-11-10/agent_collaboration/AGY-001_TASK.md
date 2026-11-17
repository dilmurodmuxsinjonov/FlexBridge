# AGY-001 - durable feature administration design, read-only

User explicitly added Antigravity as a continuing collaborator. Codex owns integration
and verifies every result; you are not alone. All changes/PRs belong to
integration/r1-agent-collaboration or feature/agent branches based on it. MAIN IS
FROZEN at764fb98496fa40857acb07844fd09fcafa99b7d6: do not push, merge, rebase,
retarget PRs or alter settings on main/master. No GitHub mutations in this task.

Your isolated workspace is D:/Codex/FlexBridge-agents/antigravity, branch
agent/antigravity-r1, initial tree764fb984. READ ONLY: no code, config, git or
document edits and no shell execution. Return the requested report in your response.
Do not read .env, .data, credentials, agent auth/log/config files or private evidence.
Read only tracked repository primary specifications, relevant backend source/tests
and the task text. Never invent model identity, quota, test execution or readiness.

Task: design a bounded durable/authenticated API121 feature-flag administration
unit. Verify primary specs/v1_3/FlexBridge_toliq_topshiriq.md CAP037 and
specs/v1_4/FlexBridge_model_1_4.json DB092/API121, plus
backend/app/services/feature_flags.py, operations.py, authority.py, db/storage.py,
relevant migrations and security tests. Primary actual role is time-bound platform
ADMIN with current MFA (not SUPER_ADMIN). API121 is PATCH
/api/v1/operator/feature-flags/{code}; API122=incidents. An older NEXT.md reference
to CAP036/SUPER_ADMIN is wrong; use primary sources.

Source explicitly defaults OFF ratings, academic_official_export, WhatsApp and
paid_checkout. Flags cannot bypass capability/tenant/session/MFA/agreement/provider
checks. User keeps R2 freelance out of R1, including org overrides. Current RAM/UID
FeatureFlagService is not an authority boundary; operations readiness reads its R2
state. Old tests/test_s2_1_3_retention_flags.py is archived and not acceptance; do
not rewrite archive or revive its permissive R2 behavior. DB092 has code/enabled/
rule_schema/changed_by_id/reason; changed_by must be a genuine human actor, no fake
bootstrap identity. A missing privileged flag is OFF. Existing unproved legacy true
rows must not become certified new privilege; preserve provenance while requiring
real current ADMIN intent. Current accepted runtime0016/125; forward migration only
if needed, no edits to released0016. Do not implement or enable any live flag.

Return: (1) verified source facts with file/line; (2) a narrow technical contract
and explicit new design choices vs source facts; (3) proposed file ownership and
schema/provenance/nonce/version/receipt/atomic audit/lock ordering; (4) meaningful
actual-session/expiry/concurrency/populated upgrade tests; (5) unresolved requirement
gaps and a concrete next implementation task. Separate ADMIN state administration
from subsequent enforcement at paid/rating/export/WhatsApp business boundaries.
No official grade/signature/completion/legal/provider/full R1/pilot certification.
Codex will check your report against sources, then assign the next bounded task.
