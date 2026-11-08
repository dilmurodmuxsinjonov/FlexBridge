param(
    [string]$PostgresBin = 'D:\Codex\.tools\postgresql-17.11\pgsql\bin',
    [ValidateRange(1024,65535)][int]$Port = 55440
)
$ErrorActionPreference='Stop'
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cluster=Join-Path $workspace 'backend\.data\pg_tests'
$oldAdmin=$env:FLEXBRIDGE_TEST_ADMIN_URL
$started=$false
if (!(Test-Path -LiteralPath (Join-Path $PostgresBin 'pg_ctl.exe'))) { throw 'Provide -PostgresBin pointing to PostgreSQL 17 binaries.' }
New-Item -ItemType Directory -Force -Path (Split-Path $cluster) | Out-Null
if (!(Test-Path -LiteralPath (Join-Path $cluster 'PG_VERSION'))) {
    & (Join-Path $PostgresBin 'initdb.exe') -D $cluster -U flexbridge_test -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Test cluster initialization failed.' }
}
try {
    & (Join-Path $PostgresBin 'pg_ctl.exe') -D $cluster -l (Join-Path $workspace 'backend\.data\pg_tests.log') -o "-h 127.0.0.1 -p $Port" -w start
    if ($LASTEXITCODE -ne 0) { throw 'Could not start the dedicated test cluster; inspect its log and port.' }
    $started=$true
    $env:FLEXBRIDGE_TEST_ADMIN_URL="postgresql+psycopg://flexbridge_test@127.0.0.1:$Port/postgres"
    Push-Location $workspace
    try { python -m pytest backend -q; $testExit=$LASTEXITCODE } finally { Pop-Location }
} finally {
    if ($started) { & (Join-Path $PostgresBin 'pg_ctl.exe') -D $cluster -m fast -w stop }
    $env:FLEXBRIDGE_TEST_ADMIN_URL=$oldAdmin
}
exit $testExit
