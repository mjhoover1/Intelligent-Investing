"""Main entry point for the API server."""

import os
import sys

import uvicorn

from src.api.app import app


if __name__ == "__main__":
    # Get host/port from environment or defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError("Port out of range")
    except ValueError:
        print(f"Error: Invalid PORT value '{port_str}'. Must be an integer between 1-65535.")
        sys.exit(1)

    uvicorn.run(app, host=host, port=port)
