param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$apiPython = Join-Path $root ".venv_api\Scripts\python.exe"
$python = if (Test-Path $apiPython) { $apiPython } else { "python" }

$argsList = @("-m", "tools.preflight_environment")
if ($Json) {
    $argsList += "--json"
}

& $python @argsList
exit $LASTEXITCODE
