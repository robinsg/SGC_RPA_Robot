#!/bin/bash
set -euo pipefail

# --- Logging Setup ---
LOG_DIR="logs"
DEBUG_CAPTURE_DIR="logs/captures"
mkdir -p "$LOG_DIR"
mkdir -p "$DEBUG_CAPTURE_DIR"
export LOG_DIR

# --- Argument Processing ---
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --yaml-file <path>    Path to the YAML automation script"
    echo "  -h, --host <name>         LPAR host name (e.g., pub400.com)"
    echo "  -e, --env <path>          Path to the environment file (must start with '.env')"
    echo "  --help                    Show this help message and exit"
    echo ""
    echo "Example:"
    echo "  $0 -f my_script.yaml -h pub400.com"
    echo "  $0 -f my_script.yaml -h pub400.com -e .env.custom"
}

YAML_FILE=""
LPAR_NAME=""
ENV_FILE_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--yaml-file)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                YAML_FILE="$2"
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
                exit 1
            fi
            ;;
        -h|--host)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                LPAR_NAME="$2"
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
                exit 1
            fi
            ;;
        -e|--env)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                ENV_FILE_ARG="$2"
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
                exit 1
            fi
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown or positional argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

# Verify required arguments
if [[ -z "$YAML_FILE" ]] || [[ -z "$LPAR_NAME" ]]; then
    echo "Error: Both --yaml-file and --host are required." >&2
    usage
    exit 1
fi

# Verify YAML file exists
# Search for the YAML file:
# 1. At the provided path
# 2. In the yaml_scripts directory
if [[ -f "$YAML_FILE" ]]; then
    : # File found at provided path
elif [[ -f "yaml_scripts/$YAML_FILE" ]]; then
    YAML_FILE="yaml_scripts/$YAML_FILE"
else
    echo "Error: YAML file '$YAML_FILE' not found (checked current directory and yaml_scripts/)." >&2
    exit 1
fi

LPAR_NAME_LOWER=$(echo "$LPAR_NAME" | tr '[:upper:]' '[:lower:]')

# Validate environment file if provided
if [[ -n "$ENV_FILE_ARG" ]]; then
    ENV_BASE=$(basename "$ENV_FILE_ARG")
    if [[ "$ENV_BASE" != .env* ]]; then
        echo "Error: Environment file name must start with '.env'" >&2
        exit 1
    fi
    ENV_FILE="$ENV_FILE_ARG"
else
    ENV_FILE=".env.${LPAR_NAME_LOWER}"
fi

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
if [ -f "$ENV_FILE" ]; then
  log_message "Loading environment variables from $ENV_FILE"
  # Manually parse the .env file instead of sourcing it to prevent code injection.
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Strip leading/trailing whitespace
    line=$(echo "$line" | xargs)

    # Skip comments and empty lines
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue

    # Remove 'export ' prefix if present
    line="${line#export }"

    # Extract key and value, ignoring inline comments
    if [[ "$line" == *=* ]]; then
      key="${line%%=*}"
      # Strip potential trailing comment from the rest of the line
      value_part="${line#*=}"
      value="${value_part%% #*}"
      # Trim whitespace from key and value
      key=$(echo "$key" | xargs)
      value=$(echo "$value" | xargs)
      # Handle Secret() keyword
      if [[ "$value" == Secret\(*\) ]]; then
        # Extract content between parentheses
        secret_content="${value#Secret(}"
        secret_content="${secret_content%)}"
        value=$(echo "$secret_content" | xargs)

        # Add to ROBOT_SENSITIVE_VARS
        if [ -z "${ROBOT_SENSITIVE_VARS:-}" ]; then
          export ROBOT_SENSITIVE_VARS="$key"
        else
          # Avoid duplicates
          if [[ ! ",$ROBOT_SENSITIVE_VARS," == *",$key,"* ]]; then
            export ROBOT_SENSITIVE_VARS="$ROBOT_SENSITIVE_VARS,$key"
          fi
        fi
      fi

      # Strip quotes from value
      value="${value%\"}"
      value="${value#\"}"
      value="${value%\'}"
      value="${value#\'}"

      export "$key=$value"
    fi
  done < "$ENV_FILE"
else
  log_message "Error: Configuration file '$ENV_FILE' not found for LPAR '$LPAR_NAME'."
  exit 1
fi

# --- Variable Assignment & Integrity ---
# The command-line LPAR name is the source of truth for the host.
# This prevents the .env file from overriding the LPAR context.
export TN5250_HOST="$LPAR_NAME_LOWER"

# --- Connectivity Check ---
if [ -n "${HMC_HOST:-}" ]; then
    CHECK_HOST="${HMC_HOST:-}"
    CHECK_PORT=2301
