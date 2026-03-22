#!/bin/bash
# AxonClone production build script
# Builds frontend and prepares Tauri bundle

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== AxonClone Build ==="

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
uv pip install -e . --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null

# Build frontend
echo "[2/3] Building frontend..."
npm run build
echo "Frontend build complete: dist/"

# Build Tauri app (if cargo is available)
echo "[3/3] Building Tauri app..."
if command -v cargo &>/dev/null; then
    cd "$ROOT_DIR"
    npm run tauri build 2>/dev/null || echo "Tauri build skipped (not configured)"
else
    echo "Cargo not found, skipping Tauri build."
fi

echo ""
echo "=== Build complete ==="
