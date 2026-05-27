param(
    [switch]$Install,
    [string]$Python = "python",
    [ValidateSet("cu121", "cpu")]
    [string]$TorchFlavor = "cu121"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $ProjectRoot ".venv_indictrans2"
$RequirementsPath = Join-Path $ProjectRoot "requirements-indictrans2.txt"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "IndicTrans2 setup script for VidioLingua"
Write-Host "Project: $ProjectRoot"
Write-Host "Target venv: $VenvPath"
Write-Host "Requirements: $RequirementsPath"
Write-Host "This script targets only .venv_indictrans2 and does not touch .venv_tts."
Write-Host ""

if (-not $Install) {
    Write-Host "Dry run only. Re-run with -Install after approval to create/install the environment."
    Write-Host "Recommended: pass -Python with a Python 3.11 x64 executable path."
    Write-Host ""
    Write-Host "Planned commands:"
    Write-Host "$Python -m venv `"$VenvPath`""
    Write-Host "`"$VenvPython`" -m pip install --upgrade pip setuptools wheel"
    if ($TorchFlavor -eq "cu121") {
        Write-Host "`"$VenvPython`" -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121"
    } else {
        Write-Host "`"$VenvPython`" -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu"
    }
    Write-Host "`"$VenvPython`" -m pip install -r `"$RequirementsPath`""
    exit 0
}

if ($VenvPath -like "*\.venv_tts*") {
    throw "Refusing to run: target path unexpectedly points at .venv_tts."
}

if (-not (Test-Path -LiteralPath $RequirementsPath)) {
    throw "Missing requirements file: $RequirementsPath"
}

$VersionText = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($VersionText -notin @("3.10", "3.11")) {
    throw "Refusing to create .venv_indictrans2 with Python $VersionText. Use Python 3.11 x64, or Python 3.10 x64 as fallback."
}

& $Python -m venv $VenvPath
& $VenvPython -m pip install --upgrade pip setuptools wheel

if ($TorchFlavor -eq "cu121") {
    & $VenvPython -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
} else {
    & $VenvPython -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
}

& $VenvPython -m pip install -r $RequirementsPath

Write-Host ""
Write-Host "IndicTrans2 environment install finished."
Write-Host "Next, after model-download approval, use:"
Write-Host "`"$VenvPath\Scripts\hf.exe`" auth login"
Write-Host "`"$VenvPath\Scripts\hf.exe`" download ai4bharat/indictrans2-en-indic-dist-200M --local-dir models\indictrans2\en-indic-dist-200M"
