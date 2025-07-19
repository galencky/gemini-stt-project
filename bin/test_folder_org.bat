@echo off
REM Test folder organization functionality

echo ========================================
echo Testing Folder Organization
echo ========================================
echo.

REM Navigate to project root
cd /d "%~dp0\.."

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
    echo.
)

REM Run the test
python tools\test_folder_organizer.py

pause