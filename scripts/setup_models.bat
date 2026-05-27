@echo off
REM ============================================================
REM VidioLingua — Model Setup Script
REM Clones SadTalker and GFPGAN repos and downloads checkpoints.
REM Run once before first use.
REM ============================================================

echo [Setup] VidioLingua Phase 1 Model Setup
echo ==========================================

set ROOT=%~dp0..
set ML_DIR=%ROOT%\ml

REM Create ml/ dir if not exists
if not exist "%ML_DIR%" mkdir "%ML_DIR%"

REM -----------------------------------------------------------
REM 1. SadTalker
REM -----------------------------------------------------------
echo.
echo [1/3] Setting up SadTalker...
if exist "%ML_DIR%\SadTalker\" (
    echo SadTalker already cloned. Skipping.
) else (
    git clone https://github.com/OpenTalker/SadTalker.git "%ML_DIR%\SadTalker"
    if errorlevel 1 (
        echo ERROR: Failed to clone SadTalker. Check your internet connection.
        pause
        exit /b 1
    )
)

REM Download SadTalker checkpoints
echo Downloading SadTalker checkpoints (this may take a few minutes)...
cd /d "%ML_DIR%\SadTalker"
if exist "checkpoints\" (
    echo Checkpoints already exist. Skipping download.
) else (
    mkdir checkpoints
    REM Download using Python + requests (if available) or curl
    curl -L "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar" -o "checkpoints\mapping_00109-model.pth.tar"
    curl -L "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar" -o "checkpoints\mapping_00229-model.pth.tar"
    curl -L "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors" -o "checkpoints\SadTalker_V0.0.2_256.safetensors"
    curl -L "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors" -o "checkpoints\SadTalker_V0.0.2_512.safetensors"
    echo SadTalker checkpoints downloaded.
)

REM -----------------------------------------------------------
REM 2. GFPGAN
REM -----------------------------------------------------------
echo.
echo [2/3] Setting up GFPGAN...
if exist "%ML_DIR%\GFPGAN\" (
    echo GFPGAN already cloned. Skipping.
) else (
    git clone https://github.com/TencentARC/GFPGAN.git "%ML_DIR%\GFPGAN"
    if errorlevel 1 (
        echo ERROR: Failed to clone GFPGAN. Check your internet connection.
        pause
        exit /b 1
    )
)

REM Download GFPGAN v1.3 model weights
echo Downloading GFPGAN model weights...
cd /d "%ML_DIR%\GFPGAN"
if exist "experiments\pretrained_models\GFPGANv1.3.pth" (
    echo GFPGAN weights already exist. Skipping.
) else (
    mkdir experiments\pretrained_models 2>nul
    curl -L "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth" -o "experiments\pretrained_models\GFPGANv1.3.pth"
    echo GFPGAN weights downloaded.
)

REM Install GFPGAN dependencies
pip install basicsr facexlib realesrgan >nul 2>&1
cd /d "%ML_DIR%\GFPGAN"
pip install -r requirements.txt >nul 2>&1
python setup.py develop >nul 2>&1

REM -----------------------------------------------------------
REM 3. Ollama (Llama-3 Translation)
REM -----------------------------------------------------------
echo.
echo [3/3] Ollama / Llama-3 Translation Setup
echo   Ollama must be installed separately from: https://ollama.com/download
echo   After installing Ollama, run:
echo     ollama pull llama3
echo   Then set in backend/.env:
echo     VIDIOLINGUA_TRANSLATION_ENGINE=llama3

REM -----------------------------------------------------------
REM Update backend/.env with new paths
REM -----------------------------------------------------------
echo.
echo [Setup] Adding new env vars to backend/.env.example...
(
echo.
echo # === Phase 1 Model Upgrade Config ===
echo.
echo # SadTalker path (set after running scripts/setup_models.bat)
echo VIDIOLINGUA_SADTALKER_DIR=%ML_DIR%\SadTalker
echo.
echo # GFPGAN path
echo VIDIOLINGUA_GFPGAN_DIR=%ML_DIR%\GFPGAN
echo.
echo # BGM Separation: set to true to enable UVR5/Demucs
echo VIDIOLINGUA_USE_UVR5=false
echo.
echo # Translation engine: llama3 or google (default: google)
echo VIDIOLINGUA_TRANSLATION_ENGINE=google
echo.
echo # Ollama settings (for llama3 engine)
echo OLLAMA_BASE_URL=http://localhost:11434
echo OLLAMA_MODEL=llama3
echo.
echo # ASR model (tiny/base/small/medium/large-v2/large-v3)
echo VIDIOLINGUA_WHISPER_MODEL=base
echo.
echo # HuggingFace token for PyAnnote speaker diarization
echo HUGGINGFACE_TOKEN=
echo.
echo # TTS engine: xtts or hume or legacy
echo VIDIOLINGUA_TTS_ENGINE=xtts
) >> "%ROOT%\backend\.env"

echo.
echo ==========================================
echo [Setup] DONE!
echo.
echo Next steps:
echo   1. Set VIDIOLINGUA_SADTALKER_DIR and VIDIOLINGUA_GFPGAN_DIR in backend\.env
echo   2. Install Python deps: pip install -r requirements.txt
echo   3. (Optional) Install Ollama + pull llama3 for duration-aware translation
echo   4. (Optional) Set HUGGINGFACE_TOKEN for speaker diarization
echo   5. Run the backend: cd backend ^&^& uvicorn main:app --reload
echo ==========================================
pause
