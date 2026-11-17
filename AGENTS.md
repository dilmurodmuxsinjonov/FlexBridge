# FlexBridge collaboration policy (latest user instruction, 2026-11-10)

## Working branches and frozen main

- Shared integration branch: `integration/r1-agent-collaboration`.
- `main`/`master` are frozen. Do not push, merge, rebase, retarget a PR to them,
  delete/recreate them, change their settings or use an admin override. The user
  must explicitly lift this restriction before any future main mutation.
- Main freeze began at `764fb98496fa40857acb07844fd09fcafa99b7d6`, after PR69
  was merged before the user's restriction. Reading main is permitted.
- Bounded feature/fix/agent branches start from the integration branch. All new
  PRs target `integration/r1-agent-collaboration`; verified units may merge only
  there. Confirm the current PR base before publishing, readying or merging.
- Keep existing work; no reset/discard/clean of another agent's or user's edits.

## Codex, Antigravity and Copilot

- Codex coordinates and remains responsible for verification and integration.
- Use actual `agy` CLI for continuing Antigravity collaboration and `copilot` for
  independent code/Git review. Read
  `C:/Users/dilmu/.codex/skills/tashqi_ai_agentlar/SKILL.md` for the protocol.
- Give each task an ID, explicit goal, source context, isolated workspace/branch,
  owned files, expected output and measurable acceptance. Agents are not alone;
  they must not revert other work or edit outside their ownership.
- Antigravity workspace: `D:/Codex/FlexBridge-agents/antigravity`, branch
  `agent/antigravity-r1`. Keep conflicting production edits in separate worktrees.
- Start with read-only source/design or clearly scoped implementation work.
  Verify each report, diff and relevant execution; then send the next concrete
  task. Agent opinion is not a test, legal/provider/pilot or model certification.
- Select models by task and actual `agy models` availability. Complex architecture
  starts with `gemini-4-argon-high`; use another suitable available model if actual
  quota/limit evidence requires it. Do not invent model names or assert execution
  from the availability list. Record requested vs reported model, exit status,
  conversation ID if exposed, findings, verification and next task.
- On a real model limit, switch to a suitable listed model and retain task context.
  Diagnose transport/permission errors separately. Do not retry unchanged forever
  or claim another model ran unless it actually returned a result.
- Do not read/send `.env`, runtime `.data`, account credentials, private identity
  evidence or provider secrets to agents. Raw CLI logs remain outside publication.

## Conditional master succession (Q016, latest user instruction)

- If Codex reaches its real limit, Antigravity is authorized to take over the
  complete ongoing development workflow, including Copilot/OpenCode coordination.
  Follow ANTIGRAVITY_MASTER_PROTOCOL.md and the D: CURRENT_HANDOFF.json.
- Codex remains master until an explicit takeover trigger. Silence/timeouts are
  not quota evidence. No detached authoritative Codex quota detector is available;
  the prepared terminal takeover records the actual supplied trigger.
- Before later mutations inspect D:/Codex/FlexBridge-agents/coordinator_state.json.
  If owner is ANTIGRAVITY, do not concurrently write or merge; arrange an orderly
  handback after the runner/in-flight tasks stop. Main freeze and integration-only
  policy, source/test/CI verification and user stop instructions always persist.

## Evidence, continuity and storage

- All new work, tools, reports and artifacts belong on D:. Repo: `D:/FlexBridge`.
- Read four root journals and relevant primary specifications; record ownership
  and acceptance before implementation. Preserve failed stages and old history.
- Update `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`,
  `03_BOSQICHLAR_VA_HOLAT.md`, decisions when changed, and
  `ANTIGRAVITY_HANDOFF.md`. Explicitly retain the frozen-main constraint.
- Full R1 remains active until the user stops work. Small green units do not
  imply full functionality or pilot acceptance. Source hashes, actual native
  results, exact-head CI and current review feedback precede integration merge.
- No live deployment, money movement, credential rotation, pg_live edits,
  Docker/admin/UAC/reboot action is implied by ordinary development delegation.
