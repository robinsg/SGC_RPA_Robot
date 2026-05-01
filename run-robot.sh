#!/bin/bash
set -e

# --- Logging Setup ---
LOG_DIR="logs"
DEBUG_CAPTURE_DIR="logs/captures"
mkdir -p "$LOG_DIR"
mkdir -p "$DEBUG_CAPTURE_DIR"
export LOG_DIR

# --- Argument Processing ---
# YAML file is the first argument, LPAR name is the second.
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Error: Both YAML file and LPAR name are required."
  echo "Usage: $0 <path_to_yaml_script> <LPAR_NAME>"
  exit 1
fi

YAML_FILE="$1"
LPAR_NAME="$2"

# Verify YAML file exists
if [ ! -f "$YAML_FILE" ]; then
  echo "Error: YAML file '$YAML_FILE' not found."
  exit 1
fi

LPAR_NAME_LOWER=$(echo "$LPAR_NAME" | tr '[:upper:]' '[:lower:]')

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
  log_message "Error: Configuration file '$ENV_FILE' not found for LPAR '$LPAR_NAME'."
  exit 1
fi

# --- Variable Assignment & Integrity ---
# The command-line LPAR name is the source of truth for the host.
# This prevents the .env file from overriding the LPAR context.
export TN5250_HOST=$LPAR_NAME_LOWER

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

# Ensure a clean state by terminating any existing session with this name.
# This prevents "hanging" sessions from causing state-related failures.
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_message "Existing session '$TMUX_SESSION' found. Terminating it to ensure a clean start."
    tmux kill-session -t "$TMUX_SESSION"
    # Brief pause to allow the system to reap the processes
    sleep 1
fi

# Track if this script instance created the session (now effectively always true)
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

# Determine the required tmux buffer dimensions based on the device type
# 27x132 models
if [[ "$TN5250_DEVICE_TYPE" == "IBM-3477-FC" || "$TN5250_DEVICE_TYPE" == "IBM-3477-FG" || "$TN5250_DEVICE_TYPE" == "IBM-3180-2" ]]; then
    TMUX_SIZE="-x 132 -y 27"
# 24x80 models
elif [[ "$TN5250_DEVICE_TYPE" == "IBM-3179-2" || "$TN5250_DEVICE_TYPE" == "IBM-3196-A1" || "$TN5250_DEVICE_TYPE" == "IBM-5292-2" || "$TN5250_DEVICE_TYPE" == "IBM-5291-1" || "$TN5250_DEVICE_TYPE" == "IBM-5251-11" ]]; then
    TMUX_SIZE="-x 80 -y 24"
else
    log_message "Error: Unsupported TN5250_DEVICE_TYPE '$TN5250_DEVICE_TYPE'."
    exit 1
fi

# The host must be the last argument for tn5250
TN_CMD_ARGS+=("$TN5250_HOST")

FULL_CMD="tn5250 ${TN_CMD_ARGS[*]}"
log_message "Executing: $FULL_CMD with window size $TMUX_SIZE"
tmux new-session -d -s "$TMUX_SESSION" $TMUX_SIZE "$FULL_CMD"

# Robustness Check: Wait a moment and verify the session started.
sleep 1
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_message "Error: Failed to start tmux session '$TMUX_SESSION'."
    log_message "This is often caused by an invalid hostname or tn5250 command error."
    log_message "Please check the hostname in your .env file and the tn5250 installation."
    exit 1
fi
log_message "Session started successfully."


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
