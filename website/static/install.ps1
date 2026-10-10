$ErrorActionPreference = "Stop"

$UvInstallerUrl = "https://astral.sh/uv/install.ps1"

function Find-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    $candidates = @()
    if ($env:UV_INSTALL_DIR) {
        $candidates += Join-Path $env:UV_INSTALL_DIR "uv.exe"
    }
    if ($env:XDG_BIN_HOME) {
        $candidates += Join-Path $env:XDG_BIN_HOME "uv.exe"
    }
    $candidates += Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    $candidates += Join-Path $env:USERPROFILE ".cargo\bin\uv.exe"

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    return $null
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host "Je uses uv to manage its isolated Python environment."
    Write-Host "uv was not found, so the official uv installer will be run now."

    $installer = Invoke-RestMethod $UvInstallerUrl
    Invoke-Expression $installer

    $uv = Find-Uv
    if (-not $uv) {
        throw "uv was installed but its executable could not be found. Open a new terminal and run: uv tool install git+https://github.com/JeffreyLei03/JE.git"
    }
}

Write-Host "Installing Je with $uv ..."
& $uv tool install git+https://github.com/JeffreyLei03/JE.git
if ($LASTEXITCODE -ne 0) {
    throw "uv could not install Je."
}

$toolBin = (& $uv tool dir --bin | Select-Object -Last 1).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "uv could not locate its tool executable directory."
}
$je = Join-Path $toolBin "je.exe"
if (-not (Test-Path -LiteralPath $je -PathType Leaf)) {
    throw "Je was installed but $je was not found."
}

& $je --version
if ($LASTEXITCODE -ne 0) {
    throw "Je was installed but could not be started."
}
Write-Host "Je is installed. Run: je"

$pathEntries = $env:PATH -split ";"
if ($toolBin -notin $pathEntries) {
    Write-Host "Restart PowerShell if 'je' is not found; $toolBin must be on PATH."
}
