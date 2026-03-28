[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipSmoke,
    [ValidateSet("base", "viewer")]
    [string]$PackageProfile = "base",
    [string]$DependencyMatrixPath = "",
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

$packageProfileEnvVar = "EA_NODE_EDITOR_PACKAGE_PROFILE"
$artifactRoot = Join-Path $repoRoot "artifacts\pyinstaller"
$buildDir = Join-Path (Join-Path $artifactRoot "build") $PackageProfile
$distDir = Join-Path (Join-Path $artifactRoot "dist") $PackageProfile

if ($Clean) {
    if (Test-Path $buildDir) {
        Remove-Item -Recurse -Force $buildDir
    }
    if (Test-Path $distDir) {
        Remove-Item -Recurse -Force $distDir
    }
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

function Get-DependencyAvailability {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExecutable
    )

    $probeScriptPath = [System.IO.Path]::GetTempFileName()
    $probeOutputPath = Join-Path $env:TEMP ("ea_node_editor_dependency_probe_" + [guid]::NewGuid().ToString("N") + ".json")
    Set-Content -Path $probeScriptPath -Encoding utf8 -Value @"
import importlib.util
import json
import sys
from pathlib import Path

modules = {
    "openpyxl": "openpyxl",
    "psutil": "psutil",
    "ansys_dpf_core": "ansys.dpf.core",
    "pyvista": "pyvista",
    "pyvistaqt": "pyvistaqt",
    "vtk": "vtkmodules",
}
payload = {key: bool(importlib.util.find_spec(value)) for key, value in modules.items()}
Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
"@

    try {
        $probeProcess = Start-Process -FilePath $PythonExecutable -ArgumentList @($probeScriptPath, $probeOutputPath) -PassThru -Wait
        if ($probeProcess.ExitCode -ne 0) {
            return @{
                openpyxl = "unknown"
                psutil = "unknown"
                ansys_dpf_core = "unknown"
                pyvista = "unknown"
                pyvistaqt = "unknown"
                vtk = "unknown"
            }
        }
        if (-not (Test-Path $probeOutputPath)) {
            return @{
                openpyxl = "unknown"
                psutil = "unknown"
                ansys_dpf_core = "unknown"
                pyvista = "unknown"
                pyvistaqt = "unknown"
                vtk = "unknown"
            }
        }
        $parsed = Get-Content -Path $probeOutputPath -Raw | ConvertFrom-Json
        return @{
            openpyxl = [bool]$parsed.openpyxl
            psutil = [bool]$parsed.psutil
            ansys_dpf_core = [bool]$parsed.ansys_dpf_core
            pyvista = [bool]$parsed.pyvista
            pyvistaqt = [bool]$parsed.pyvistaqt
            vtk = [bool]$parsed.vtk
        }
    }
    catch {
        return @{
            openpyxl = "unknown"
            psutil = "unknown"
            ansys_dpf_core = "unknown"
            pyvista = "unknown"
            pyvistaqt = "unknown"
            vtk = "unknown"
        }
    }
    finally {
        Remove-Item -Path $probeScriptPath, $probeOutputPath -Force -ErrorAction SilentlyContinue
    }
}

function Assert-PackageProfileDependencies {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("base", "viewer")]
        [string]$Profile,
        [Parameter(Mandatory = $true)]
        [hashtable]$Availability
    )

    if ($Profile -ne "viewer") {
        return
    }

    $requiredModules = @(
        @{ Key = "ansys_dpf_core"; Display = "ansys-dpf-core" },
        @{ Key = "pyvista"; Display = "pyvista" },
        @{ Key = "pyvistaqt"; Display = "pyvistaqt" },
        @{ Key = "vtk"; Display = "vtk" }
    )

    $missing = @()
    foreach ($module in $requiredModules) {
        if ($Availability[$module.Key] -ne $true) {
            $missing += $module.Display
        }
    }

    if ($missing.Count -gt 0) {
        throw (
            "Viewer package profile requires the optional ansys/viewer extras in the project venv. " +
            "Install .[ansys,viewer] or .[dev] before packaging. Missing: $($missing -join ', ')."
        )
    }
}

