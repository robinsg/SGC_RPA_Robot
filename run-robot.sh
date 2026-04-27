#!/bin/bash

# Configuration
YAML_FILE=${1:-"example_script.yaml"}
ENV_FILE=".env"

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' $ENV_FILE | xargs)
fi

# Default values for TN5250 config
TN5250_HOST=${TN5250_HOST:-""}
TN5250_MAP=${TN5250_MAP:-"23"}
TN5250_SSL_FLAG=""
if [ "$TN5250_SSL" = "on" ] || [ "$TN5250_SSL" = "True" ]; then
    TN5250_SSL_FLAG="+ssl"
fi
TN5250_DEVICE_TYPE=${TN5250_DEVICE_TYPE:-"IBM-3477-FC"}
TN5250_DEVICE_NAME=${TN5250_DEVICE_NAME:-"ROBOT01"}
TMUX_SESSION=${TMUX_SESSION:-"5250_robot"}

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required but not installed."
    exit 1
fi

# Check if session exists, if not, start it
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    if [ -z "$TN5250_HOST" ]; then
        echo "Error: TN5250_HOST is not set and no existing tmux session '$TMUX_SESSION' found."
        exit 1
    fi
    
    echo "Starting new TN5250 session for host: $TN5250_HOST"
    # Construct the tn5250 command
    TN_CMD="tn5250 map=$TN5250_MAP env.TERM=$TN5250_DEVICE_TYPE env.DEVNAME=$TN5250_DEVICE_NAME $TN5250_SSL_FLAG $TN5250_HOST"
    
    tmux new-session -d -s "$TMUX_SESSION" "$TN_CMD"
    # Give it a moment to initialize
    sleep 2
fi

# Run the robot engine
echo "--- Starting RPA Automation ---"
npx tsx src/robot/cli.ts "$YAML_FILE"
EXIT_CODE=$?
echo "--- Robot Finished ---"

exit $EXIT_CODE
