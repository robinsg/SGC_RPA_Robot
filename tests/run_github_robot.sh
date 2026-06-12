#!/bin/bash
# Exit immediately if a command fails, or if an unset variable is used.
set -euo pipefail

# Capture the generic variant key sent by GitHub Actions
VARIANT_KEY="${1:-}"
CONFIG_FILE="/home/github-runner/customer_config.json"

if [[ -z "$VARIANT_KEY" ]]; then
    echo "ERROR: No variant key provided."
    exit 1
fi

# Check if the local config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: Local configuration file missing at $CONFIG_FILE"
    exit 1
fi

# Parse the parameters safely from the local JSON using Python
# We use Python because jq is not installed on the runner.
PARSE_CMD="
import json, sys
try:
    with open('$CONFIG_FILE') as f:
        config = json.load(f)
    variant = config.get('$VARIANT_KEY')
    if variant:
        print(variant.get('yaml_file', ''))
        print(variant.get('host', ''))
        print(variant.get('env_file', ''))
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"

# Use a temporary array to capture the output
mapfile -t PARAMS < <(python3 -c "$PARSE_CMD")

if [[ ${#PARAMS[@]} -lt 3 ]] || [[ -z "${PARAMS[0]}" ]] || [[ -z "${PARAMS[1]}" ]] || [[ -z "${PARAMS[2]}" ]]; then
    echo "ERROR: Could not resolve valid config for key '$VARIANT_KEY' in $CONFIG_FILE."
    exit 1
fi

SECRETS_PATH="$(pwd)/.secrets/"
YAML_PATH="${SECRETS_PATH}/yaml_scripts/"
YAML_FILE="${PARAMS[0]}"
HOST_NAME="${PARAMS[1]}"
ENV_FILE="${PARAMS[2]}"

# Prepend the SECRETS_PATH path
    # Prepend the location to the env and yaml config file path
    ENV_FILE="${SECRETS_PATH}${ENV_FILE}"
    YAML_FILE="${YAML_PATH}${YAML_FILE}"

echo "=========================================================="
echo "Executing robotic tests for: $VARIANT_KEY"
echo "Using parameters: --yaml-file $YAML_FILE --host [HIDDEN] --env [HIDDEN]"
echo "=========================================================="

# Ensure execution permissions on the original script
chmod +x ./run-robot.sh

# Trigger the existing, original wrapper script with the unpacked arguments
./run-robot.sh --yaml-file "$YAML_FILE" --host "$HOST_NAME" --env "$ENV_FILE"
