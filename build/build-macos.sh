#!/bin/bash
# TallySync Manager — macOS Distribution Build Script
# Produces: dist/TallySync-v{VERSION}-macOS.zip
# Run from the project root:  ./build/build-macos.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
SERVER_DIR="$ROOT_DIR/server"
DIST_DIR="$ROOT_DIR/dist"
VERSION=$(python3 -c "import sys; sys.path.insert(0,'$SERVER_DIR'); from config import APP_VERSION; print(APP_VERSION)" 2>/dev/null || echo "1.0.0")

echo ""
echo "  TallySync Manager — macOS Build"
echo "  Version: $VERSION"
echo ""

# ── Step 1: Build PyInstaller binary ─────────────────────────────────────────
echo "  [1/3] Compiling server binary..."
cd "$SERVER_DIR"
.venv/bin/pyinstaller \
  --onefile \
  --name tallysync-server \
  --distpath "$DIST_DIR/bin" \
  --workpath /tmp/tallysync-build \
  --noconfirm \
  main.py >/dev/null 2>&1
echo "  Binary built: dist/bin/tallysync-server"

# ── Step 2: Assemble distribution folder ─────────────────────────────────────
echo "  [2/3] Assembling distribution package..."
PACKAGE_DIR="$DIST_DIR/TallySync-v${VERSION}-macOS"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/server-bin"
mkdir -p "$PACKAGE_DIR/server-bin/data"

# Binary
cp "$DIST_DIR/bin/tallysync-server" "$PACKAGE_DIR/server-bin/"
chmod +x "$PACKAGE_DIR/server-bin/tallysync-server"

# Frontend
cp -r "$ROOT_DIR/pages" "$PACKAGE_DIR/"
cp -r "$ROOT_DIR/assets" "$PACKAGE_DIR/"

# macOS launcher app
if [ -d "$ROOT_DIR/TallySync.app" ]; then
  cp -r "$ROOT_DIR/TallySync.app" "$PACKAGE_DIR/"
fi

# Setup scripts (macOS only)
mkdir -p "$PACKAGE_DIR/setup"
cp "$ROOT_DIR/setup/start.sh"                       "$PACKAGE_DIR/setup/" 2>/dev/null || true
cp "$ROOT_DIR/setup/install-autostart-macos.sh"     "$PACKAGE_DIR/setup/" 2>/dev/null || true
cp "$ROOT_DIR/setup/com.tallysync.manager.plist"    "$PACKAGE_DIR/setup/" 2>/dev/null || true

# Update start.sh to use the binary instead of python main.py
sed -i '' 's|.venv/bin/python main.py|./tallysync-server|g' \
  "$PACKAGE_DIR/setup/start.sh" 2>/dev/null || true

# README
cat > "$PACKAGE_DIR/README.txt" <<'EOF'
TallySync Manager — macOS Quick Start
======================================

Option A — Double-click launcher (easiest):
  1. Open TallySync.app

Option B — Terminal:
  1. cd into this folder
  2. ./setup/start.sh

Option C — Auto-start at login:
  1. ./setup/install-autostart-macos.sh

Requirements: macOS 12+ (Monterey or later)
EOF

# ── Step 3: Zip it up ────────────────────────────────────────────────────────
echo "  [3/3] Creating zip archive..."
cd "$DIST_DIR"
ZIP_NAME="TallySync-v${VERSION}-macOS.zip"
rm -f "$ZIP_NAME"
zip -r "$ZIP_NAME" "TallySync-v${VERSION}-macOS" -x "*.DS_Store" >/dev/null
echo "  Done! → dist/$ZIP_NAME  ($(du -sh "$ZIP_NAME" | cut -f1))"
echo ""
