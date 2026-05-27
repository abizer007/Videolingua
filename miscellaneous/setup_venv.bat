@echo off
title Vidiolingua - Setup virtual environment
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

if exist ".venv\Scripts\python.exe" (
    echo Virtual environment already exists at .venv
    echo Installing/updating dependencies...
    .venv\Scripts\pip.exe install -r requirements.txt -q
    echo.
    echo Done. Run start.bat to launch the app.
    pause
    exit /b 0
)

echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo Failed to create venv. Make sure Python is installed and on PATH.
    pause
    exit /b 1
)

echo Installing dependencies (this may take a few minutes)...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo Pip install had issues. Check the output above.
    pause
    exit /b 1
)

echo.
echo Setup complete. Run start.bat to launch the app.
pause
