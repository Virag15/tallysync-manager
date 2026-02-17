#!/bin/bash
# TallySync Manager — macOS Auto-Start Installer
# Installs a LaunchAgent so the server starts when you log in.
# Run once:  chmod +x setup/install-autostart-macos.sh && ./setup/install-autostart-macos.sh
#
# To remove:  launchctl unload ~/Library/LaunchAgents/com.tallysync.manager.plist
#             rm ~/Library/LaunchAgents/com.tallysync.manager.plist

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../server"
VENV_PYTHON="$SERVER_DIR/.venv/bin/python"
MAIN_PY="$SERVER_DIR/main.py"
LOG_DIR="$SERVER_DIR/data/logs"
PLIST_SRC="$SCRIPT_DIR/com.tallysync.manager.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.tallysync.manager.plist"

echo ""
echo "  TallySync Manager — macOS Auto-Start Installer"
echo ""

# Verify venv exists
if [ ! -f "$VENV_PYTHON" ]; then
  echo "  ERROR: Virtual environment not found at $VENV_PYTHON"
  echo "  Please run:  cd server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

mkdir -p "$LOG_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

# Substitute placeholders in plist template
sed \
  -e "s|PLACEHOLDER_VENV_PYTHON|$VENV_PYTHON|g" \
  -e "s|PLACEHOLDER_MAIN_PY|$MAIN_PY|g" \
  -e "s|PLACEHOLDER_SERVER_DIR|$SERVER_DIR|g" \
  -e "s|PLACEHOLDER_LOG_DIR|$LOG_DIR|g" \
  "$PLIST_SRC" > "$PLIST_DST"

# Unload if already loaded (ignore error)
launchctl unload "$PLIST_DST" 2>/dev/null || true

# Load
launchctl load "$PLIST_DST"

echo "  SUCCESS! TallySync Manager will now start automatically at login."
echo ""
echo "  Plist installed at: $PLIST_DST"
echo "  Logs:               $LOG_DIR/tallysync.log"
echo ""
echo "  To start now:    ./setup/start.sh"
echo "  To stop:         launchctl unload ~/Library/LaunchAgents/com.tallysync.manager.plist"
echo "  To uninstall:    launchctl unload ~/Library/LaunchAgents/com.tallysync.manager.plist"
echo "                   rm ~/Library/LaunchAgents/com.tallysync.manager.plist"
echo ""
