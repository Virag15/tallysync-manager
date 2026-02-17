@echo off
:: TallySync Manager — Binary Distribution Startup Script
:: No Python required. Double-click to start.
title TallySync Manager
set "ROOT=%~dp0.."
set "LOG=%ROOT%\server-bin\data\logs"
if not exist "%LOG%" mkdir "%LOG%"

echo  Starting TallySync Manager...
start /b "" "%ROOT%\server-bin\tallysync-server.exe" > "%LOG%\tallysync.log" 2>&1

:: Poll /api/health until ready (up to 30 seconds).
:: First run is slow — PyInstaller extracts ~200 MB before starting.
echo  Waiting for server to be ready...
set /a TRIES=0
:WAIT_LOOP
timeout /t 2 /nobreak >nul
curl -sf http://localhost:8001/api/health >nul 2>&1
if %errorlevel% == 0 goto READY
set /a TRIES+=1
if %TRIES% lss 15 goto WAIT_LOOP
echo  Server is taking longer than usual — opening browser anyway...

:READY
start "" "http://localhost:8001/pages/dashboard.html"
echo.
echo  TallySync Manager is running at http://localhost:8001
echo  Close this window to stop the server.
echo.
pause
