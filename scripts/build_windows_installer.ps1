[CmdletBinding()]
param(
    [string]$DistPath = "artifacts\pyinstaller\dist\EA_Node_Editor",
    [string]$OutputRoot = "artifacts\releases\installer",
    [ValidateRange(2, 60)]
    [int]$SmokeSeconds = 5
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return Join-Path $repoRoot $PathValue
}

$resolvedDistPath = Resolve-RepoPath -PathValue $DistPath
if (-not (Test-Path $resolvedDistPath)) {
    throw "PyInstaller dist folder not found: $resolvedDistPath"
}

$sourceExe = Join-Path $resolvedDistPath "EA_Node_Editor.exe"
if (-not (Test-Path $sourceExe)) {
    throw "Expected packaged executable not found: $sourceExe"
}

$resolvedOutputRoot = Resolve-RepoPath -PathValue $OutputRoot
New-Item -ItemType Directory -Path $resolvedOutputRoot -Force | Out-Null

$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleRoot = Join-Path $resolvedOutputRoot $runId
$payloadRoot = Join-Path $bundleRoot "payload\EA_Node_Editor"
$scriptRoot = Join-Path $bundleRoot "scripts"

New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null
New-Item -ItemType Directory -Path $scriptRoot -Force | Out-Null

Copy-Item -Path (Join-Path $resolvedDistPath "*") -Destination $payloadRoot -Recurse -Force

$installScriptPath = Join-Path $scriptRoot "Install-EA_Node_Editor.ps1"
$uninstallScriptPath = Join-Path $scriptRoot "Uninstall-EA_Node_Editor.ps1"

$installScript = @'
[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\EA_Node_Editor"
)

$ErrorActionPreference = "Stop"
$packageRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$payload = Join-Path $packageRoot "payload\EA_Node_Editor"
if (-not (Test-Path $payload)) {
    throw "Installer payload not found: $payload"
}

$targetDir = Join-Path $InstallRoot "EA_Node_Editor"
if (Test-Path $targetDir) {
    Remove-Item -Recurse -Force $targetDir
}
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
Copy-Item -Path (Join-Path $payload "*") -Destination $targetDir -Recurse -Force

$record = [ordered]@{
    installed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    install_root = $InstallRoot
    install_dir = $targetDir
    executable = (Join-Path $targetDir "EA_Node_Editor.exe")
}
$recordPath = Join-Path $InstallRoot "install_record.json"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $recordPath
Write-Host "Installed to: $targetDir"
'@

$uninstallScript = @'
[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\EA_Node_Editor"
)

$ErrorActionPreference = "Stop"
$targetDir = Join-Path $InstallRoot "EA_Node_Editor"
if (Test-Path $targetDir) {
    Remove-Item -Recurse -Force $targetDir
}
$recordPath = Join-Path $InstallRoot "install_record.json"
if (Test-Path $recordPath) {
    Remove-Item -Force $recordPath
}
Write-Host "Uninstalled from: $targetDir"
'@

Set-Content -Path $installScriptPath -Value $installScript
Set-Content -Path $uninstallScriptPath -Value $uninstallScript

$bundleZip = Join-Path $bundleRoot "EA_Node_Editor_installer_bundle_$runId.zip"
$zipCreated = $false
$zipError = ""
for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        Compress-Archive -Path (Join-Path $bundleRoot "payload"), (Join-Path $bundleRoot "scripts") -DestinationPath $bundleZip -Force
        $zipCreated = $true
        $zipError = ""
        break
    }
    catch {
        $zipError = $_.Exception.Message
        if ($attempt -lt 5) {
            Start-Sleep -Seconds 2
        }
    }
}
if (-not $zipCreated) {
    Write-Warning "Installer zip creation skipped after retries: $zipError"
}

$validationTempRoot = Join-Path $env:TEMP "ea_installer_validation_$runId"
if (Test-Path $validationTempRoot) {
    Remove-Item -Recurse -Force $validationTempRoot
}
New-Item -ItemType Directory -Path $validationTempRoot -Force | Out-Null

$packageRootForValidation = $bundleRoot
if ($zipCreated) {
    $expandedRoot = Join-Path $validationTempRoot "expanded"
    Expand-Archive -Path $bundleZip -DestinationPath $expandedRoot -Force
    $packageRootForValidation = $expandedRoot
}

$validationInstallRoot = Join-Path $validationTempRoot "install_root"
$expandedInstallScript = Join-Path $packageRootForValidation "scripts\Install-EA_Node_Editor.ps1"
$expandedUninstallScript = Join-Path $packageRootForValidation "scripts\Uninstall-EA_Node_Editor.ps1"

