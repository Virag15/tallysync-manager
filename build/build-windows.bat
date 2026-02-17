@echo off
:: TallySync Manager — Windows Distribution Build Script
:: Run on a Windows machine with Python + pip installed
:: Produces: dist\TallySync-v1.0.0-Windows.zip
::
:: Usage:  cd project-root  &&  build\build-windows.bat

title TallySync Build

set "ROOT_DIR=%~dp0.."
set "SERVER_DIR=%ROOT_DIR%\server"
set "DIST_DIR=%ROOT_DIR%\dist"
set "VERSION=1.0.0"

echo.
echo   TallySync Manager - Windows Build
echo   Version: %VERSION%
echo.

:: ── Ensure venv ───────────────────────────────────────────────────────────
cd /d "%SERVER_DIR%"
if not exist ".venv\Scripts\activate.bat" (
    echo   Creating virtual environment...
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    pip install -r requirements.txt --quiet
    pip install pyinstaller --quiet
) else (
    call ".venv\Scripts\activate.bat"
    pip install pyinstaller --quiet >nul 2>&1
)

:: ── Step 1: Build binary ───────────────────────────────────────────────────
echo   [1/3] Compiling server binary...
pyinstaller --onefile --name tallysync-server --distpath "%DIST_DIR%\bin" --workpath "%TEMP%\tallysync-build" --noconfirm main.py >nul 2>&1
echo   Binary built: dist\bin\tallysync-server.exe

:: ── Step 2: Assemble distribution ─────────────────────────────────────────
echo   [2/3] Assembling distribution package...
set "PKG=%DIST_DIR%\TallySync-v%VERSION%-Windows"
if exist "%PKG%" rd /s /q "%PKG%"
mkdir "%PKG%\server-bin\data"

copy "%DIST_DIR%\bin\tallysync-server.exe" "%PKG%\server-bin\" >nul
xcopy /e /i /q "%ROOT_DIR%\pages" "%PKG%\pages\" >nul
xcopy /e /i /q "%ROOT_DIR%\assets" "%PKG%\assets\" >nul

:: Setup scripts (Windows)
mkdir "%PKG%\setup"
copy "%ROOT_DIR%\setup\start.bat"                    "%PKG%\setup\" >nul 2>&1
copy "%ROOT_DIR%\setup\install-autostart-windows.bat" "%PKG%\setup\" >nul 2>&1

:: Update start.bat to call the binary instead of python main.py
:: (The distributed start.bat already points to .venv path — customers use the binary)
echo @echo off>                                          "%PKG%\setup\start.bat"
echo title TallySync Manager>>                           "%PKG%\setup\start.bat"
echo set "ROOT=%~dp0..">>                                "%PKG%\setup\start.bat"
echo set "LOG=%ROOT%\server-bin\data\logs">>             "%PKG%\setup\start.bat"
echo if not exist "%%LOG%%" mkdir "%%LOG%%">>            "%PKG%\setup\start.bat"
echo start /b "" "%%ROOT%%\server-bin\tallysync-server.exe" ^> "%%LOG%%\tallysync.log" 2^>^&1>> "%PKG%\setup\start.bat"
echo start /b "" python -m http.server 3000 --directory "%%ROOT%%" ^> "%%LOG%%\frontend.log" 2^>^&1>> "%PKG%\setup\start.bat"
echo timeout /t 3 /nobreak ^>nul>>                      "%PKG%\setup\start.bat"
echo start "" "http://localhost:3000">>                  "%PKG%\setup\start.bat"
echo pause>>                                             "%PKG%\setup\start.bat"

(
echo TallySync Manager - Windows Quick Start
echo =========================================
echo.
echo 1. Double-click: setup\start.bat
echo    This starts the server and opens your browser automatically.
echo.
echo 2. To start automatically at Windows login:
echo    Run: setup\install-autostart-windows.bat
echo.
echo Requirements: Windows 10+ ^(no Python required^)
) > "%PKG%\README.txt"

:: ── Step 3: Zip ────────────────────────────────────────────────────────────
echo   [3/3] Creating zip archive...
cd /d "%DIST_DIR%"
powershell -command "Compress-Archive -Path 'TallySync-v%VERSION%-Windows' -DestinationPath 'TallySync-v%VERSION%-Windows.zip' -Force"
echo   Done! dist\TallySync-v%VERSION%-Windows.zip
echo.
