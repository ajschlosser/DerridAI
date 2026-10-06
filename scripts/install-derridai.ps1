# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$InstallDir = "",
    [switch]$AddToPath
)

$ErrorActionPreference = "Stop"

$Repository = "ajschlosser/DerridAI"
$Target = "windows-x86_64"
$Asset = "derridai-windows-x86_64.exe"
$ChecksumAsset = "$Asset.sha256"

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "DerridAI currently supports 64-bit Windows only."
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "DerridAI\bin"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $BaseUrl = "https://github.com/$Repository/releases/latest/download"
}
else {
    $Tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
    $BaseUrl = "https://github.com/$Repository/releases/download/$Tag"
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("derridai-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TempDir | Out-Null

try {
    $BinaryPath = Join-Path $TempDir $Asset
    $ChecksumPath = Join-Path $TempDir $ChecksumAsset

    Write-Host "Downloading DerridAI for $Target..."
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/$Asset" -OutFile $BinaryPath
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/$ChecksumAsset" -OutFile $ChecksumPath

    $Expected = ((Get-Content -Path $ChecksumPath -TotalCount 1).Trim() -split "\s+")[0].ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($Expected)) {
        throw "Downloaded checksum file is empty."
    }

    $Actual = (Get-FileHash -Algorithm SHA256 -Path $BinaryPath).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) {
        throw "Checksum verification failed; refusing to install DerridAI."
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $Destination = Join-Path $InstallDir "derridai.exe"
    Copy-Item -Force -Path $BinaryPath -Destination $Destination

    if ($AddToPath) {
        $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $Parts = @($UserPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($Parts -notcontains $InstallDir) {
            $Updated = if ($UserPath) { "$UserPath;$InstallDir" } else { $InstallDir }
            [Environment]::SetEnvironmentVariable("Path", $Updated, "User")
            Write-Host "Added $InstallDir to the user PATH. Open a new terminal to use it."
        }
    }

    Write-Host "Installed $Destination"
    & $Destination --version
}
finally {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $TempDir
}