& powershell -NoProfile -ExecutionPolicy Bypass -File $expandedInstallScript -InstallRoot $validationInstallRoot
if ($LASTEXITCODE -ne 0) {
    throw "Installer validation failed during install phase."
}

$installedExe = Join-Path $validationInstallRoot "EA_Node_Editor\EA_Node_Editor.exe"
if (-not (Test-Path $installedExe)) {
    throw "Installer validation failed: installed executable not found at $installedExe"
}

$previousQtPlatform = $env:QT_QPA_PLATFORM
$smokePassed = $false
$smokeExitCode = $null
$smokeProcess = $null
try {
    $env:QT_QPA_PLATFORM = "offscreen"
    $smokeProcess = Start-Process -FilePath $installedExe -WorkingDirectory (Split-Path $installedExe -Parent) -PassThru
    Start-Sleep -Seconds $SmokeSeconds
    if ($smokeProcess.HasExited) {
        $smokeExitCode = $smokeProcess.ExitCode
        throw "Installer validation failed: installed executable exited early with code $smokeExitCode."
    }
    Stop-Process -Id $smokeProcess.Id -Force
    $smokePassed = $true
}
finally {
    if ($null -ne $smokeProcess -and -not $smokeProcess.HasExited) {
        Stop-Process -Id $smokeProcess.Id -Force
    }
    if ($null -eq $previousQtPlatform) {
        Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    }
    else {
        $env:QT_QPA_PLATFORM = $previousQtPlatform
    }
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $expandedUninstallScript -InstallRoot $validationInstallRoot
if ($LASTEXITCODE -ne 0) {
    throw "Installer validation failed during uninstall phase."
}

$postUninstallExe = Join-Path $validationInstallRoot "EA_Node_Editor\EA_Node_Editor.exe"
$uninstallPassed = -not (Test-Path $postUninstallExe)
if (-not $uninstallPassed) {
    throw "Installer validation failed: executable still exists after uninstall."
}

$sourceExeHash = (Get-FileHash -Path $sourceExe -Algorithm SHA256).Hash
$bundleHash = ""
if ($zipCreated -and (Test-Path $bundleZip)) {
    $bundleHash = (Get-FileHash -Path $bundleZip -Algorithm SHA256).Hash
}

$validationReport = [ordered]@{
    run_id = $runId
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    source_dist_path = $resolvedDistPath
    source_exe = $sourceExe
    source_exe_sha256 = $sourceExeHash
    installer_bundle = if ($zipCreated) { $bundleZip } else { "" }
    installer_bundle_sha256 = $bundleHash
    validation = [ordered]@{
        install_phase = "pass"
        smoke_phase = if ($smokePassed) { "pass" } else { "fail" }
        smoke_seconds = $SmokeSeconds
        smoke_exit_code = $smokeExitCode
        uninstall_phase = if ($uninstallPassed) { "pass" } else { "fail" }
        install_root = $validationInstallRoot
    }
    packaging = [ordered]@{
        zip_created = $zipCreated
        zip_error = $zipError
        package_root = $bundleRoot
    }
}

$validationReportPath = Join-Path $bundleRoot "installer_validation.json"
$validationReport | ConvertTo-Json -Depth 10 | Set-Content -Path $validationReportPath

$manifest = [ordered]@{
    run_id = $runId
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    artifacts = [ordered]@{
        bundle_root = $bundleRoot
        installer_bundle = if ($zipCreated) { $bundleZip } else { "" }
        install_script = $installScriptPath
        uninstall_script = $uninstallScriptPath
        validation_report = $validationReportPath
    }
    checksums = [ordered]@{
        source_exe_sha256 = $sourceExeHash
        installer_bundle_sha256 = $bundleHash
    }
    packaging = [ordered]@{
        zip_created = $zipCreated
        zip_error = $zipError
    }
}

$manifestPath = Join-Path $bundleRoot "installer_manifest.json"
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestPath

try {
    Remove-Item -Recurse -Force $validationTempRoot
}
catch {
    # Non-fatal cleanup failure.
}

if ($zipCreated) {
    Write-Host "Installer bundle created: $bundleZip"
}
else {
    Write-Host "Installer bundle zip was not created; folder artifact retained: $bundleRoot"
}
Write-Host "Installer manifest: $manifestPath"
Write-Host "Installer validation: $validationReportPath"
Write-Host "Installer pipeline PASS."
