param(
    [string]$OutputDir = "models\xtts_v2",
    [switch]$AgreeToCoquiTerms
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv_tts\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing TTS Python at $python"
}

$argsList = @("-m", "tools.download_xtts_v2_model", "--output-dir", $OutputDir)
if ($AgreeToCoquiTerms) {
    $argsList += "--agree-to-coqui-terms"
}

& $python @argsList
exit $LASTEXITCODE
