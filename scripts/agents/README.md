# Conditional Antigravity coordinator

Windows/D: tools for user decision Q016. See ../../ANTIGRAVITY_MASTER_PROTOCOL.md.
Antigravity is a conditional successor; Codex remains master until an explicit
trigger. There is no authoritative detached Codex quota detector. Silence or a
print timeout never automatically starts a second coordinator.

Installed runtime copies are in D:/Codex/FlexBridge-agents. This directory keeps
their reviewed source. Update installed copies only while the coordinator is
CODEX and no master runner/turn is active; compare hashes. No startup task,
idle watchdog, login change, permission-skip flag or service is installed.

The launcher starts a hidden process only on explicit invocation. Its OS lock
prevents competing runners, coordinator ownership fences later Codex writes,
and STOP_MASTER prevents new chunks. A timed-out server turn can still be active;
inspect/drain it before generation-checked handback. Network preflight retries
are bounded; an unverifiable frozen main stops new work.

Run the harmless local checks:

```powershell
D:\FlexBridge\.venv\Scripts\python.exe D:\FlexBridge\scripts\agents\check_master_protocol.py
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Codex\FlexBridge-agents\Start-AntigravityMaster.ps1 -DryRun
```

The sample fixture contains only status/error fields from actual prior CLI
outcomes. Checks prove classifier/handback/OS-lock boundaries, not native business
correctness or automatic agent takeover. Actual AGY012 ordinary CLI reads passed
GitHub metadata, worker versions and disposable PostgreSQL SELECT1. Future writes,
model authentication and policy approval must still be checked when attempted.
