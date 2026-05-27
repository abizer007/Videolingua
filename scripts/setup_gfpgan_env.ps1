$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python310 = Get-Command python3.10 -ErrorAction SilentlyContinue

if (-not $python310) {
    throw "Python 3.10 is required for the isolated GFPGAN env. Install Python 3.10 x64, then rerun this script."
}

$venv = Join-Path $root ".venv_gfpgan"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $python310.Source -m venv $venv
}

$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root "requirements-gfpgan.txt")
