# Purpose: Refresh a working copy from the newest GitHub "Download ZIP" archive
#          sitting in Downloads, then clear those archives away.

<#
.SYNOPSIS
    Extracts the newest downloaded EA_Node source archive over a working copy.

.DESCRIPTION
    GitHub's "Download ZIP" button wraps the whole repository in a single
    top-level folder (EA_Node-main/), and the browser suffixes repeat downloads
    with " (1)", " (2)" and so on. This script:

      1. picks the most recently written archive in -DownloadsPath whose name is
         "<ArchiveBaseName>.zip" or "<ArchiveBaseName> (N).zip";
      2. skips past any leading single-folder levels, so the repository contents
         - not the wrapper folder - land directly in -DestinationPath,
         overwriting whatever is already there;
      3. deletes every matching archive from -DownloadsPath once extraction has
         succeeded.

    This is an overwrite, not a mirror: files that exist in the destination but
    not in the archive are left untouched.

.PARAMETER DownloadsPath
    Folder searched for archives.

.PARAMETER DestinationPath
    Folder the archive contents are written into. Created when missing.

.PARAMETER ArchiveBaseName
    Archive name without the ".zip" suffix and without any " (N)" copy marker.

.EXAMPLE
    .\scripts\sync_from_downloads_zip.ps1

.EXAMPLE
    .\scripts\sync_from_downloads_zip.ps1 -WhatIf

    Reports the archive that would be used and the archives that would be
    deleted, without writing or removing anything.

.EXAMPLE
    .\scripts\sync_from_downloads_zip.ps1 -DownloadsPath D:\Incoming -DestinationPath D:\work\EA_Node_Editor
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$DownloadsPath = "C:\Users\kamilemre.atay\Downloads",

    [ValidateNotNullOrEmpty()]
    [string]$DestinationPath = "C:\Users\kamilemre.atay\PycharmProjects\EA_Node_Editor",

    [ValidateNotNullOrEmpty()]
    [string]$ArchiveBaseName = "EA_Node-main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not ("System.IO.Compression.ZipFile" -as [type])) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
}

function Get-DownloadedArchive {
    # Newest first; the " (N)" copy marker only breaks ties on identical stamps.
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$BaseName
    )

    $pattern = "^{0}(?: \((?<copy>\d+)\))?\.zip$" -f [regex]::Escape($BaseName)
    $found = New-Object System.Collections.Generic.List[object]

    foreach ($file in Get-ChildItem -LiteralPath $Directory -File -Filter "*.zip") {
        if ($file.Name -match $pattern) {
            $copyIndex = 0
            if ($Matches.ContainsKey("copy")) {
                $copyIndex = [int]$Matches["copy"]
            }
            $found.Add([pscustomobject]@{
                File          = $file
                CopyIndex     = $copyIndex
                LastWriteTime = $file.LastWriteTime
            })
        }
    }

    # Emits loose objects; callers wrap in @() so a single match stays a list.
    return $found | Sort-Object -Property LastWriteTime, CopyIndex -Descending
}

function Get-ArchiveContentPrefix {
    # Descend while a level holds exactly one entry and that entry is a folder,
    # so a wrapper such as "EA_Node-main/" never reaches the destination.
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][System.IO.Compression.ZipArchive]$Archive
    )

    $prefix = ""

    while ($true) {
        $children = @{}

        foreach ($entry in $Archive.Entries) {
            $full = $entry.FullName.Replace("\", "/")
            if ($prefix.Length -gt 0 -and -not $full.StartsWith($prefix, [System.StringComparison]::Ordinal)) {
                continue
            }

            $relative = $full.Substring($prefix.Length)
            if ($relative.Length -eq 0) {
                continue
            }

            $name = $relative.Split("/")[0]
            if ($name.Length -eq 0) {
                continue
            }

            # Anything with a path separator after the first segment is a folder.
            $isDirectory = $relative.Length -gt $name.Length
            if ($children.ContainsKey($name)) {
                $children[$name] = $children[$name] -or $isDirectory
            }
            else {
                $children[$name] = $isDirectory
            }
        }

        if ($children.Count -eq 0) {
            throw "The archive has no entries to extract below '$prefix'."
        }

        if ($children.Count -ne 1) {
            break
        }

        $onlyName = @($children.Keys)[0]
        if (-not $children[$onlyName]) {
            break
        }

        $prefix = "$prefix$onlyName/"
    }

    return $prefix
}

