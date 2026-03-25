[CmdletBinding()]
param(
    [ValidateSet("base", "viewer")]
    [string]$PackageProfile = "base",
    [string]$DistPath = "",
    [string]$OutputRoot = "",
    [ValidateRange(2, 60)]
    [int]$SmokeSeconds = 5
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Resolve-PowerShellHostPath {
    $candidateNames = @(
        "powershell.exe",
        "pwsh.exe",
        "powershell",
        "pwsh"
    )

    foreach ($candidateName in $candidateNames) {
        try {
            $command = Get-Command $candidateName -ErrorAction Stop
            if (-not [string]::IsNullOrWhiteSpace($command.Source)) {
                return $command.Source
            }
            if (-not [string]::IsNullOrWhiteSpace($command.Path)) {
                return $command.Path
            }
            return $candidateName
        }
        catch {
            continue
        }
    }

    foreach ($candidatePath in @((Join-Path $PSHOME "powershell.exe"), (Join-Path $PSHOME "pwsh.exe"))) {
        if (Test-Path $candidatePath) {
            return $candidatePath
        }
    }

    throw "Unable to resolve a PowerShell host for installer validation."
}

function Invoke-PowerShellScriptFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostPath,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$InstallRoot
    )

    $childProcess = Start-Process -FilePath $HostPath -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $ScriptPath,
        "-InstallRoot",
        $InstallRoot
    ) -PassThru -Wait -NoNewWindow
    if ($childProcess.ExitCode -ne 0) {
        throw "PowerShell child host failed for script: $ScriptPath"
    }
}

function New-InstallerBundleZip {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BundleRoot,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $tarCommand = Get-Command "tar.exe" -ErrorAction SilentlyContinue
    if ($null -ne $tarCommand) {
        $tarProcess = Start-Process -FilePath $tarCommand.Source -ArgumentList @(
            "-a",
            "-cf",
            $DestinationPath,
            "-C",
            $BundleRoot,
            "payload",
            "scripts"
        ) -PassThru -Wait -NoNewWindow
        if ($tarProcess.ExitCode -ne 0) {
            throw "tar.exe failed with exit code $($tarProcess.ExitCode)."
        }
        if (-not (Test-Path $DestinationPath)) {
            throw "tar.exe did not create installer bundle: $DestinationPath"
        }
        if ((Get-Item $DestinationPath).Length -le 0) {
            throw "tar.exe created an empty installer bundle: $DestinationPath"
        }
        return
    }

    Compress-Archive -Path (Join-Path $BundleRoot "payload"), (Join-Path $BundleRoot "scripts") -DestinationPath $DestinationPath -Force
    if (-not (Test-Path $DestinationPath)) {
        throw "Compress-Archive did not create installer bundle: $DestinationPath"
    }
    if ((Get-Item $DestinationPath).Length -le 0) {
        throw "Compress-Archive created an empty installer bundle: $DestinationPath"
    }
}

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

if ([string]::IsNullOrWhiteSpace($DistPath)) {
    $DistPath = "artifacts\pyinstaller\dist\$PackageProfile\COREX_Node_Editor"
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = "artifacts\releases\installer\$PackageProfile"
}

$resolvedDistPath = Resolve-RepoPath -PathValue $DistPath
if (-not (Test-Path $resolvedDistPath)) {
    throw "PyInstaller dist folder not found: $resolvedDistPath"
}

$sourceExe = Join-Path $resolvedDistPath "COREX_Node_Editor.exe"
if (-not (Test-Path $sourceExe)) {
    throw "Expected packaged executable not found: $sourceExe"
}

$resolvedOutputRoot = Resolve-RepoPath -PathValue $OutputRoot
New-Item -ItemType Directory -Path $resolvedOutputRoot -Force | Out-Null

$runId = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleRoot = Join-Path $resolvedOutputRoot $runId
$payloadRoot = Join-Path $bundleRoot "payload\COREX_Node_Editor"
$scriptRoot = Join-Path $bundleRoot "scripts"

New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null
New-Item -ItemType Directory -Path $scriptRoot -Force | Out-Null

Copy-Item -Path (Join-Path $resolvedDistPath "*") -Destination $payloadRoot -Recurse -Force

$installScriptPath = Join-Path $scriptRoot "Install-COREX_Node_Editor.ps1"
$uninstallScriptPath = Join-Path $scriptRoot "Uninstall-COREX_Node_Editor.ps1"

$installScript = @'
[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\COREX_Node_Editor"
)

$ErrorActionPreference = "Stop"
$packageRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$payload = Join-Path $packageRoot "payload\COREX_Node_Editor"
if (-not (Test-Path $payload)) {
    throw "Installer payload not found: $payload"
}

$targetDir = Join-Path $InstallRoot "COREX_Node_Editor"
if (Test-Path $targetDir) {
    Remove-Item -Recurse -Force $targetDir
}
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
Copy-Item -Path (Join-Path $payload "*") -Destination $targetDir -Recurse -Force

$record = [ordered]@{
    installed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    install_root = $InstallRoot
    install_dir = $targetDir
    executable = (Join-Path $targetDir "COREX_Node_Editor.exe")
}
$recordPath = Join-Path $InstallRoot "install_record.json"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $recordPath
Write-Host "Installed to: $targetDir"
'@

$uninstallScript = @'
[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\COREX_Node_Editor"
)

$ErrorActionPreference = "Stop"
$targetDir = Join-Path $InstallRoot "COREX_Node_Editor"
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

$bundleZip = Join-Path $bundleRoot "COREX_Node_Editor_installer_bundle_$runId.zip"
$zipCreated = $false
$zipError = ""
try {
    New-InstallerBundleZip -BundleRoot $bundleRoot -DestinationPath $bundleZip
    $zipCreated = $true
    $zipError = ""
}
catch {
    $zipError = $_.Exception.Message
}
if (-not $zipCreated) {
    Write-Warning "Installer zip creation skipped: $zipError"
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
$expandedInstallScript = Join-Path $packageRootForValidation "scripts\Install-COREX_Node_Editor.ps1"
$expandedUninstallScript = Join-Path $packageRootForValidation "scripts\Uninstall-COREX_Node_Editor.ps1"
$validationShellPath = Resolve-PowerShellHostPath

try {
    Invoke-PowerShellScriptFile -HostPath $validationShellPath -ScriptPath $expandedInstallScript -InstallRoot $validationInstallRoot
}
catch {
    throw "Installer validation failed during install phase."
}

$installedExe = Join-Path $validationInstallRoot "COREX_Node_Editor\COREX_Node_Editor.exe"
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

try {
    Invoke-PowerShellScriptFile -HostPath $validationShellPath -ScriptPath $expandedUninstallScript -InstallRoot $validationInstallRoot
}
catch {
    throw "Installer validation failed during uninstall phase."
}

$postUninstallExe = Join-Path $validationInstallRoot "COREX_Node_Editor\COREX_Node_Editor.exe"
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
    package_profile = $PackageProfile
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
        validation_shell = $validationShellPath
    }
    packaging = [ordered]@{
        package_profile = $PackageProfile
        zip_created = $zipCreated
        zip_error = $zipError
        package_root = $bundleRoot
    }
}

$validationReportPath = Join-Path $bundleRoot "installer_validation.json"
$validationReport | ConvertTo-Json -Depth 10 | Set-Content -Path $validationReportPath

$manifest = [ordered]@{
    run_id = $runId
    package_profile = $PackageProfile
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
        package_profile = $PackageProfile
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
