[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipSmoke,
    [string]$DependencyMatrixPath = "docs\specs\perf\rc3\dependency_matrix.csv",
    [ValidateRange(2, 60)]
    [int]$SmokeSeconds = 5
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Virtualenv Python was not found at $pythonExe"
}

$specFile = Join-Path $repoRoot "ea_node_editor.spec"
if (-not (Test-Path $specFile)) {
    throw "PyInstaller spec file not found: $specFile"
}

$artifactRoot = Join-Path $repoRoot "artifacts\pyinstaller"
$buildDir = Join-Path $artifactRoot "build"
$distDir = Join-Path $artifactRoot "dist"

if ($Clean -and (Test-Path $artifactRoot)) {
    Remove-Item -Recurse -Force $artifactRoot
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

$buildArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--workpath", $buildDir,
    "--distpath", $distDir,
    $specFile
)

Write-Host "Building Windows package with PyInstaller..."
& $pythonExe @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

$exePath = Join-Path $distDir "COREX_Node_Editor\COREX_Node_Editor.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected executable was not created: $exePath"
}

Write-Host "Build complete: $exePath"

function Get-DependencyAvailability {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExecutable
    )

    $probeScript = "import importlib.util, json; print(json.dumps({'openpyxl': bool(importlib.util.find_spec('openpyxl')), 'psutil': bool(importlib.util.find_spec('psutil'))}))"

    try {
        $raw = & $PythonExecutable -c $probeScript
        if ($LASTEXITCODE -ne 0) {
            return @{
                openpyxl = "unknown"
                psutil = "unknown"
            }
        }
        $parsed = $raw | ConvertFrom-Json
        return @{
            openpyxl = [bool]$parsed.openpyxl
            psutil = [bool]$parsed.psutil
        }
    }
    catch {
        return @{
            openpyxl = "unknown"
            psutil = "unknown"
        }
    }
}

function Write-DependencyMatrix {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputPath,
        [Parameter(Mandatory = $true)]
        [hashtable]$Availability
    )

    $rows = @(
        [PSCustomObject]@{
            dependency = "openpyxl"
            build_env_installed = $Availability.openpyxl
            source_runtime_behavior = "Excel Read/Write: CSV always works; XLSX requires openpyxl and emits deterministic RuntimeError when unavailable."
            packaged_runtime_behavior = "Same node behavior in packaged app; missing dependency message instructs rebuild with openpyxl in build environment."
            packaging_policy = "Optional include; bundled only if present in build environment."
            operator_action = "Install openpyxl before packaging when XLSX workflows are required."
        },
        [PSCustomObject]@{
            dependency = "psutil"
            build_env_installed = $Availability.psutil
            source_runtime_behavior = "System metrics require psutil for live CPU and RAM readings."
            packaged_runtime_behavior = "Packaged app must include psutil so the telemetry strip remains live."
            packaging_policy = "Required dependency; missing install is a packaging defect."
            operator_action = "Install psutil before packaging."
        }
    )

    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    $rows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding utf8
}

$dependencyAvailability = Get-DependencyAvailability -PythonExecutable $pythonExe
$dependencyMatrixFullPath = if ([System.IO.Path]::IsPathRooted($DependencyMatrixPath)) {
    $DependencyMatrixPath
}
else {
    Join-Path $repoRoot $DependencyMatrixPath
}
Write-DependencyMatrix -OutputPath $dependencyMatrixFullPath -Availability $dependencyAvailability
Write-Host "Dependency matrix written: $dependencyMatrixFullPath"

if ($SkipSmoke) {
    Write-Host "Smoke test skipped."
    exit 0
}

Write-Host "Running startup smoke test ($SmokeSeconds s)..."
$previousQtPlatform = $env:QT_QPA_PLATFORM
$process = $null
try {
    $env:QT_QPA_PLATFORM = "offscreen"
    $process = Start-Process -FilePath $exePath -WorkingDirectory (Split-Path $exePath -Parent) -PassThru
    Start-Sleep -Seconds $SmokeSeconds

    if ($process.HasExited) {
        throw "Smoke test failed: executable exited early with code $($process.ExitCode)."
    }

    Stop-Process -Id $process.Id -Force
    Write-Host "Smoke test passed: process stayed alive for $SmokeSeconds seconds."
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    if ($null -eq $previousQtPlatform) {
        Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    }
    else {
        $env:QT_QPA_PLATFORM = $previousQtPlatform
    }
}
