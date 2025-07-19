@echo off
REM Diagnostic script for Gemini STT

echo ========================================
echo Gemini STT Diagnostics
echo ========================================
echo.

REM Check Python
echo Checking Python...
python --version 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python not found in PATH
    pause
    exit /b 1
) else (
    echo ✓ Python found
)
echo.

REM Check virtual environment
echo Checking virtual environment...
if exist venv\Scripts\activate.bat (
    echo ✓ Virtual environment exists
    call venv\Scripts\activate.bat
) else (
    echo ❌ Virtual environment not found
    echo   Run setup_windows.bat first
)
echo.

REM Navigate to project root first
cd /d "%~dp0\.."

REM Check compatibility
echo Running compatibility check...
python tools\check_compatibility.py
echo.

REM Test imports
echo Testing imports...
python tools\test_imports.py
echo.

REM Check .env file
echo Checking configuration...
if exist .env (
    echo ✓ .env file found
    python -c "from src.core import Config; c=Config(); v,e=c.validate(); print('✓ Configuration valid' if v else f'❌ Configuration errors: {e}')"
) else (
    echo ❌ .env file not found
    echo   Copy .env.example to .env and add your API keys
)
echo.

REM Check working directories
echo Checking directories...
if exist working (
    echo ✓ Working directory exists
) else (
    echo ⚠ Working directory missing (will be created on first run)
)

if exist logs (
    echo ✓ Logs directory exists
) else (
    echo ⚠ Logs directory missing (will be created on first run)
)
echo.

REM Test folder organization
echo Testing folder organization...
python -c "from src.core import Config; c=Config(); print(f'✓ Folder organization: {'ENABLED' if c.organize_to_folders else 'DISABLED'}')"
echo.

echo ========================================
echo Diagnostics complete
echo ========================================
pause