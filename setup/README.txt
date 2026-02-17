======================================================
  TallySync Manager — Setup Guide
======================================================

WINDOWS (Binary — no Python required)
--------------------------------------
1. Double-click:  setup\start.bat
   The server starts and your browser opens automatically.

2. To start automatically at Windows login (run once):
   Double-click:  setup\install-autostart-windows.bat
   (Run as Administrator if prompted)

   To remove auto-start:
   schtasks /Delete /TN "TallySync Manager" /F


MACOS (Binary — no Python required)
-------------------------------------
1. Open the TallySync.app launcher  — OR —
   In Terminal:
     chmod +x setup/start.sh
     ./setup/start.sh

2. To start automatically at login (run once):
   ./setup/install-autostart-macos.sh

   To remove:
   launchctl unload ~/Library/LaunchAgents/com.tallysync.manager.plist


OPENING THE APP
---------------
After starting, go to:  http://localhost:8001/pages/dashboard.html

This URL opens automatically when you use start.bat / start.sh.
The same server serves both the API (port 8001) and the dashboard.

On first open → go to Settings:
  1. The API Key is loaded automatically.
  2. If asked for a Backend URL, enter:  http://localhost:8001


DEVELOPER / SOURCE INSTALL
---------------------------
Requires Python 3.10+

  Windows (Command Prompt in "server" folder):
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
    python main.py

  macOS / Linux (Terminal in "server" folder):
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    python3 main.py

  The setup\start.bat and setup/start.sh scripts auto-detect
  whether a binary or Python venv is present.


CHANGING THE PORT
-----------------
Create a file called  server/.env  and add:
  PORT=8002

The server will use port 8002 on next start.
Update the URL in your browser accordingly.


SUPPORT
-------
  GitHub:  https://github.com/Virag15/tallysync-manager
======================================================
