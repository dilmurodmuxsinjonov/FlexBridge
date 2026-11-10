# Q016: conditional Antigravity master handoff

User instruction2026-11-10: if Codex reaches its limit, Antigravity takes over
the whole authorized FlexBridge development workflow, including actual Copilot
and OpenCode coordination. This adds conditional authority; main/master remain
frozen764fb98496fa40857acb07844fd09fcafa99b7d6. All new PRs/verified merges target
integration/r1-agent-collaboration. FullR1 remains active until the user stops it.

## Trigger and exclusive ownership

Codex is the current master. Do not infer a quota from silence, a CLI print timeout,
a closed app or stale heartbeat. This environment exposes no authoritative Codex
quota event to a detached local script. Automatic quota detection is NOT installed.
When a genuine limit is observed and a tool call is still possible, Codex launches
the prepared takeover. If the host has already stopped Codex tools, the user can
run the same terminal command without another planning/approval conversation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Codex\FlexBridge-agents\Start-AntigravityMaster.ps1 -Reason CodexLimit
```

The launcher records the explicit trigger and switches the local coordinator
record to Antigravity. It does not claim the script independently observed quota.
An OS-held exclusive lock prevents two master runners. Codex must check
D:/Codex/FlexBridge-agents/coordinator_state.json before later source/Git/GitHub
mutations; while owner=ANTIGRAVITY it performs read-only inspection until an
explicit, orderly handback. The user can stop the runner by creating
D:/Codex/FlexBridge-agents/STOP_MASTER; no new chunk starts after that marker.
An in-flight CLI turn must also be inspected/stopped before resuming Codex writes.
The owner record is an agent coordination rule, not a kernel restriction on
arbitrary manual Git/API commands or cancellation of already running tool calls.
After the runner and every in-flight AGY/worker turn are confirmed stopped, an
explicit generation-checked handback is available (replace N with the observed
coordinator generation):

```powershell
D:\FlexBridge\.venv\Scripts\python.exe D:\Codex\FlexBridge-agents\antigravity_master_runner.py --handback --expected-generation N --confirmed-no-active-turn
```

This operator confirmation is required; the command does not independently prove
a server conversation ended. An active runner's OS lock blocks handback. Unknown
or stale generations are rejected, and a timed-out turn never triggers a fresh
model merely because stderr echoed quota words. STOP_MASTER is never cleared by
handoff/handback; user stop remains authoritative.

## Antigravity master's responsibilities

1. Read AGENTS.md, four journals, ANTIGRAVITY_HANDOFF.md, this protocol and the
   machine-readable CURRENT_HANDOFF.json. Refresh actual git/PR/CI/process facts;
   a handoff snapshot is historical, not proof of current remote state.
2. Preserve every user's/agent's working-tree edit. No reset/clean/discard,
   main mutation, live deployment/money/credential/pg_live/admin/reboot action.
3. Coordinate bounded tasks with actual agy/copilot/opencode CLIs. Give each an
   ID, owned files, isolated worktree, acceptance and exact next task. Workers
   are not alone; no conflicting writes or reverting others. Master can delegate
   and implement, but independently checks worker diff/source/real tests.
4. Discover actual CLI models and choose by task: available GeminiArgonHigh for
   architecture/security, available FlashHigh for focused work; suitable listed
   alternatives on actual model quota. Record requested vs reported identity;
   do not certify identity from a self-description. Diagnose account/transport
   errors separately. Do not duplicate a continuing turn after a print timeout.
5. Copilot is an independent code/Git reviewer; OpenCode supplies additional
   implementation/review. Source opinions are not native/browser/provider tests.
   Preserve failures, reject unsupported findings with evidence and retain limits.
6. Native PostgreSQL uses disposable databases, never pg_live. Keep raw logs,
   credentials, .env/.data/private evidence outside publication and agent prompts.
7. Verify complete matching-head push/PR CI summaries, source/index/commit pins,
   current comments/reviews and explicit integration base before any merge.
   Full green jobs do not alone imply fullR1/pilot readiness. Never use admin
   overrides or retarget to main. Close nondefault-branch issues only after proof.
8. Update journals and exact next tasks after each bounded unit. At every chunk
   end write MASTER_NEXT.md with completed work, evidence, unresolved risks,
   active process/conversation IDs, ownership and the next concrete task.

## Current handoff facts (refresh before acting)

Root D:/FlexBridge: feature/74-antigravity-master from accepted integration
d72462e705df5d45a91963679301bb377b3755c5. PR73/source83548d3 was merged ONLY
into integration after complete1142 CI twice665.73s/905.46s and current feedback
checks; Issue72 is closed. Native49passed214.83s plus6passed23.09s; finalAGY007
static18file review no actionableP1P2,19source/doc/test hashes verified against
published head. Actual runtime draft0017/127,canonical94;71explicit61placeholder
registrations of132, not functionality. Main frozen764fb984, acceptedintegrationd72462e7.

Isolated D:/Codex/FlexBridge-agents/antigravity: agent/antigravity-r1 at d72462e7.
Its19 verified source/doc/test WIP paths were preserved in retained stash
fdfa466984e6439aebe37c8f007f24d7d8049722, then fast-forwarded to the identical
accepted source; normalized hashes checked. Q016 policy/handoff WIP is separate
from published PR73 source. AGY008 API108 design returned but Codex rejected
specific invented columns/counts/lock and replay contradictions; its critique
is AGY-008_CODEX_REVIEW.md. Revised design is required before implementation.
No restart of an ongoing turn on timeout. API108/Issue67,
downstream flag gates, candidate diary/attachments, completion/amendments,
frontend/providers/legal/DR/UAT/fullR1/pilot remain open.

The prepared master runner is dormant until the explicit trigger. A standby
acknowledgement is not a takeover or completed work. Never claim background
autonomy continued unless an actual runner receipt/process proves it.

Actual AGY012 read-only smoke in ordinary CLI auto mode (no optional sandbox)
succeeded for GitHub refs/PR metadata, Copilot/OpenCode versions and disposable
PostgreSQL SELECT1. The optional sandbox was removed from the master runner
after actual AGY011 denials; no dangerous skip-permissions flag was added. These
reads do not certify future pushes/merges or worker model authentication.
