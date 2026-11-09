param(
    [switch]$SystemPrerequisites,
    [switch]$InstallDocker,
    [string]$InstallerDirectory = 'D:\Codex\Installers\FlexBridge',
    [string]$ApplicationDirectory = 'D:\Codex\Apps\DockerDesktop',
    [string]$EvidenceDirectory = 'D:\Codex\Setup'
)
# Run SystemPrerequisites in an administrator PowerShell; InstallDocker as the
# intended normal user after any required restart. Never restarts the computer.
$ErrorActionPreference = 'Stop'
if (-not $SystemPrerequisites -and -not $InstallDocker) {
    throw 'Choose -SystemPrerequisites or -InstallDocker; see ANTIGRAVITY_HANDOFF.md.'
}
if ($SystemPrerequisites -and $InstallDocker) {
    throw 'Run system prerequisites elevated and Docker per-user installation separately.'
}
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null

function Assert-PublisherInstaller($filePath, $expectedHash, $publisherPattern) {
    if (-not (Test-Path -LiteralPath $filePath)) { throw "Missing verified installer: $filePath" }
    if ((Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
        throw "Installer checksum mismatch: $filePath"
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $filePath
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch $publisherPattern) {
        throw "Installer publisher signature is invalid: $filePath"
    }
}

if ($SystemPrerequisites) {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Enabling Windows features and the WSL service requires native administrator approval.'
    }
    $msiPath = Join-Path $InstallerDirectory 'wsl.2.7.14.0.x64.msi'
    Assert-PublisherInstaller $msiPath 'db084e536279a59e90a26ec598d8aa8a4dff8309f41d078fd06242953ac1ebcd' 'Microsoft'
    $features = @()
    foreach ($featureName in @('VirtualMachinePlatform', 'Microsoft-Windows-Subsystem-Linux')) {
        $state = Get-WindowsOptionalFeature -Online -FeatureName $featureName
        if ($state.State -eq 'Disabled') {
            $enabled = Enable-WindowsOptionalFeature -Online -FeatureName $featureName -All -NoRestart
            $features += [ordered]@{name=$featureName;state=[string]$enabled.State;restartNeeded=[bool]$enabled.RestartNeeded}
        } else {
            $features += [ordered]@{name=$featureName;state=[string]$state.State;restartNeeded=($state.State -ne 'Enabled')}
        }
    }
    $msiLog = Join-Path $EvidenceDirectory 'flexbridge-wsl-msi.log'
    $msiResult = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList '/i',('"' + $msiPath + '"'),'/qn','/norestart','/L*v',('"' + $msiLog + '"')
    [ordered]@{features=$features;wslInstallerExit=$msiResult.ExitCode;automaticRestart=$false;at=(Get-Date -Format o)} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'flexbridge-system-setup.json') -Encoding UTF8
    if ($msiResult.ExitCode -notin @(0,3010)) { throw "WSL MSI failed: exit $($msiResult.ExitCode); inspect $msiLog" }
    Write-Output 'System setup finished. Check restartNeeded/installer exit3010; restart manually when convenient.'
}

if ($InstallDocker) {
    $feature = Get-CimInstance Win32_OptionalFeature -Filter "Name='VirtualMachinePlatform'"
    if ($feature.InstallState -ne 1) { throw 'VirtualMachinePlatform is not enabled. Complete system prerequisites and restart first.' }
    $dockerInstaller = Join-Path $InstallerDirectory 'DockerDesktop-4.99.0.exe'
    Assert-PublisherInstaller $dockerInstaller 'a5e299131c9c53d60f3f752b162078945eb5faf6eedcf0be20a214c6e6cea444' 'Docker'
    $desktop = Start-Process -FilePath $dockerInstaller -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList 'install','--user','--quiet','--accept-license','--backend=wsl-2',
        ('--installation-dir="' + $ApplicationDirectory + '"'),'--wsl-default-data-root=D:\Codex\Docker\wsl'
    [ordered]@{dockerInstallerExit=$desktop.ExitCode;requestedDirectory=$ApplicationDirectory;automaticRestart=$false;at=(Get-Date -Format o)} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'flexbridge-docker-setup.json') -Encoding UTF8
    if ($desktop.ExitCode -ne 0) { throw "Docker installer failed: exit $($desktop.ExitCode). Check the publisher install log." }
    $dockerCli = Join-Path $ApplicationDirectory 'resources\bin\docker.exe'
    if (-not (Test-Path -LiteralPath $dockerCli)) { throw 'Docker installer returned success but requested CLI location was not found; inspect actual installation.' }
    & $dockerCli --version
    & $dockerCli compose version
    Write-Output 'CLI installation verified. Start Docker Desktop and verify docker info/hello-world before claiming engine readiness.'
}
