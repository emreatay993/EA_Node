[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipSmoke,
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

$exePath = Join-Path $distDir "EA_Node_Editor\EA_Node_Editor.exe"
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
