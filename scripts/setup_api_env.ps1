$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv_api"
$repoPython = Join-Path $root ".uv_python\cpython-3.11.11-windows-x86_64-none\python.exe"
$python = if (Test-Path $repoPython) { $repoPython } else { "python" }

function Invoke-Checked {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)
    & $Command[0] @($Command[1..($Command.Length - 1)])
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($Command -join ' ')"
    }
}

Invoke-Checked $python --version

if (-not (Test-Path (Join-Path $venv "Scripts\python.exe")) -or -not (Test-Path (Join-Path $venv "Scripts\pip.exe"))) {
    Invoke-Checked $python -m venv --clear $venv
}

$venvPython = Join-Path $venv "Scripts\python.exe"
Invoke-Checked $venvPython -m pip install --upgrade pip
Invoke-Checked $venvPython -m pip install -r (Join-Path $root "requirements-api.txt")
