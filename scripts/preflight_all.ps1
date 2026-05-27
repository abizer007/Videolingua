param(
    [string]$Video = "Vidiolingua_Test_Official.mp4",
    [string]$TargetLanguage = "fr",
    [string]$Reference = "test_speaker_ref.wav",
    [string]$Output = "outputs\preflight_french.wav",
    [string]$ModelPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$apiPython = Join-Path $root ".venv_api\Scripts\python.exe"
$ttsPython = Join-Path $root ".venv_tts\Scripts\python.exe"
$python = if (Test-Path $apiPython) { $apiPython } else { "python" }
$pipelinePython = if (Test-Path $ttsPython) { $ttsPython } else { $python }

$env:VIDIOLINGUA_TRANSLATION_ENGINE = "google"
& $python -m tools.preflight_environment --all --video $Video
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$argsList = @(
    "-m", "tools.preflight_video_translation_pipeline",
    "--video", $Video,
    "--target-language", $TargetLanguage,
    "--reference", $Reference,
    "--output", $Output
)
if ($ModelPath) {
    $argsList += @("--model-path", $ModelPath)
}
& $pipelinePython @argsList
exit $LASTEXITCODE