function Write-DependencyMatrix {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputPath,
        [Parameter(Mandatory = $true)]
        [hashtable]$Availability,
        [Parameter(Mandatory = $true)]
        [ValidateSet("base", "viewer")]
        [string]$Profile
    )

    $viewerPackagedBehavior = if ($Profile -eq "viewer") {
        "Viewer profile bundles the runtime stack and fails the build when missing from the build environment."
    }
    else {
        "Base profile excludes the viewer runtime stack to keep packaged builds lean."
    }

    $rows = @(
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "excel"
            dependency = "openpyxl"
            build_env_installed = $Availability.openpyxl
            source_runtime_behavior = "Excel Read/Write: CSV always works; XLSX requires openpyxl and emits deterministic RuntimeError when unavailable."
            packaged_runtime_behavior = "Same node behavior in packaged app; missing dependency message instructs rebuild with openpyxl in build environment."
            packaging_policy = "Optional include; bundled only if present in build environment."
            operator_action = "Install openpyxl before packaging when XLSX workflows are required."
        },
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "core"
            dependency = "psutil"
            build_env_installed = $Availability.psutil
            source_runtime_behavior = "System metrics require psutil for live CPU and RAM readings."
            packaged_runtime_behavior = "Packaged app must include psutil so the telemetry strip remains live."
            packaging_policy = "Required dependency; missing install is a packaging defect."
            operator_action = "Install psutil before packaging."
        },
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "ansys"
            dependency = "ansys-dpf-core"
            build_env_installed = $Availability.ansys_dpf_core
            source_runtime_behavior = "PyDPF runtime services remain optional until a DPF-backed workflow executes."
            packaged_runtime_behavior = $viewerPackagedBehavior
            packaging_policy = "Viewer profile only; required when building the viewer-enabled packaged app."
            operator_action = "Install the ansys extra before running a viewer-profile package build."
        },
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "viewer"
            dependency = "pyvista"
            build_env_installed = $Availability.pyvista
            source_runtime_behavior = "PyVista-backed mesh materialization stays optional until export or viewer rendering is requested."
            packaged_runtime_behavior = $viewerPackagedBehavior
            packaging_policy = "Viewer profile only; required when building the viewer-enabled packaged app."
            operator_action = "Install the viewer extra before running a viewer-profile package build."
        },
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "viewer"
            dependency = "pyvistaqt"
            build_env_installed = $Availability.pyvistaqt
            source_runtime_behavior = "PyVistaQt stays optional until Qt-hosted viewer surfaces are requested."
            packaged_runtime_behavior = $viewerPackagedBehavior
            packaging_policy = "Viewer profile only; required when building the viewer-enabled packaged app."
            operator_action = "Install the viewer extra before running a viewer-profile package build."
        },
        [PSCustomObject]@{
            package_profile = $Profile
            dependency_group = "viewer"
            dependency = "vtk"
            build_env_installed = $Availability.vtk
            source_runtime_behavior = "VTK stays optional until PyVista materialization or viewer rendering loads VTK modules."
            packaged_runtime_behavior = $viewerPackagedBehavior
            packaging_policy = "Viewer profile only; required when building the viewer-enabled packaged app."
            operator_action = "Install the viewer extra before running a viewer-profile package build."
        }
    )

    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    $rows | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding utf8
}

$dependencyAvailability = Get-DependencyAvailability -PythonExecutable $pythonExe
Assert-PackageProfileDependencies -Profile $PackageProfile -Availability $dependencyAvailability

if ([string]::IsNullOrWhiteSpace($DependencyMatrixPath)) {
    $DependencyMatrixPath = "artifacts\releases\packaging\$PackageProfile\dependency_matrix.csv"
}

$dependencyMatrixFullPath = if ([System.IO.Path]::IsPathRooted($DependencyMatrixPath)) {
    $DependencyMatrixPath
}
else {
    Join-Path $repoRoot $DependencyMatrixPath
}
Write-DependencyMatrix -OutputPath $dependencyMatrixFullPath -Availability $dependencyAvailability -Profile $PackageProfile
Write-Host "Dependency matrix written: $dependencyMatrixFullPath"

$buildArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--workpath", $buildDir,
    "--distpath", $distDir,
    $specFile
)

$previousPackageProfile = [System.Environment]::GetEnvironmentVariable($packageProfileEnvVar, "Process")
Write-Host "Building Windows package with PyInstaller (profile: $PackageProfile)..."
try {
    [System.Environment]::SetEnvironmentVariable($packageProfileEnvVar, $PackageProfile, "Process")
    $buildProcess = Start-Process -FilePath $pythonExe -ArgumentList $buildArgs -PassThru -Wait -NoNewWindow
    if ($buildProcess.ExitCode -ne 0) {
        throw "PyInstaller build failed with exit code $($buildProcess.ExitCode)."
    }
}
finally {
    [System.Environment]::SetEnvironmentVariable($packageProfileEnvVar, $previousPackageProfile, "Process")
}

$exePath = Join-Path $distDir "COREX_Node_Editor\COREX_Node_Editor.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected executable was not created: $exePath"
}

Write-Host "Build complete: $exePath"

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
