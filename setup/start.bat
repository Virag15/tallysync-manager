@echo off
:: TallySync Manager — Windows Startup Script
:: Double-click this file to start both servers and open the dashboard.
:: On first run it will automatically create the Python virtual environment.

title TallySync Manager

:: Resolve paths relative to this script's location
set "SETUP_DIR=%~dp0"
set "ROOT_DIR=%SETUP_DIR%.."
set "SERVER_DIR=%ROOT_DIR%\server"
set "VENV_DIR=%SERVER_DIR%\.venv"
set "LOG_DIR=%SERVER_DIR%\data\logs"

:: ── Ensure log directory exists ────────────────────────────────────────────
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: ── Check Python ───────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python not found. Please install Python 3.10+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: ── Create virtual environment on first run ────────────────────────────────
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo  First run detected — setting up Python environment...
    echo  This will take about 1-2 minutes.
    echo.
    cd /d "%SERVER_DIR%"
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  ERROR: Could not create virtual environment.
        pause & exit /b 1
    )
    echo  Installing dependencies...
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to install dependencies. Check requirements.txt.
        pause & exit /b 1
    )
    echo  Setup complete!
    echo.
) else (
    cd /d "%SERVER_DIR%"
    call "%VENV_DIR%\Scripts\activate.bat"
)

:: ── Start backend in background ────────────────────────────────────────────
echo  Starting TallySync backend on http://localhost:8001 ...
start /b "" python main.py > "%LOG_DIR%\tallysync.log" 2>&1

:: ── Start frontend static server in background ─────────────────────────────
echo  Starting frontend on http://localhost:3000 ...
start /b "" python -m http.server 3000 --directory "%ROOT_DIR%" > "%LOG_DIR%\frontend.log" 2>&1

:: ── Wait for backend to be ready (poll up to 12 seconds) ──────────────────
echo  Waiting for server to be ready...
set /a TRIES=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -sf http://localhost:8001/api/health >nul 2>&1
if %errorlevel% == 0 goto READY
set /a TRIES+=1
if %TRIES% lss 12 goto WAIT_LOOP

:READY
:: ── Open browser ──────────────────────────────────────────────────────────
echo  Opening TallySync Manager in your browser...
start "" "http://localhost:3000"

echo.
echo  TallySync Manager is running!
echo  Dashboard: http://localhost:3000
echo  API:       http://localhost:8001
echo  Logs:      %LOG_DIR%
echo.
echo  Close this window to stop the servers.
echo.

:: Keep window open so servers stay alive
pause
