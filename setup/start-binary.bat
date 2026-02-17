@echo off
:: TallySync Manager — Binary Distribution Startup Script
:: No Python required. Double-click to start.
title TallySync Manager
set "ROOT=%~dp0.."
set "LOG=%ROOT%\server-bin\data\logs"
if not exist "%LOG%" mkdir "%LOG%"
echo  Starting TallySync Manager...
start /b "" "%ROOT%\server-bin\tallysync-server.exe" > "%LOG%\tallysync.log" 2>&1
echo  Waiting for server...
timeout /t 4 /nobreak >nul
start "" "http://localhost:8001/pages/dashboard.html"
echo.
echo  TallySync Manager is running at http://localhost:8001
echo  Close this window to stop the server.
echo.
pause
