@echo off
:: TallySync Manager — Windows Startup Script
:: Double-click this file to start the server and open the dashboard.
:: The server runs on http://localhost:8001 and also serves the frontend.

title TallySync Manager

:: Resolve paths relative to this script's location
set "SETUP_DIR=%~dp0"
set "ROOT_DIR=%SETUP_DIR%.."
set "SERVER_DIR=%ROOT_DIR%\server"
set "BIN_DIR=%ROOT_DIR%\server-bin"
set "LOG_DIR=%ROOT_DIR%\server-bin\data\logs"

:: ── Prefer pre-built binary (customer install, no Python needed) ────────────
if exist "%BIN_DIR%\tallysync-server.exe" (
    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
    echo  Starting TallySync Manager...
    start /b "" "%BIN_DIR%\tallysync-server.exe" > "%LOG_DIR%\tallysync.log" 2>&1
    goto WAIT
)

:: ── Fallback: Python venv (developer / source install) ─────────────────────
set "VENV_DIR=%SERVER_DIR%\.venv"
set "LOG_DIR=%SERVER_DIR%\data\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: tallysync-server.exe not found and Python is not installed.
    echo  Please download the Windows binary release from:
    echo  https://github.com/Virag15/tallysync-manager/releases
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo  First run — setting up Python environment (1-2 minutes)...
    echo.
    cd /d "%SERVER_DIR%"
    python -m venv .venv
    if %errorlevel% neq 0 ( echo  ERROR: Could not create venv. & pause & exit /b 1 )
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 ( echo  ERROR: pip install failed. & pause & exit /b 1 )
    echo  Setup complete!
    echo.
) else (
    cd /d "%SERVER_DIR%"
    call "%VENV_DIR%\Scripts\activate.bat"
)

echo  Starting TallySync backend on http://localhost:8001 ...
start /b "" python main.py > "%LOG_DIR%\tallysync.log" 2>&1

:WAIT
:: ── Wait for server to be ready (poll up to 15 seconds) ────────────────────
echo  Waiting for server...
set /a TRIES=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -sf http://localhost:8001/api/health >nul 2>&1
if %errorlevel% == 0 goto READY
set /a TRIES+=1
if %TRIES% lss 15 goto WAIT_LOOP

:READY
:: ── Open dashboard in browser ───────────────────────────────────────────────
echo  Opening TallySync Manager...
start "" "http://localhost:8001/pages/dashboard.html"

echo.
echo  TallySync Manager is running at http://localhost:8001
echo  Logs: %LOG_DIR%
echo.
echo  Close this window to stop the server.
echo.

:: Keep window open so the server process stays alive
pause
