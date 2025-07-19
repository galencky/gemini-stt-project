@echo off
REM Activate virtual environment and check pipeline status

if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python main_v2.py --status
pause