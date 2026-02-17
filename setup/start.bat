@echo off
:: TallySync Manager — Windows Startup Script
:: Double-click this file to start both servers and open the dashboard.

title TallySync Manager

:: Resolve paths relative to this script's location
set "SETUP_DIR=%~dp0"
set "ROOT_DIR=%SETUP_DIR%.."
set "SERVER_DIR=%ROOT_DIR%\server"

:: ── Activate virtual environment ──────────────────────────────────────────
cd /d "%SERVER_DIR%"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo.
    echo  ERROR: Virtual environment not found at server\.venv\
    echo  Please run:
    echo    python -m venv .venv
    echo    .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: ── Start backend in background ───────────────────────────────────────────
echo  Starting TallySync backend on http://localhost:8001 ...
start /b "" python main.py > "..\server\data\logs\tallysync.log" 2>&1

:: ── Start frontend static server in background ────────────────────────────
echo  Starting frontend on http://localhost:3000 ...
start /b "" python -m http.server 3000 --directory "%ROOT_DIR%" > "..\server\data\logs\frontend.log" 2>&1

:: ── Wait for backend to be ready (poll up to 10 seconds) ─────────────────
echo  Waiting for server to be ready...
set /a TRIES=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -sf http://localhost:8001/api/health >nul 2>&1
if %errorlevel% == 0 goto READY
set /a TRIES+=1
if %TRIES% lss 10 goto WAIT_LOOP

:READY
:: ── Open browser ─────────────────────────────────────────────────────────
echo  Opening TallySync Manager in your browser...
start "" "http://localhost:3000"

echo.
echo  TallySync Manager is running.
echo  Close this window to stop the servers.
echo.

:: Keep window open so servers stay alive
pause
