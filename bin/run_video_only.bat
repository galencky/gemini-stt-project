@echo off
REM Quick run script for video processing only

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

REM Run video processing script
echo Starting Video Processing...
echo ========================================
python scripts\process_videos_only.py
echo ========================================
echo.
echo Video processing finished.
pause