# AGY011: read-only master capability smoke (actual commands, no takeover)

User Q016 successor authorization; Codex is current master. No source/Git/GitHub/
lease/process modifications, no takeover or other-agent task invocation. Main
frozen764fb984; all future PRs/verified merges integration-only. You are not alone.

AGY009 asserted --mode auto --sandbox blocks network/externalCLI/localPG; that
claim is UNVERIFIED. Controller invokes this task in exactly that mode to test
only harmless read capabilities. Run only these commands via terminal, capture
actual exit/status or precise sandbox denial; no bypass/install/login/token changes:
1. git -C D:/FlexBridge ls-remote origin refs/heads/main refs/heads/integration/r1-agent-collaboration
2. gh pr view 73 --repo dilmurodmuxsinjonov/FlexBridge --json number,state,baseRefName,headRefOid
3. copilot --version
4. opencode --version
5. D:/FlexBridge/.venv/Scripts/python.exe -c "import psycopg; c=psycopg.connect('host=127.0.0.1 port=55440 dbname=postgres user=flexbridge_test connect_timeout=5'); print(c.execute('SELECT 1').fetchone()[0]); c.close()"+
The local PostgreSQL role is the disposable-test admin with no password in this
task, not pg_live or a private credential. Read SELECT1 only; no data inspection.
Do not read .env/.data/credentials/CLI config/raw logs. If a command needs
interactive/bypass approval, report that limitation; do not silently auto-escalate.
No claim that a harmless read proves a future push/merge will be approved. No
actual Copilot/OpenCode model task here, only CLI availability/version checks.
Return <=400words actual command exit results, permissions limits and whether
the blanket network-block claim is supported. Currentmaster CODEX, remain standby.
