#!/bin/bash
# TallySync Manager — macOS / Linux Startup Script
# Run:  chmod +x setup/start.sh && ./setup/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../server"

cd "$SERVER_DIR"

if [ ! -d ".venv" ]; then
  echo "ERROR: Virtual environment not found at server/.venv/"
  echo "Please run:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

source ".venv/bin/activate"

echo ""
echo "  TallySync Manager starting on http://localhost:8001"
echo "  Press Ctrl+C to stop."
echo ""

python main.py
