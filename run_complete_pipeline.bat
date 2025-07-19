@echo off
REM Complete Gemini STT Pipeline - Process videos, transcribe, and organize for upload

echo ========================================
echo    Gemini STT Complete Pipeline
echo ========================================
echo.

REM Check virtual environment
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo 🚀 Starting complete pipeline...
echo.

REM Run main pipeline with resume
python main.py --resume

REM Check if pipeline completed successfully
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Pipeline failed with error code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo 📦 Organizing files for manual upload...
echo.

REM Run organize script
python scripts\utilities\organize_for_upload.py

REM Check if organize completed successfully
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ File organization failed with error code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================
echo ✅ Complete pipeline finished!
echo.
echo 📁 Check output_for_upload folder for files to upload manually
echo 📋 See UPLOAD_INSTRUCTIONS.txt for next steps
echo ========================================
echo.

pause