#!/bin/bash
# AxonClone environment initialization script
# Sets up Python venv, installs dependencies, initializes databases

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== AxonClone Init ==="

# Create data directories
echo "[1/4] Creating data directories..."
mkdir -p data/sqlite data/lancedb data/cache data/logs data/exports

# Install Python dependencies
echo "[2/4] Installing Python dependencies..."
uv pip install -e . 2>/dev/null || pip install -e .

# Install frontend dependencies
echo "[3/4] Installing frontend dependencies..."
npm install --legacy-peer-deps

# Initialize databases
echo "[4/4] Initializing databases..."
uv run python ./_axon/scripts/init_db.py 2>/dev/null || python ./_axon/scripts/init_db.py 2>/dev/null || echo "DB init skipped (databases will be created on first run)"

echo ""
echo "=== Init complete ==="
echo "  Run '././_axon/scripts/dev.sh' to start development servers"
echo "  Run 'npm run tauri dev' for Tauri desktop app"
