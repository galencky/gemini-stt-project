@echo off
REM Gemini STT Setup Script for Windows
echo ========================================
echo Gemini STT Setup for Windows
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found:
python --version

REM Check Python version for compatibility
python -c "import sys; exit(0 if sys.version_info < (3, 13) else 1)" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Python 3.13+ detected
    echo Audio processing may have limited functionality due to audioop removal
    echo Consider using Python 3.12 or earlier for full compatibility
    echo.
)
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo Virtual environment created
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
echo.

REM Create necessary directories
echo Creating working directories...
if not exist "working" mkdir working
if not exist "working\from_google_drive" mkdir working\from_google_drive
if not exist "working\transcription" mkdir working\transcription
if not exist "working\parsed" mkdir working\parsed
if not exist "working\markdown" mkdir working\markdown
if not exist "working\uploaded" mkdir working\uploaded
if not exist "logs" mkdir logs
echo.

REM Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Copying .env.example to .env...
    if exist ".env.example" (
        copy .env.example .env
        echo Please edit .env with your API keys and configuration
    ) else (
        echo ERROR: .env.example not found
    )
) else (
    echo .env file found
)
echo.

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: FFmpeg not found!
    echo FFmpeg is required for video processing
    echo Download from: https://ffmpeg.org/download.html
    echo.
)

echo ========================================
echo Setup complete!
echo.
echo To use Gemini STT:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Edit .env file with your API keys
echo 3. Run: python main.py
echo ========================================
pause