function Expand-ArchiveContent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][System.IO.Compression.ZipArchive]$Archive,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Prefix,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $root = $Destination
    if (-not $root.EndsWith("\")) {
        $root = "$root\"
    }

    $fileCount = 0

    foreach ($entry in $Archive.Entries) {
        $full = $entry.FullName.Replace("\", "/")
        if ($Prefix.Length -gt 0 -and -not $full.StartsWith($Prefix, [System.StringComparison]::Ordinal)) {
            continue
        }

        $relative = $full.Substring($Prefix.Length)
        if ($relative.Length -eq 0) {
            continue
        }

        $target = [System.IO.Path]::GetFullPath((Join-Path $root $relative.Replace("/", "\")))
        if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Archive entry '$($entry.FullName)' would be written outside '$Destination'."
        }

        if ($relative.EndsWith("/")) {
            if (-not (Test-Path -LiteralPath $target -PathType Container)) {
                New-Item -ItemType Directory -Path $target -Force | Out-Null
            }
            continue
        }

        $parent = Split-Path -Parent $target
        if ($parent -and -not (Test-Path -LiteralPath $parent -PathType Container)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }

        if (Test-Path -LiteralPath $target -PathType Leaf) {
            # A read-only file would otherwise fail the overwrite.
            $existing = Get-Item -LiteralPath $target -Force
            if ($existing.Attributes -band [System.IO.FileAttributes]::ReadOnly) {
                $existing.Attributes = $existing.Attributes -bxor [System.IO.FileAttributes]::ReadOnly
            }
        }

        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
        $fileCount++
    }

    return $fileCount
}

$DownloadsPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($DownloadsPath)
$DestinationPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($DestinationPath)

if (-not (Test-Path -LiteralPath $DownloadsPath -PathType Container)) {
    throw "Downloads folder not found: $DownloadsPath"
}

$archives = @(Get-DownloadedArchive -Directory $DownloadsPath -BaseName $ArchiveBaseName)
if ($archives.Count -eq 0) {
    throw "No '$ArchiveBaseName.zip' or '$ArchiveBaseName (N).zip' archive found in $DownloadsPath."
}

$newest = $archives[0]
Write-Host "Archive:     $($newest.File.Name)"
Write-Host "Modified:    $($newest.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"
if ($archives.Count -gt 1) {
    Write-Host "Superseded:  $($archives.Count - 1) older matching archive(s), removed at the end."
}

if (-not (Test-Path -LiteralPath $DestinationPath -PathType Container)) {
    if ($PSCmdlet.ShouldProcess($DestinationPath, "Create destination folder")) {
        New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
    }
}

$zip = [System.IO.Compression.ZipFile]::OpenRead($newest.File.FullName)
try {
    if ($zip.Entries.Count -eq 0) {
        throw "Archive is empty: $($newest.File.FullName)"
    }

    $prefix = Get-ArchiveContentPrefix -Archive $zip
    if ($prefix.Length -gt 0) {
        Write-Host "Stripping:   $prefix"
    }
    Write-Host "Destination: $DestinationPath"

    if ($PSCmdlet.ShouldProcess($DestinationPath, "Extract '$($newest.File.Name)'")) {
        $extracted = Expand-ArchiveContent -Archive $zip -Prefix $prefix -Destination $DestinationPath
        Write-Host "Extracted:   $extracted file(s)."
    }
}
finally {
    $zip.Dispose()
}

# Re-read the folder so anything that landed mid-run is cleaned up too.
$removed = 0
foreach ($archive in @(Get-DownloadedArchive -Directory $DownloadsPath -BaseName $ArchiveBaseName)) {
    if ($PSCmdlet.ShouldProcess($archive.File.FullName, "Delete archive")) {
        Remove-Item -LiteralPath $archive.File.FullName -Force
        $removed++
    }
}

Write-Host "Deleted:     $removed archive(s) from $DownloadsPath"
