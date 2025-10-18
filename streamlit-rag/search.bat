@echo off
REM Batch file to run console search easily on Windows
REM Usage: search.bat

cd /d "%~dp0"

REM Check if virtual environment exists
if exist "..\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ..\venv\Scripts\activate.bat
)

echo.
echo Starting Console Search...
echo.
python console_search.py

if errorlevel 1 (
    echo.
    echo Error running console_search.py
    echo Make sure Python and dependencies are installed.
    pause
)
