#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="cineagent"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="cli"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --ui) MODE="ui"; shift ;;
        --cli) MODE="cli"; shift ;;
        -h|--help)
            echo "Usage: ./start.sh [--cli|--ui]"
            echo ""
            echo "  --cli   Launch CLI chat with --debug (default)"
            echo "  --ui    Launch Streamlit UI on :8501"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Verify conda env exists
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "ERROR: Conda env '${ENV_NAME}' not found."
    echo "Run ./setup.sh first."
    exit 1
fi

# Verify .env exists
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo "ERROR: .env file not found."
    echo "Run ./setup.sh or copy .env.example to .env and fill in API keys."
    exit 1
fi

# Get conda base for activation in subshells
CONDA_BASE="$(conda info --base)"

open_terminal() {
    local title="$1"
    local cmd="$2"

    osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    set newTab to do script "echo '=== ${title} ===' && source '${CONDA_BASE}/etc/profile.d/conda.sh' && conda activate ${ENV_NAME} && cd '${SCRIPT_DIR}' && ${cmd}"
    set custom title of front window to "${title}"
end tell
APPLESCRIPT
}

echo "=== CineAgent — Starting Services ==="
echo ""

# Kill any existing processes on our ports
for port in 8000 8001 8501; do
    pid=$(lsof -ti ":${port}" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing existing process on port ${port} (PID: ${pid})"
        kill "$pid" 2>/dev/null || true
    fi
done

# Launch Cinema API
echo "Opening Cinema API (:8000)..."
open_terminal "CineAgent — Cinema API :8000" \
    "cd cinema_api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

sleep 2

# Launch Assistant API
echo "Opening Assistant API (:8001)..."
open_terminal "CineAgent — Assistant API :8001" \
    "cd assistant && uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

sleep 3

# Launch CLI or Streamlit
if [ "$MODE" = "ui" ]; then
    echo "Opening Streamlit UI (:8501)..."
    open_terminal "CineAgent — Streamlit UI :8501" \
        "cd assistant && streamlit run streamlit_app.py --server.port 8501"
else
    echo "Opening CLI (debug mode)..."
    open_terminal "CineAgent — CLI Chat" \
        "cd assistant && python -m assistant.cli chat --debug"
fi

echo ""
echo "=== All services launched ==="
echo ""
echo "Services:"
echo "  Cinema API:    http://localhost:8000"
echo "  Assistant API: http://localhost:8001"
if [ "$MODE" = "ui" ]; then
    echo "  Streamlit UI:  http://localhost:8501"
else
    echo "  CLI:           running in separate terminal"
fi
echo ""
echo "Run ./stop.sh to stop all services."
