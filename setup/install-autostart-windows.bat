@echo off
:: TallySync Manager — Windows Auto-Start Installer
:: Registers TallySync to start automatically when you log in to Windows.
:: Run this once. To remove, run: schtasks /Delete /TN "TallySync Manager" /F

title TallySync Manager — Auto-Start Setup

set "START_BAT=%~dp0start.bat"

echo.
echo  Installing TallySync Manager auto-start...
echo  Script: %START_BAT%
echo.

schtasks /Create ^
  /SC ONLOGON ^
  /TN "TallySync Manager" ^
  /TR "cmd /c start \"TallySync\" /min \"%START_BAT%\"" ^
  /RL HIGHEST ^
  /F

if errorlevel 1 (
    echo.
    echo  ERROR: Could not register scheduled task.
    echo  Try running this file as Administrator.
    echo.
    pause
    exit /b 1
)

echo.
echo  SUCCESS! TallySync Manager will now start automatically at login.
echo  To start it now, run:  %START_BAT%
echo.
echo  To remove auto-start:  schtasks /Delete /TN "TallySync Manager" /F
echo.
pause
