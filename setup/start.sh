#!/bin/bash
# TallySync Manager — macOS / Linux Startup Script
# Run:  chmod +x setup/start.sh && ./setup/start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
BIN="$ROOT_DIR/server-bin/tallysync-server"

# ── Prefer pre-built binary (customer install, no Python needed) ──────────────
if [ -x "$BIN" ]; then
    LOG_DIR="$ROOT_DIR/server-bin/data/logs"
    mkdir -p "$LOG_DIR"
    echo ""
    echo "  Starting TallySync Manager..."
    "$BIN" > "$LOG_DIR/tallysync.log" 2>&1 &
    SERVER_PID=$!

    # Wait for server ready
    for i in $(seq 1 15); do
        sleep 1
        curl -sf http://localhost:8001/api/health >/dev/null 2>&1 && break
    done

    # Open browser
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:8001/pages/dashboard.html"
    fi

    echo "  TallySync Manager is running at http://localhost:8001"
    echo "  Press Ctrl+C to stop."
    echo ""
    wait $SERVER_PID
    exit 0
fi

# ── Fallback: Python venv (developer / source install) ───────────────────────
SERVER_DIR="$ROOT_DIR/server"
cd "$SERVER_DIR"

if [ ! -d ".venv" ]; then
    echo ""
    echo "  First run — setting up Python environment (1-2 minutes)..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt --quiet
    echo "  Setup complete!"
    echo ""
fi

source ".venv/bin/activate"

echo ""
echo "  TallySync Manager starting on http://localhost:8001"
echo "  Press Ctrl+C to stop."
echo ""

# Open browser in background after a short delay
(sleep 3 && open "http://localhost:8001/pages/dashboard.html" 2>/dev/null || true) &

python main.py
