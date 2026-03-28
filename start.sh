#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="cineagent"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs/$(date +%Y%m%d_%H%M%S)"
MODE="cli"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --ui) MODE="ui"; shift ;;
        --cli) MODE="cli"; shift ;;
        -h|--help)
            echo "Usage: ./start.sh [--cli|--ui]"
            echo ""
            echo "  --cli   Launch CLI chat with debug (default)"
            echo "  --ui    Launch Streamlit UI on :8501"
            echo ""
            echo "Services log to logs/ directory."
            echo "Run ./stop.sh to stop background services."
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Verify conda env is active
if [[ "${CONDA_DEFAULT_ENV:-}" != "${ENV_NAME}" ]]; then
    echo "ERROR: Conda env '${ENV_NAME}' is not active."
    echo "Run:  conda activate ${ENV_NAME}"
    echo "Then: ./start.sh"
    exit 1
fi

# Verify .env exists
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo "ERROR: .env file not found."
    echo "Run ./setup.sh or copy .env.example to .env and fill in API keys."
    exit 1
fi

# Set PYTHONPATH so both packages resolve from repo root
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# Load .env into environment so services find API keys regardless of cwd
set -a
source "${SCRIPT_DIR}/.env"
set +a

# Create logs dir
mkdir -p "${LOG_DIR}"

echo ""
echo "=== CineAgent ==="
echo ""

# Kill any existing processes on our ports
for port in 8000 8001 8501; do
    pids=$(lsof -ti ":${port}" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Stopping existing process on port ${port}..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
    fi
done

# Cleanup function — kill background services on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    for port in 8000 8001 8501; do
        pids=$(lsof -ti ":${port}" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill 2>/dev/null || true
        fi
    done
    echo "Done. Logs are in ${LOG_DIR}/"
}
trap cleanup EXIT

# Start Cinema API (background, logs to file)
echo "Starting Cinema API on :8000 (logs: logs/cinema.log)"
uvicorn cinema_api.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    --app-dir "${SCRIPT_DIR}" \
    > "${LOG_DIR}/cinema.log" 2>&1 &

sleep 2

# Verify Cinema API started
if ! lsof -ti :8000 &>/dev/null; then
    echo "ERROR: Cinema API failed to start. Check logs/cinema.log"
    cat "${LOG_DIR}/cinema.log"
    exit 1
fi
echo "  Cinema API ready."

# Start Assistant API (background, logs to file)
echo "Starting Assistant API on :8001 (logs: logs/assistant.log)"
uvicorn assistant.main:app \
    --host 0.0.0.0 --port 8001 --reload \
    --app-dir "${SCRIPT_DIR}" \
    > "${LOG_DIR}/assistant.log" 2>&1 &

sleep 3

# Verify Assistant API started
if ! lsof -ti :8001 &>/dev/null; then
    echo "ERROR: Assistant API failed to start. Check logs/assistant.log"
    cat "${LOG_DIR}/assistant.log"
    exit 1
fi
echo "  Assistant API ready."

echo ""
echo "Services running (logs in logs/):"
echo "  Cinema API:    http://localhost:8000  -> logs/cinema.log"
echo "  Assistant API: http://localhost:8001  -> logs/assistant.log"
echo ""

# Launch CLI or Streamlit in foreground
if [ "$MODE" = "ui" ]; then
    echo "Starting Streamlit UI on :8501..."
    echo "  Press Ctrl+C to stop everything."
    echo ""
    cd "${SCRIPT_DIR}/assistant"
    streamlit run streamlit_app.py --server.port 8501
else
    echo "Starting CineAssist CLI (debug mode)..."
    echo "  Type 'quit' or press Ctrl+C to stop."
    echo ""
    python -m assistant.cli chat --debug
fi
