#!/bin/bash
set -e

# --- Configuration Loading ---
# Check if the LPAR name argument is provided.
if [ -z "$1" ]; then
  echo "Error: LPAR name is required as the first argument."
  echo "Usage: $0 <LPAR_NAME> [path_to_yaml_script]"
  exit 1
fi

# Convert LPAR name to lower case and export it as TN5250_HOST
LPAR_NAME_LOWER=$(echo "$1" | tr '[:upper:]' '[:lower:]')
export TN5250_HOST=$LPAR_NAME_LOWER

# Load the environment file specific to the host
ENV_FILE=".env.${TN5250_HOST}"
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment variables from $ENV_FILE"
  # allexport ensures all variables in the sourced file are exported
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
else
  echo "Error: Configuration file '$ENV_FILE' not found for LPAR '$1'."
  exit 1
fi

# --- Variable Defaults ---
# Default values for TN5250 config, can be overridden by the .env file
# The second argument is the YAML file, defaulting to example_script.yaml
YAML_FILE=${2:-"example_script.yaml"}
TN5250_MAP=${TN5250_MAP:-"23"}
TN5250_DEVICE_TYPE=${TN5250_DEVICE_TYPE:-"IBM-3477-FC"}
# TN5250_DEVICE_NAME is optional and read from the env file if present.
TMUX_SESSION=${TMUX_SESSION:-"robot-${TN5250_HOST}"} # Host-specific session name

TN5250_SSL_FLAG=""
if [ "$TN5250_SSL" = "on" ] || [ "$TN5250_SSL" = "True" ]; then
    TN5250_SSL_FLAG="+ssl"
fi

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required but not installed."
    exit 1
fi

# Check if session exists, if not, start it
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "Starting new TN5250 session '$TMUX_SESSION' for host: $TN5250_HOST"
    
    # Build the tn5250 command arguments dynamically
    TN_CMD_ARGS=("map=$TN5250_MAP" "env.TERM=$TN5250_DEVICE_TYPE")

    # Add DEVNAME only if the variable is set and not empty
    if [ -n "$TN5250_DEVICE_NAME" ]; then
        TN_CMD_ARGS+=("env.DEVNAME=$TN5250_DEVICE_NAME")
    fi

    if [ -n "$TN5250_SSL_FLAG" ]; then
        TN_CMD_ARGS+=("$TN5250_SSL_FLAG")
    fi
    
    TN_CMD_ARGS+=("$TN5250_HOST")
    
    FULL_CMD="tn5250 ${TN_CMD_ARGS[*]}"
    echo "Executing: $FULL_CMD"
    tmux new-session -d -s "$TMUX_SESSION" "$FULL_CMD"
    
    # Give it a moment to initialize before the robot tries to connect
    echo "Waiting for session to initialize..."
    sleep 2
fi

# Export the session name so the robot knows which session to target
export TMUX_SESSION

# Run the robot engine
echo "--- Starting RPA Automation ---"
npx tsx src/robot/cli.ts "$YAML_FILE"
EXIT_CODE=$?
echo "--- Robot Finished ---"

exit $EXIT_CODE