#!/usr/bin/env bash
set -euo pipefail

echo "=== CineAgent — Stopping Services ==="
echo ""

stopped=0

for port in 8000 8001 8501; do
    pids=$(lsof -ti ":${port}" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Stopping process on port ${port}..."
        echo "$pids" | xargs kill 2>/dev/null || true
        stopped=$((stopped + 1))
    fi
done

if [ "$stopped" -eq 0 ]; then
    echo "No services running."
else
    echo ""
    echo "Stopped ${stopped} service(s)."
fi
