# AGY007 / Issue72: final read-only migration and test review

Workspace D:/Codex/FlexBridge-agents/antigravity. You are not alone. Source is
frozen and copied hash-identically to root feature/72-durable-feature-flags.
MAIN/MASTER FROZEN764fb984; target integration/r1-agent-collaboration only.
NO EDIT OWNERSHIP: read-only source review. No tools that mutate files, no shell
execution/compile/tests, no Git/GitHub/other agents, no .env/.data/secrets/provider.

Read these frozen files and needed related source as context:
backend/alembic/versions/0017_feature_flag_administration.py
backend/app/db/feature_flag_admin.py
backend/app/db/storage.py
backend/app/main.py
backend/tests/security/test_feature_flag_admin_api121.py
backend/tests/security/test_feature_flag_http_boundary.py
backend/tests/security/test_feature_flag_readiness_and_transactions.py
backend/tests/security/test_feature_flag_proof_controls.py
backend/tests/test_s2_1_3_retention_flags.py
backend/tests/security/test_academic_migration.py
backend/tests/security/test_academic_review_migration.py
backend/tests/security/test_enrollment_migration.py
backend/tests/security/test_regressions.py
backend/app/services/feature_flag_admin.py
backend/app/services/feature_flags.py
backend/app/services/operations.py
backend/app/api/v1/feature_flags.py
backend/app/core/iam_http.py

CAP037/API121/DB092: actual current independent ADMIN expiring grant + MFA session,
strict global schema, quotedversion and actor/key idempotency, exact minimal
receipt replay with current authority. actor/key->code->flag->user/session/grant
locks, expiry after waits and at commit. Immutable origins preserve all legacy
rows with no invented session/intent; PUBLIC events certify current state.
Canonical/state/proof/audit/receipt/digest equality and rollback must hold.
Protected4+R2 disable-only, paid alias readonly/off, no org override. This unit
manages state, not downstream domain/provider gates. FullR1/API108/pilot open.

Observed, not your execution: fresh0017/127tables (canonical94),32charrevisionfits32.
Earlier SQLNULL bug corrected; real new MFA login and logout audit preserved.
Copilot five-file service/router/operations review exit0/noP1P2 with unchanged pins;
its later migration reviews failed before starting due model-list/account retrieval.
Genuine readiness and audit xmin/savepoint P2s reproduced and corrected. DB-owned
BEFORE audit INSERT stamp uses top-level pg_current_xact_id text (primaryPG17 docs
confirm stable topID under savepoints).11nativecases passed32.43s including valid
savepoint/rollback/previousaudit rejection/forgedstamp overwrite/missingtableprobe.
Implicit ambient failed reads separately red->green; HTTPboundary5passed21.20s.
AGY006 new proof-control sixcases passed23.09s, exactreceipt/digestguard rejection,
realclock expiry aftervalidinsert beforecommitrollback, outerRR503.
Initial broad49:47passed2fixtureexpectationfail215.10s; canonical existing selfgrant
constraint rejects before service, legacy invalidschema before missingproof.
Codex strengthened both exact tests;2passed14.00s. ActualHTTPwaiter/blocker evidence
now persists in JUnit properties. Final broad49 currently running; don't claim green.

Find concrete actionableP1/P2 with path/actual line and reproduction; distinguish
test assumption bugs from production bypasses. Check provenance/chain/commit
constraints, same topTxn audit stamp, populated migration rollback, current
authority after actual waits, receipt replay and whether tests could pass for the
wrong reason. Expiry at commit MUST reject, chain forks/reordering and late
LEGACY_IMPORT insertions MUST fail; these intentional boundaries are not defects.
Do not suggest weakening them. If no findings say so with scope limits. No
invented execution/model/pilot certification. <=800 words. Wait for next task.
