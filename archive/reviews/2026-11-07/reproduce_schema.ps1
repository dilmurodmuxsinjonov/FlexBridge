$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$reviewSource = Join-Path $reviewRoot 'specs/v1_4/verify_v1_4_schema.mjs'
$reviewDestination = (Join-Path $PSScriptRoot 'schema_verification.json').Replace('\', '/')
$reviewScript = Get-Content -LiteralPath $reviewSource -Raw -Encoding utf8
$reviewOldLine = "const reportPath = 'D:/FlexBridge/specs/v1_4/v1_4_schema_verification.json';"
if (-not $reviewScript.Contains($reviewOldLine)) {
    throw 'Expected report path declaration not found; canonical report will not be overwritten.'
}
$reviewScript = $reviewScript.Replace($reviewOldLine, "const reportPath = '$reviewDestination';")
$reviewScript | node --input-type=module
if ($LASTEXITCODE -ne 0) { throw "Schema verifier exited with code $LASTEXITCODE" }
