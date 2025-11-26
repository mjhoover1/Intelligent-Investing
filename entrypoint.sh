#!/bin/bash
set -e

# Signal Sentinel - Container Entrypoint
# Usage: ./entrypoint.sh [web|worker|both|cli]

MODE="${1:-web}"

echo "Starting Signal Sentinel in ${MODE} mode..."

# Initialize database
python -c "from src.db.database import init_db; init_db()"

case "$MODE" in
    web)
        # Run FastAPI server only
        echo "Starting API server on port 8000..."
        exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000
        ;;

    worker)
        # Run monitor worker only
        echo "Starting monitor worker (interval: ${MONITOR_INTERVAL_SECONDS}s)..."
        exec python -m src.cli.main monitor start --ai
        ;;

    both)
        # Run both API and monitor (using background process)
        echo "Starting API server and monitor worker..."

        # Start monitor in background
        python -m src.cli.main monitor start --ai &
        MONITOR_PID=$!

        # Trap to clean up background process
        trap "kill $MONITOR_PID 2>/dev/null" EXIT

        # Start API server in foreground
        exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000
        ;;

    cli)
        # Run CLI command (pass remaining args)
        shift
        exec python -m src.cli.main "$@"
        ;;

    *)
        echo "Unknown mode: $MODE"
        echo "Usage: $0 [web|worker|both|cli]"
        exit 1
        ;;
esac
