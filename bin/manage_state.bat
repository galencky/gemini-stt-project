@echo off
REM State management script for Gemini STT

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

echo ========================================
echo Gemini STT State Management
echo ========================================
echo.
echo Options:
echo 1. Show current pipeline state
echo 2. Clear pipeline state (start fresh)
echo 3. Run pipeline (resume from last state)
echo 4. Run pipeline (ignore previous state)
echo 5. Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Current Pipeline State:
    echo ========================================
    python main.py --show-state
    echo ========================================
    pause
    goto :eof
)

if "%choice%"=="2" (
    echo.
    echo Clearing pipeline state...
    python main.py --clear-state
    echo.
    pause
    goto :eof
)

if "%choice%"=="3" (
    echo.
    echo Running pipeline with resume...
    python main.py
    pause
    goto :eof
)

if "%choice%"=="4" (
    echo.
    echo Running pipeline without resume...
    python main.py --no-resume
    pause
    goto :eof
)

if "%choice%"=="5" (
    exit /b 0
)

echo Invalid choice!
pause