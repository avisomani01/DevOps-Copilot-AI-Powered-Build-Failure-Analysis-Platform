[CmdletBinding()]
param(
    [switch]$Serve,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Find-Python {
    $localPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
    $candidates = @(
        $localPython,
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
    ) | Where-Object { $_ -and (Test-Path $_) }

    if ($candidates.Count -eq 0) {
        throw "Python 3.11+ was not found. Install it from https://www.python.org/downloads/ and run this script again."
    }

    return $candidates[0]
}

Push-Location $projectRoot
try {
    if (-not (Test-Path $venvPython)) {
        $python = Find-Python
        Write-Host "Creating virtual environment with $python"
        & $python -m venv .venv
    }

    & $venvPython -m pip install --requirement requirements.txt

    if (-not $SkipTests) {
        & $venvPython -m pytest -q
        & $venvPython evaluate.py
    }

    if ($Serve) {
        & $venvPython -m uvicorn app.main:app --reload --port 8000
    }
}
finally {
    Pop-Location
}
