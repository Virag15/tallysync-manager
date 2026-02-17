@echo off
:: TallySync Manager — Windows Startup Script
:: Double-click this file to start the TallySync backend server.

title TallySync Manager Server

:: Move to the server folder (one level up from setup\)
cd /d "%~dp0..\server"

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo.
    echo  ERROR: Virtual environment not found at server\.venv\
    echo  Please run:  python -m venv .venv  ^&^&  .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo  TallySync Manager starting on http://localhost:8001
echo  Press Ctrl+C to stop.
echo.

python main.py

if errorlevel 1 (
    echo.
    echo  Server stopped with an error. Check the log above.
    pause
)
