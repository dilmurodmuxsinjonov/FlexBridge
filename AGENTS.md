# FlexBridge collaboration policy (latest user instruction, 2026-11-19, Q-017)

## Working branches and main (updated 2026-11-19, Q-017)

- Active base and integration target branch: **`main`** (per explicit user
  instruction on 2026-11-19: `"hozirdan boshlab ishlarni meinga kochirib
  bundan keyin brechga otishni buyutgunimcha meinda ishla"`). Continue working
  on/into `main` until the user explicitly commands switching back to a separate
  branch.
- Historical branch `integration/r1-agent-collaboration` (`f3f5469591eb00f7b852ae3236b0a3b61dcf1ffd`,
  covering PR #282–#295 / `LOG-198`–`LOG-205`) is retained for audit history.
- Prior `main` freeze history preserved:
  - Freeze began at `764fb98496fa40857acb07844fd09fcafa99b7d6` (2026-11-10, after PR #69).
  - 2026-11-17: with explicit user approval, `main` was promoted to `19643248c3215c74dfbb6dc6ef448568fb71ba43`
    via PR #279 (`03c09cb`); backup `backup/main-2026-11-17-764fb98`, tag
    `main-backup-2026-11-17`, bundle `D:/Codex/FlexBridge-backups/main-764fb98-2026-11-17.bundle`.
  - 2026-11-17 (later): with explicit user approval (`"mainni yangila"`),
    `main` was promoted to `ab332775a1ec29b39f4d6fb4909d100b43d8e1b3` via PR #281
    (`2018d7b`); backup `backup/main-2026-11-17-03c09cb`, tag
    `main-backup-2026-11-17-03c09cb`, bundle
    `D:/Codex/FlexBridge-backups/main-03c09cb-2026-11-17.bundle`.
  - 2026-11-19 (`Q-017` / `LOG-206`): with explicit user instruction, the `main`
    freeze is lifted, verified `integration/r1-agent-collaboration`
    (`f3f5469591eb00f7b852ae3236b0a3b61dcf1ffd`) is promoted to `main` via
    `release/main-2026-11-19`, and previous `main` (`2018d7b92149417be45e4370ba0c445979e93a84`)
    is backed up as branch `backup/main-2026-11-19-2018d7b`, tag
    `main-backup-2026-11-19-2018d7b`, and bundle
    `D:/Codex/FlexBridge-backups/main-2018d7b-2026-11-19.bundle`.
- Short-lived feature/fix branches start from `main`, open verified PRs
  targeting `main`, pass exact-head CI, merge into `main`, and return the local
  checkout to `main` (`D:/Codex/FlexBridge-agents/hooks/pre-push` remains intact
  so unreviewed direct pushes to `main` stay guarded). Confirm the PR base (`main`)
  before publishing, readying or merging.
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
  handback after the runner/in-flight tasks stop. Active `main`-based PR/CI
  policy (`Q-017`, until the user orders a branch switch), source/test/CI
  verification and user stop instructions always persist.

## Evidence, continuity and storage

- All new work, tools, reports and artifacts belong on D:. Repo: `D:/FlexBridge`.
- Read four root journals and relevant primary specifications; record ownership
  and acceptance before implementation. Preserve failed stages and old history.
- Update `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`,
  `03_BOSQICHLAR_VA_HOLAT.md`, decisions when changed, and
  `ANTIGRAVITY_HANDOFF.md`. Explicitly retain the active `Q-017` `main` workflow policy.
- Full R1 remains active until the user stops work. Small green units do not
  imply full functionality or pilot acceptance. Source hashes, actual native
  results, exact-head CI and current review feedback precede integration merge.
- No live deployment, money movement, credential rotation, pg_live edits,
  Docker/admin/UAC/reboot action is implied by ordinary development delegation.
