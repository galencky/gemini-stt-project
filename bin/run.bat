@echo off
REM Quick run script for Gemini STT

REM Move to project root
cd /d "%~dp0\.."

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run bin\setup_windows.bat first
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create .env from .env.example and add your API keys
    pause
    exit /b 1
)

REM Run main script
echo Starting Gemini STT Pipeline...
echo ========================================
python main.py
echo ========================================
echo.
echo Pipeline finished. Check logs folder for details.
pause