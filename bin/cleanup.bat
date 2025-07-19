@echo off
REM Clean up working directories for files that have been organized

echo ========================================
echo Working Directory Cleanup
echo ========================================
echo.
echo This will clean up files that have already been organized
echo to Google Drive or local folders.
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

REM Run cleanup in dry-run mode by default
echo Running in DRY RUN mode (no files will be deleted)
echo.
python tools\cleanup_working.py

echo.
echo To actually delete files, run:
echo   python tools\cleanup_working.py --execute
echo.
pause