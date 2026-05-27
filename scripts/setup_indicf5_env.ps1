param(
    [switch]$Run,
    [string]$Python = "D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe",
    [string]$VenvPath = "D:\Vidiolingua\.venv_indicf5"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Vidiolingua"
$Requirements = Join-Path $ProjectRoot "requirements-indicf5.txt"
$TorchIndex = "https://download.pytorch.org/whl/cu121"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

function Assert-InProject {
    param([string]$PathValue, [string]$Label)
    $full = [System.IO.Path]::GetFullPath($PathValue)
    $root = [System.IO.Path]::GetFullPath($ProjectRoot)
    if (-not $full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay inside $ProjectRoot. Got: $full"
    }
    return $full
}

$VenvFull = Assert-InProject $VenvPath "VenvPath"
$RequirementsFull = Assert-InProject $Requirements "Requirements"

if ($VenvFull -ieq (Join-Path $ProjectRoot ".venv_tts")) {
    throw "Refusing to touch .venv_tts"
}
if ($VenvFull -ieq (Join-Path $ProjectRoot ".venv_indictrans2")) {
    throw "Refusing to touch .venv_indictrans2"
}

$Commands = @(
    @($Python, "-m", "venv", $VenvFull),
    @($VenvPython, "-m", "ensurepip", "--upgrade", "--default-pip"),
    @($VenvPython, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"),
    @($VenvPython, "-m", "pip", "install", "torch==2.5.1", "torchvision==0.20.1", "torchaudio==2.5.1", "--index-url", $TorchIndex),
    @($VenvPython, "-m", "pip", "install", "-r", $RequirementsFull)
)

Write-Host "IndicF5 setup target: $VenvFull"
Write-Host "Python: $Python"
Write-Host "Requirements: $RequirementsFull"
Write-Host "This script installs only into .venv_indicf5 and does not download the IndicF5 model."
Write-Host ""
Write-Host "Planned commands:"
foreach ($cmd in $Commands) {
    Write-Host ("  " + (($cmd | ForEach-Object { if ($_ -match "\s") { '"' + $_ + '"' } else { $_ } }) -join " "))
}

if (-not $Run) {
    Write-Host ""
    Write-Host "Dry run only. Re-run with -Run after approval to execute."
    exit 0
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python interpreter not found: $Python"
}
if (-not (Test-Path -LiteralPath $RequirementsFull)) {
    throw "Requirements file not found: $RequirementsFull"
}

foreach ($cmd in $Commands) {
    $exe = $cmd[0]
    $args = $cmd[1..($cmd.Count - 1)]
    Write-Host ""
    Write-Host ("Running: " + (($cmd | ForEach-Object { if ($_ -match "\s") { '"' + $_ + '"' } else { $_ } }) -join " "))
    & $exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $exe"
    }
}

Write-Host ""
Write-Host "IndicF5 environment setup finished. Model download/validation still requires separate approval."
