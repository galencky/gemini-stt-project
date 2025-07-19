@echo off
REM Open the local organized folders directory

echo Opening organized folders directory...

REM Navigate to project root
cd /d "%~dp0\.."

REM Check if the directory exists
if exist "working\organized_for_upload" (
    explorer "working\organized_for_upload"
    echo.
    echo These folders contain processed files organized for manual upload.
    echo You can drag and drop these folders to Google Drive or any cloud storage.
) else (
    echo No organized folders found yet.
    echo Run the main pipeline or organize.cmd first.
)

pause