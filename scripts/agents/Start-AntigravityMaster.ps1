param(
    [ValidateSet('CodexLimit','UserTakeover')][string]$Reason='CodexLimit',
    [switch]$DryRun
)
$ErrorActionPreference='Stop'
$taskPython='D:\FlexBridge\.venv\Scripts\python.exe'
$taskRunner='D:\Codex\FlexBridge-agents\antigravity_master_runner.py'
if ($DryRun) {
    & $taskPython $taskRunner --dry-run --reason $Reason
    exit $LASTEXITCODE
}
$taskStamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$taskProcess=Start-Process -FilePath $taskPython -ArgumentList @($taskRunner,'--reason',$Reason) -WorkingDirectory 'D:\FlexBridge' -WindowStyle Hidden -PassThru -RedirectStandardOutput "D:\Codex\FlexBridge-agents\master_$taskStamp.stdout.txt" -RedirectStandardError "D:\Codex\FlexBridge-agents\master_$taskStamp.stderr.txt"
Write-Output "Started explicit takeover runner PID=$($taskProcess.Id). Inspect coordinator_state.json for acquired ownership; no automatic quota detection is claimed."
