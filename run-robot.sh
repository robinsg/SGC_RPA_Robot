#!/bin/bash
set -e

# --- Logging Setup ---
LOG_DIR="logs"
DEBUG_CAPTURE_DIR="logs/captures"
mkdir -p "$LOG_DIR"
mkdir -p "$DEBUG_CAPTURE_DIR"
export LOG_DIR

# --- LPAR Name Processing ---
# This must be done early so the logger knows the filename.
if [ -z "$1" ]; then
  echo "Error: LPAR name is required as the first argument."
  echo "Usage: $0 <LPAR_NAME> [path_to_yaml_script]"
  exit 1
fi
LPAR_NAME_LOWER=$(echo "$1" | tr '[:upper:]' '[:lower:]')

# --- Unified Logging Function ---
# Logs a message to both stdout and the appropriate log file.
log_message() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    local log_file="${LOG_DIR}/${LPAR_NAME_LOWER}.log"
    
    # Append the formatted message to the log file
    echo "${timestamp},${LPAR_NAME_LOWER},BASH: ${message}" >> "$log_file"
    
    # Also print the original message to the console
    echo "${message}"
}


# --- Configuration Loading ---
ENV_FILE=".env.${LPAR_NAME_LOWER}"
if [ -f "$ENV_FILE" ]; then
  log_message "Loading environment variables from $ENV_FILE"
  # allexport ensures all variables in the sourced file are exported
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
else
  log_message "Error: Configuration file '$ENV_FILE' not found for LPAR '$1'."
  exit 1
fi

# --- Variable Assignment & Integrity ---
# The command-line LPAR name is the source of truth for the host.
# This prevents the .env file from overriding the LPAR context.
export TN5250_HOST=$LPAR_NAME_LOWER

# The second argument is the YAML file, defaulting to example_script.yaml
YAML_FILE=${2:-"example_script.yaml"}

# Unconditionally set the session name based on the host. This prevents
# a value from the .env file from causing a mismatch.
TMUX_SESSION="robot-${TN5250_HOST}"

# --- TN5250 Parameter Setup ---
TN5250_MAP=${TN5250_MAP:-"285"}
TN5250_DEVICE_TYPE=${TN5250_DEVICE_TYPE:-"IBM-3477-FC"}

TN5250_SSL_FLAG=""
if [ "$TN5250_SSL" = "on" ] || [ "$TN5250_SSL" = "True" ]; then
    TN5250_SSL_FLAG="+ssl"
fi

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    log_message "Error: tmux is required but not installed."
    exit 1
fi

# Track if this script instance created the session
SESSION_CREATED_BY_SCRIPT=false
# Check if session exists, if not, start it
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    SESSION_CREATED_BY_SCRIPT=true
    log_message "Starting new TN5250 session '$TMUX_SESSION' for host: $TN5250_HOST"
    
    # Build the tn5250 command arguments dynamically
    TN_CMD_ARGS=("map=$TN5250_MAP" "env.TERM=$TN5250_DEVICE_TYPE")

    # Add DEVNAME only if the variable is set and not empty
    if [ -n "$TN5250_DEVICE_NAME" ]; then
        TN_CMD_ARGS+=("env.DEVNAME=$TN5250_DEVICE_NAME")
    fi

    if [ -n "$TN5250_SSL_FLAG" ]; then
        TN_CMD_ARGS+=("$TN5250_SSL_FLAG")
    fi
    
    # The host must be the last argument for tn5250
    TN_CMD_ARGS+=("$TN5250_HOST")
    
    FULL_CMD="tn5250 ${TN_CMD_ARGS[*]}"
    log_message "Executing: $FULL_CMD"
    tmux new-session -d -s "$TMUX_SESSION" "$FULL_CMD"
    
    # Robustness Check: Wait a moment and verify the session started.
    sleep 1
    if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        log_message "Error: Failed to start tmux session '$TMUX_SESSION'."
        log_message "This is often caused by an invalid hostname or tn5250 command error."
        log_message "Please check the hostname in your .env file and the tn5250 installation."
        exit 1
    fi
    log_message "Session started successfully."
fi

# Export the session name so the robot knows which session to target
export TMUX_SESSION

# Run the robot engine, but temporarily disable 'exit on error' to handle cleanup
set +e
log_message "--- Starting RPA Automation ---"
npx tsx src/robot/cli.ts "$YAML_FILE"
EXIT_CODE=$?
set -e # Re-enable exit on error

log_message "--- Robot Finished ---"

# --- Cleanup ---
# If the script failed AND this script was the one that created the session, kill it.
if [ "$EXIT_CODE" -ne 0 ] && [ "$SESSION_CREATED_BY_SCRIPT" = true ]; then
    log_message "Robot failed with exit code $EXIT_CODE. Terminating tmux session '$TMUX_SESSION'..."
    tmux kill-session -t "$TMUX_SESSION"
    log_message "Session terminated."
fi

exit $EXIT_CODE
