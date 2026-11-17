# AGY006 / Issue72: focused proof-control regression draft

You are not alone. D:/Codex/FlexBridge-agents/antigravity, branchagent/antigravity-r1,
integratione506 baseline. Main/master frozen764fb984. No Git/GitHub/agent/provider/
install/secret/.env/.data actions. ONLY OWN this ONE NEW file:
backend/tests/security/test_feature_flag_proof_controls.py.
All other source/tests are frozen; Codex is running the existing broad flag suite.

AGY005 is accepted within its scope: Codex independent compile and native11passed
32.43s, including real savepoint, rollback, earlier-audit rejection, forged stamp
overwrite and unrelated audit unchanged. DB-owned top-level xid8 stamp is verified.
Current service also has Codex verify_storage actual-query probe and implicit
ambient read isolation fix, both red->green. Independent frozen five-file Copilot
source review exit0 found no actionable P1/P2; excluded migration deliberately.

Draft meaningful native PostgreSQL tests using existing identities, actual
auth sessions and service, not manufactured MFA. Inspect actual interfaces.
Do not run native tests (shared runner); syntax compile your ONE file allowed.

1. Exact receipt and digest DB controls: create one valid real ADMIN event first.
   In a NEW transaction load/copy that event and prepare a NEW event UUID and
   genuinely inserted new same-transaction audit via AppendOnlyAuditStore with
   exact current metadata/source/code/version/event/flag actor. Keep canonical
   row/proof otherwise matching. Update receipt event_id/audit_event_id. Attempt
   INSERT with wrong receipt enabled, extra internal receipt key, missing
   decided_at (parameterize), and separately wrong after_digest. Require the
   SPECIFIC guard error (exact minimal receipt / canonical flag state), not just
   any IntegrityError (a version UNIQUE error would be a false positive).
   Its guard runs BEFORE the existing flag/version UNIQUE check, so this is a
   guard rejection test, NOT an assertion that a duplicate version could commit.
   Preserve SQL NULL (sqlalchemy.null()) for absent JSONB before_snapshot.
   Assert no extra flag event/audit persisted after attempted transactions roll back.
2. Real clock expiry AFTER a valid event is inserted but BEFORE outer commit:
   set trusted fixture's exact ADMIN grant expiry to near future inside outer
   transaction, call service to insert valid change, wait bounded via DB clock
   polling until actual expiry, then outer commit must fail with explicit
   current ADMIN authority at commit error; no flag/origin/event/flag audit survives.
   Do not monkeypatch clock or remove required guards; bounded8seconds enough.
3. Actual REPEATABLE READ outer transaction mutation must fail503
   FEATURE_FLAG_ISOLATION_UNSAFE with no effects; use storage.transaction ContextVar
   joining, SET TRANSACTION before any queries, not an unjoined engine connection.

Keep tests focused and failure messages safe (no SQL parameters/tokens). Trusted
role/grant fixture mutations must be labelled; no synthetic current sessions.
Return <=400 words actual owned-file changes/compile result/limitations.
Controller requested listed gemini-3.8-flash-high for this focused test draft;
fallback to GeminiArgonHigh or GPTOSS only on actual quota, never invent model.
Full R1/API108/downstream business gates/frontend/legal/providers/DR/pilot open.
