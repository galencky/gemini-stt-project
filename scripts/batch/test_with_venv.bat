@echo off
REM Activate virtual environment and test APIs

if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python test_apis.py
pause