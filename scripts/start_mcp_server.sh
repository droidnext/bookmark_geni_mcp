#!/bin/bash
# Start script for Bookmark Geni MCP Server
# This script sets up the environment and starts the MCP server
# NOTE: All output must go to stderr (>&2) to avoid breaking MCP stdio protocol
# MCP uses stdout for JSON-RPC messages only

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the MCP server root directory (parent of scripts folder)
MCP_SERVER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Change to MCP server root directory
cd "$MCP_SERVER_ROOT" || exit 1

echo "Starting Bookmark Geni MCP Server" >&2
echo "Script directory: $SCRIPT_DIR" >&2
echo "MCP server root: $MCP_SERVER_ROOT" >&2
echo "Working directory: $(pwd)" >&2

# Use PYTHON_PATH environment variable if set, otherwise try pyenv Python, then fall back to system python3
if [ -n "$PYTHON_PATH" ]; then
    PYTHON_CMD="$PYTHON_PATH"
    echo "Using PYTHON_PATH from environment: $PYTHON_CMD" >&2
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "Using system python3" >&2
else
    echo "Error: python3 not found in PATH and PYTHON_PATH not set" >&2
    exit 1
fi


# Install dependencies from requirements.txt if it exists
# NOTE: Redirect ALL pip output (stdout and stderr) to stderr to avoid breaking MCP stdio protocol
# MCP stdio protocol requires stdout to contain ONLY JSON-RPC messages
REQUIREMENTS_FILE="$MCP_SERVER_ROOT/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing/updating dependencies from requirements.txt..." >&2
    # Redirect stdout to stderr, then redirect stderr to stdout (which is now stderr)
    # This ensures ALL output (including pip notices) goes to stderr
    "$PYTHON_CMD" -m pip install --quiet --upgrade -r "$REQUIREMENTS_FILE" 1>&2 2>&1 || {
        echo "Warning: Failed to install some dependencies. Continuing anyway..." >&2
    }
fi

# Start the MCP server with unbuffered output for stdio protocol
# -u flag ensures unbuffered stdout/stderr for MCP communication
SERVER_SCRIPT="$MCP_SERVER_ROOT/servers/bookmark_server.py"
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo "Error: Server script not found at $SERVER_SCRIPT" >&2
    exit 1
fi
exec "$PYTHON_CMD" -u "$SERVER_SCRIPT" "$@"
