# AGY-002 - focused security revision, READ ONLY (maximum 1400 words)

Continue the same conversation, retaining AGY-001 context. You are not alone.
Codex verified your report against primary sources and current runtime. MAIN/MASTER
FROZEN at764fb984; only integration/r1-agent-collaboration is an allowed PR target.
Workspace D:/Codex/FlexBridge-agents/antigravity on agent/antigravity-r1.
No shell, code/file/config/Git/GitHub edits, .env/.data/private credential reads.
Do NOT start the broad implementation task proposed at the end of AGY-001.

Requested model Claude Opus5.5 High for independent security review; actual CLI
listed its ID. If actual quota/limit is returned the controller will choose another
suitable available model, retaining task context. Do not invent reported model.

Revise only these explicit design points, no renewed broad repository research:
1. Missing-row creation requires code advisory lock before SELECT FOR UPDATE;
   cross-code same actor/key also needs durable global intent serialization before
   current actor/grant checks. State one total lock order and real measured tests.
2. Existing platform_authority returns None; capture the exact locked current ADMIN
   grant/session/auth_version without UID fallback. Role-grant expiry after waits
   must be checked at decision; API standard stale version412, key conflict409.
3. Origins/initial LEGACY_IMPORT snapshots are immutable. Do not upsert an old
   origin into PUBLIC or erase history. Propose append-only PUBLIC change events
   and derived/versioned current proof with canonical-state equality at commit.
   No invented bootstrap human actor. Legacy true isn't certified enablement.
4. Replay identical stored receipt (no toggling idempotent_replay). Current actor
   must authorize replay; a previously valid config change survives author logout.
5. Choose protected enable lockout until actual prerequisites exist. Prevent the
   legacy R1_PAID_ORG_PLANS alias bypassing paid_checkout OFF. Server-owned strict
   global rule_schema only; R2/org override cannot enable anything in R1. State
   never substitutes domain authority/agreement/provider gates.
6. Current security tests belong in backend/tests/security, not archived test paths.

Return a concise revised contract with source facts vs new technical choices,
minimal helper-table shape and invariants, exact lock/replay order, 8 decisive
actual-session/SQL/upgrade/concurrency tests, and an owned-file implementation
split: AGY owns new migration/db module/service/tests; Codex owns shared storage/
router/operations wiring and integration. Flag any unresolved contradiction.
No implementation or test execution claims. Codex will check this revision and
give the next exact task. Full R1/API108/provider/legal/pilot remains unaccepted.
