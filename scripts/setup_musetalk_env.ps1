$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python310 = Get-Command python3.10 -ErrorAction SilentlyContinue

if (-not $python310) {
    throw "Python 3.10 is required for MuseTalk. Install Python 3.10 x64, then rerun this script."
}

$venv = Join-Path $root ".venv_musetalk"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $python310.Source -m venv $venv
}

$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root "requirements-musetalk.txt")

Write-Host "Clone MuseTalk 1.5 and install its upstream pinned requirements in this env before enabling VIDIOLINGUA_MUSETALK_DIR."
