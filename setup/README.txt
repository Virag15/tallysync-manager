======================================================
  TallySync Manager — Server Setup Guide
======================================================

WHAT THIS FOLDER CONTAINS
--------------------------
  start.bat                   Windows: start the server manually
  start.sh                    macOS/Linux: start the server manually
  install-autostart-windows.bat  Windows: auto-start at login (run once)
  install-autostart-macos.sh     macOS: auto-start at login (run once)


FIRST-TIME SETUP
----------------
Before starting, make sure Python dependencies are installed.

  Windows:
    Open Command Prompt in the "server" folder and run:
      python -m venv .venv
      .venv\Scripts\pip install -r requirements.txt

  macOS / Linux:
    Open Terminal in the "server" folder and run:
      python3 -m venv .venv
      .venv/bin/pip install -r requirements.txt


STARTING THE SERVER
-------------------
  Windows:  Double-click  setup\start.bat
  macOS:    Run           ./setup/start.sh

  The server runs on http://localhost:8001 by default.


AUTO-START AT LOGIN (optional)
-------------------------------
  Windows:
    Double-click  setup\install-autostart-windows.bat
    (Run as Administrator if prompted)

  macOS:
    chmod +x setup/install-autostart-macos.sh
    ./setup/install-autostart-macos.sh


OPENING THE APP
---------------
  Open your web browser and go to:
    http://localhost:5500   (if using VS Code Live Server)
    file:///path/to/Tally/pages/dashboard.html  (open directly)
    https://tallysync-manager.vercel.app        (hosted version)

  On first open, go to Settings and:
    1. Enter the Backend Server URL  (e.g.  http://localhost:8001)
    2. The API Key will be loaded automatically from the server.
    3. Click Save — the page will reload and connect.


CHANGING THE PORT
-----------------
  Create a file called  server/.env  and add:
    PORT=8002

  The server will use port 8002 on next start.


SUPPORT
-------
  GitHub:  https://github.com/Virag15/tallysync-manager
======================================================
