$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$basePython = Join-Path $root ".uv_python\cpython-3.11.11-windows-x86_64-none\python.exe"
$venv = Join-Path $root ".venv_bgm"

if (-not (Test-Path $basePython)) {
    throw "Python 3.11 is missing. Install Python 3.11 or restore $basePython."
}
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $basePython -m venv $venv
}

$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root "requirements-bgm.txt")
