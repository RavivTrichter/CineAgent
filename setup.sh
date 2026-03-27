#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="cineagent"
PYTHON_VERSION="3.11"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== CineAgent Setup ==="
echo ""

# 1. Check conda
if ! command -v conda &>/dev/null; then
    echo "ERROR: conda is not installed or not in PATH."
    echo "Install Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 2. Create conda env (skip if exists)
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Conda env '${ENV_NAME}' already exists — skipping creation."
else
    echo "Creating conda env '${ENV_NAME}' with Python ${PYTHON_VERSION}..."
    conda create -y -n "${ENV_NAME}" python="${PYTHON_VERSION}"
fi

# 3. Activate env
echo "Activating '${ENV_NAME}'..."
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

# 4. Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r "${SCRIPT_DIR}/cinema_api/requirements.txt"
pip install -q -r "${SCRIPT_DIR}/assistant/requirements.txt"
pip install -q -r "${SCRIPT_DIR}/tests/requirements.txt"

# 5. Copy .env if needed
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    if [ -f "${SCRIPT_DIR}/.env.example" ]; then
        cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
        echo ""
        echo "WARNING: Created .env from .env.example."
        echo "Please edit .env and fill in your API keys:"
        echo "  ANTHROPIC_API_KEY=..."
        echo "  TMDB_API_KEY=..."
        echo "  OMDB_API_KEY=..."
    fi
else
    echo ".env already exists — skipping."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. conda activate ${ENV_NAME}"
echo "  2. Edit .env with your API keys (if not done)"
echo "  3. ./start.sh          # Launch all services (CLI mode)"
echo "  4. ./start.sh --ui     # Launch all services (Streamlit mode)"
