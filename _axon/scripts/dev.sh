#!/bin/bash
# AxonClone development startup script
# Starts both backend and frontend in parallel

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== AxonClone Dev Server ==="

# Ensure data directories exist
mkdir -p "$ROOT_DIR/data/sqlite" "$ROOT_DIR/data/lancedb" "$ROOT_DIR/data/cache" "$ROOT_DIR/data/logs" "$ROOT_DIR/data/exports"

# Ensure Java 21 for Neo4j
export JAVA_HOME=/opt/homebrew/opt/openjdk@21 2>/dev/null || true

# Check Python dependencies
echo "[1/3] Checking Python dependencies..."
cd "$ROOT_DIR"
uv pip install -e . --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null

# Start Neo4j if not already running
echo "[2/3] Checking Neo4j..."
export NEO4J_HOME=/opt/homebrew/Cellar/neo4j/2025.04.0/libexec
if [ -x "$NEO4J_HOME/bin/neo4j" ]; then
    if ! "$NEO4J_HOME/bin/neo4j" status 2>/dev/null | grep -q "running"; then
        "$NEO4J_HOME/bin/neo4j" console &
        NEO4J_PID=$!
        echo "Neo4j starting (PID: $NEO4J_PID)..."
        sleep 5
    else
        echo "Neo4j already running."
    fi
else
    echo "Neo4j not found, skipping."
fi

# Start backend in background
echo "[3/3] Starting servers..."
cd "$ROOT_DIR"
uv run --directory "$ROOT_DIR" uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload --app-dir "$ROOT_DIR" &
BACKEND_PID=$!
echo "Backend started on http://127.0.0.1:8000 (PID: $BACKEND_PID)"

# Start frontend
cd "$ROOT_DIR"
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "=== Servers running ==="
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

wait
