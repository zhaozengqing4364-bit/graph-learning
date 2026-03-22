#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
LOOP_DIR="$ROOT_DIR/loop"
RUNS_DIR="$LOOP_DIR/runs"
LOCK_DIR="$LOOP_DIR/.runner-lock"
PROMPT_FILE="$LOOP_DIR/run-once-prompt.md"
SCHEMA_FILE="$LOOP_DIR/output-schema.json"

usage() {
  cat <<'EOF'
Usage: ./_axon/scripts/codex-loop.sh [--dry-run]

Runs one Codex safe-grow iteration in non-interactive mode.
EOF
}

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ $# -gt 0 ]]; then
  usage >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found in PATH" >&2
  exit 127
fi

for required in \
  "$ROOT_DIR/AGENTS.md" \
  "$LOOP_DIR/PROJECT_GROWTH.md" \
  "$LOOP_DIR/GLM_AUDIT.md" \
  "$LOOP_DIR/GROWTH_BACKLOG.md" \
  "$LOOP_DIR/state.json" \
  "$LOOP_DIR/log.md" \
  "$PROMPT_FILE" \
  "$SCHEMA_FILE"; do
  if [[ ! -f "$required" ]]; then
    echo "Missing required file: $required" >&2
    exit 1
  fi
done

mkdir -p "$RUNS_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "safe-grow runner is already active; exiting without starting a second turn." >&2
  exit 0
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
RUN_DIR="$RUNS_DIR/$TIMESTAMP"
mkdir -p "$RUN_DIR"

PROMPT_CONTENT="$(<"$PROMPT_FILE")"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] repo: $ROOT_DIR"
  echo "[dry-run] run dir: $RUN_DIR"
  echo "[dry-run] codex exec --skip-git-repo-check --full-auto --sandbox workspace-write --json --output-schema \"$SCHEMA_FILE\" --output-last-message \"$RUN_DIR/final.json\" \"<prompt>\""
  exit 0
fi

set +e
codex exec \
  --skip-git-repo-check \
  --full-auto \
  --sandbox workspace-write \
  --json \
  --output-schema "$SCHEMA_FILE" \
  --output-last-message "$RUN_DIR/final.json" \
  "$PROMPT_CONTENT" \
  >"$RUN_DIR/events.jsonl" \
  2>"$RUN_DIR/stderr.log"
STATUS=$?
set -e

printf '%s\n' "$STATUS" >"$RUN_DIR/exit_code.txt"

if [[ -f "$RUN_DIR/final.json" ]]; then
  cp "$RUN_DIR/final.json" "$LOOP_DIR/last-result.json"
  cat "$RUN_DIR/final.json"
else
  echo "{\"mode\":\"unknown\",\"selected_item_id\":null,\"selected_item_status\":\"failed\",\"user_benefit\":\"No final summary was produced.\",\"system_benefit\":\"Inspect .codex/loop/runs for details.\",\"verification_summary\":\"Runner finished without a structured final message.\",\"next_action\":\"Open the latest run directory and inspect stderr.log and events.jsonl.\"}"
fi

exit "$STATUS"