else
    CHECK_HOST="$TN5250_HOST"
    if [ "${TN5250_SSL:-}" = "on" ] || [ "${TN5250_SSL:-}" = "True" ]; then
        # Default to 992 for SSL, but allow override via TN5250_PORT
        CHECK_PORT=${TN5250_PORT:-992}
    else
        CHECK_PORT=${TN5250_PORT:-23}
    fi
fi

log_message "Testing connectivity to ${CHECK_HOST}:${CHECK_PORT}..."
# timeout 2s, 2>/dev/null to suppress 'connection refused' bash errors
if ! timeout 2 bash -c "true > /dev/tcp/${CHECK_HOST}/${CHECK_PORT}" 2>/dev/null; then
    log_message "Error: Port ${CHECK_PORT} on host ${CHECK_HOST} is not reachable."
    log_message "Ensure your VPN is connected or the target system is up."
    exit 1
fi
log_message "Connectivity test passed."

# Unconditionally set the session name based on the host. This prevents
# a value from the .env file from causing a mismatch.
TMUX_SESSION="robot-${TN5250_HOST}"

# --- TN5250 Parameter Setup ---
TN5250_MAP=${TN5250_MAP:-"285"}
TN5250_DEVICE_TYPE=${TN5250_DEVICE_TYPE:-"IBM-3477-FC"}

# Determine the required tmux buffer dimensions based on the device type
if [[ "$TN5250_DEVICE_TYPE" == "IBM-3477-FC" || "$TN5250_DEVICE_TYPE" == "IBM-3477-FG" || "$TN5250_DEVICE_TYPE" == "IBM-3180-2" ]]; then
    TMUX_SIZE=(-x 132 -y 27)
elif [[ "$TN5250_DEVICE_TYPE" == "IBM-3179-2" || "$TN5250_DEVICE_TYPE" == "IBM-3196-A1" || "$TN5250_DEVICE_TYPE" == "IBM-5292-2" || "$TN5250_DEVICE_TYPE" == "IBM-5291-1" || "$TN5250_DEVICE_TYPE" == "IBM-5251-11" ]]; then
    TMUX_SIZE=(-x 80 -y 24)
else
    log_message "Error: Unsupported TN5250_DEVICE_TYPE '$TN5250_DEVICE_TYPE'."
    exit 1
fi

if [ -n "${HMC_HOST:-}" ]; then
    log_message "HMC_HOST detected. Connecting via HMC Proxy on port 2301."
    # Use the simplified connection format requested for HMC
    FULL_CMD=(tn5250 "ssl:${HMC_HOST:-}:2301")
else
    # Build the standard tn5250 command arguments for direct connection
    TN_CMD_ARGS=("map=$TN5250_MAP" "env.TERM=$TN5250_DEVICE_TYPE")
    
    if [ -n "${TN5250_DEVICE_NAME:-}" ]; then
        TN_CMD_ARGS+=("env.DEVNAME=$TN5250_DEVICE_NAME")
    fi

    if [ "${TN5250_SSL:-}" = "on" ] || [ "${TN5250_SSL:-}" = "True" ]; then
        TN_CMD_ARGS+=("+ssl")
    fi
    
    TN_CMD_ARGS+=("$TN5250_HOST")
    FULL_CMD=(tn5250 "${TN_CMD_ARGS[@]}")
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
log_message "Executing: ${FULL_CMD[*]} with window size ${TMUX_SIZE[*]}"
tmux new-session -d -s "$TMUX_SESSION" "${TMUX_SIZE[@]}" "${FULL_CMD[@]}"

# Robustness Check: Wait a moment and verify the session started.
# A longer delay helps prevent a race condition where the python script
# starts before tn5250 has connected or had a chance to fail.
sleep 2

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
log_message "--- Starting RPA Automation (Python) ---"
PYTHONPATH=".:${PYTHONPATH:-}" python3 -m robot_py.cli --yaml-file "$YAML_FILE" --env "$ENV_FILE"
EXIT_CODE=$?
set -e # Re-enable exit on error

log_message "--- Robot Finished ---"

# --- Cleanup ---
# Terminate the tmux session if it was created by this script.
# This ensures no dangling sessions remain, whether the robot succeeded or failed.
if [ "$SESSION_CREATED_BY_SCRIPT" = true ]; then
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        log_message "Terminating tmux session '$TMUX_SESSION'..."
        tmux kill-session -t "$TMUX_SESSION"
        log_message "Session terminated."
    else
        log_message "Session '$TMUX_SESSION' already terminated."
    fi
fi

exit "$EXIT_CODE"
