#!/bin/bash
# Sidecar launcher for AxonClone Python backend server.
# Tauri embeds this script as a sidecar binary.
# It starts the FastAPI server and waits for it to be ready.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Activate virtual environment if it exists
VENV_DIR="$PROJECT_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# Start the backend server
cd "$PROJECT_ROOT"
exec python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
