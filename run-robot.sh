#!/bin/bash
set -euo pipefail

# --- Configuration & Constants ---
LOG_DIR="logs"
DEBUG_CAPTURE_DIR="logs/captures"
mkdir -p "$LOG_DIR" "$DEBUG_CAPTURE_DIR"
export LOG_DIR

# Map terminal types to dimensions (Source of truth)
get_terminal_size() {
    local device_type="$1"
    case "$device_type" in
        IBM-3477-FC|IBM-3477-FG|IBM-3180-2)
            echo "-x 132 -y 27"
            ;;
        IBM-3179-2|IBM-3196-A1|IBM-5292-2|IBM-5291-1|IBM-5251-11)
            echo "-x 80 -y 24"
            ;;
        *)
            return 1
            ;;
    esac
}

# --- Utility Functions ---
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --yaml-file <path>    Path to the YAML automation script"
    echo "  -h, --host <name>         LPAR host name (e.g., pub400.com)"
    echo "  --help                    Show this help message and exit"
    echo ""
    echo "Example:"
    echo "  $0 -f my_script.yaml -h pub400.com"
}

log_message() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    local log_file="${LOG_DIR}/${LPAR_NAME_LOWER:-unknown}.log"
    echo "${timestamp},${LPAR_NAME_LOWER:-unknown},BASH: ${message}" >> "$log_file"
    echo "${message}"
}

check_prerequisites() {
    local deps=("tmux" "python3" "tn5250")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            # Special case for tests that mock tn5250
            if [[ "${dep}" == "tn5250" && "${SKIP_PREREQ_CHECK:-}" == "true" ]]; then
                continue
            fi
            echo "Error: Required dependency '$dep' is not installed." >&2
            exit 1
        fi
    done
}

validate_connectivity() {
    local host="$1"
    local port="$2"
    log_message "Testing connectivity to ${host}:${port}..."
    if ! timeout 2 bash -c "true > /dev/tcp/${host}/${port}" 2>/dev/null; then
        log_message "Error: ${host}:${port} is not reachable."
        exit 1
    fi
    log_message "Connectivity test passed."
}

# --- Argument Parsing ---
YAML_FILE=""
LPAR_NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--yaml-file)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                YAML_FILE="$2"
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                exit 1
            fi
            ;;
        -h|--host)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                LPAR_NAME="$2"
                shift 2
            else
                echo "Error: Argument for $1 is missing" >&2
                exit 1
            fi
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown or positional argument: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$YAML_FILE" || -z "$LPAR_NAME" ]]; then
    echo "Error: Both --yaml-file and --host are required." >&2
    usage
    exit 1
fi

check_prerequisites

# Resolve YAML path
if [[ ! -f "$YAML_FILE" ]]; then
    if [[ -f "yaml_scripts/$YAML_FILE" ]]; then
        YAML_FILE="yaml_scripts/$YAML_FILE"
    else
        echo "Error: YAML file '$YAML_FILE' not found (checked current directory and yaml_scripts/)." >&2
        exit 1
    fi
fi

LPAR_NAME_LOWER=$(echo "$LPAR_NAME" | tr '[:upper:]' '[:lower:]')
ENV_FILE=".env.${LPAR_NAME_LOWER}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: Configuration file '$ENV_FILE' not found for LPAR '$LPAR_NAME'." >&2
    exit 1
fi

# Load environment (Targeted)
while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[^#].*= ]]; then
        export "$line"
    fi
done < "$ENV_FILE"

export TN5250_HOST="$LPAR_NAME_LOWER"
TMUX_SESSION="robot-${TN5250_HOST}"
export TMUX_SESSION

# Connectivity Setup
if [[ -n "${HMC_HOST:-}" ]]; then
    CHECK_HOST="$HMC_HOST"
    CHECK_PORT=2301
    FULL_CMD=(tn5250 "ssl:${HMC_HOST}:2301")
else
    CHECK_HOST="$TN5250_HOST"
    CHECK_PORT=${TN5250_PORT:-23}
    [[ "${TN5250_SSL:-}" =~ ^(on|True)$ ]] && CHECK_PORT=${TN5250_PORT:-992}
    
    TN_ARGS=("map=${TN5250_MAP:-285}" "env.TERM=${TN5250_DEVICE_TYPE:-IBM-3477-FC}")
    [[ -n "${TN5250_DEVICE_NAME:-}" ]] && TN_ARGS+=("env.DEVNAME=$TN5250_DEVICE_NAME")
    [[ "${TN5250_SSL:-}" =~ ^(on|True)$ ]] && TN_ARGS+=("+ssl")
    FULL_CMD=(tn5250 "${TN_ARGS[@]}" "$TN5250_HOST")
fi

# Skip connectivity check in tests if requested
if [[ "${SKIP_CONN_CHECK:-}" != "true" ]]; then
    validate_connectivity "$CHECK_HOST" "$CHECK_PORT"
fi

# Tmux Lifecycle
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_message "Existing session '$TMUX_SESSION' found. Terminating it to ensure a clean start."
    tmux kill-session -t "$TMUX_SESSION"
    sleep 1
fi

TMUX_SIZE_ARGS=$(get_terminal_size "${TN5250_DEVICE_TYPE:-IBM-3477-FC}")
log_message "Starting new TN5250 session '$TMUX_SESSION' for host: $TN5250_HOST"
# shellcheck disable=SC2086
tmux new-session -d -s "$TMUX_SESSION" $TMUX_SIZE_ARGS "${FULL_CMD[@]}"
sleep 2

if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_message "Error: Failed to start tmux session '$TMUX_SESSION'."
    exit 1
fi

# Execution
set +e
log_message "--- Starting RPA Automation (Python) ---"
PYTHONPATH="." python3 -m robot_py.cli --yaml-file "$YAML_FILE"
EXIT_CODE=$?
set -e

log_message "--- Robot Finished ---"
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_message "Terminating tmux session '$TMUX_SESSION'..."
    tmux kill-session -t "$TMUX_SESSION"
fi

exit "$EXIT_CODE"
