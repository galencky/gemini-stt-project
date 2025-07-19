@echo off
echo ==========================================
echo Gemini STT Pipeline - Windows Setup Script
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo [1/7] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping creation...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo.
echo [2/7] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo [3/7] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [4/7] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo [5/7] Checking .env file...
if exist .env (
    echo .env file found - assuming it's already configured
) else (
    echo ERROR: .env file not found!
    echo Please create .env file with your API keys
    if exist .env.example (
        echo You can copy .env.example to .env as a starting point
    )
    pause
    exit /b 1
)

echo.
echo [6/7] Creating necessary directories...
if not exist data mkdir data
if not exist data\inbox mkdir data\inbox
if not exist data\transcripts mkdir data\transcripts
if not exist data\parsed mkdir data\parsed
if not exist data\markdown mkdir data\markdown
if not exist data\uploaded mkdir data\uploaded
if not exist logs mkdir logs

echo.
echo [7/7] Testing imports...
python -c "import sys; sys.path.insert(0, '.'); from src.utils import config; print('✅ Config module loaded')"
if errorlevel 1 (
    echo ERROR: Failed to import config module
    pause
    exit /b 1
)

python -c "import google.generativeai; print('✅ Gemini SDK loaded')"
if errorlevel 1 (
    echo ERROR: Failed to import Gemini SDK
    pause
    exit /b 1
)

REM Check Python version for pydub compatibility
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Try to import pydub, but don't fail on Python 3.13
python -c "from pydub import AudioSegment; print('✅ Pydub loaded')" 2>nul
if errorlevel 1 (
    echo.
    echo ⚠️  WARNING: Pydub import failed (this is expected on Python 3.13)
    echo.
    echo The pipeline will still work as long as FFmpeg is installed.
    echo Make sure FFmpeg is installed and in PATH
    echo Download from: https://ffmpeg.org/download.html
    echo.
    REM Don't exit, just warn
)

echo.
echo ==========================================
echo ✅ Setup completed successfully!
echo ==========================================
echo.
echo Virtual environment is activated. You can now:
echo.
echo 1. Test API connections:
echo    python test_apis.py
echo.
echo 2. Check pipeline status:
echo    python main_v2.py --status
echo.
echo 3. Run the smart pipeline:
echo    python main_v2.py --resume
echo.
echo 4. Run without resume (process everything):
echo    python main_v2.py
echo.
echo To deactivate the virtual environment later, type: deactivate
echo.
pause