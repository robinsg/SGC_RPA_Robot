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
        print(variant.get('log_level', ''))
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"

# Use a temporary array to capture the output
mapfile -t PARAMS < <(python3 -c "$PARSE_CMD")

if [[ ${#PARAMS[@]} -lt 4 ]] || [[ -z "${PARAMS[0]}" ]] || [[ -z "${PARAMS[1]}" ]] || [[ -z "${PARAMS[2]}" ]] || [[ -z "${PARAMS[3]}" ]]; then
    echo "ERROR: Could not resolve valid config for key '$VARIANT_KEY' in $CONFIG_FILE."
    exit 1
fi

SECRETS_PATH="${HOME}/.secrets/"
YAML_PATH="${SECRETS_PATH}/yaml_scripts/"
YAML_FILE="${PARAMS[0]}"
HOST_NAME="${PARAMS[1]}"
ENV_FILE="${PARAMS[2]}"
LOG_LEVEL="${PARAMS[3]}"

# Prepend the SECRETS_PATH path
    # Prepend the location to the env and yaml config file path
    ENV_FILE="${SECRETS_PATH}${ENV_FILE}"
    YAML_FILE="${YAML_PATH}${YAML_FILE}"

# GitHub Actions Masking
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    # Pass variables to python via environment to avoid escaping issues
    export MASK_HOST_NAME="$HOST_NAME"
    export MASK_YAML_FILE="$YAML_FILE"
    export MASK_ENV_FILE="$ENV_FILE"
    python3 -c "
import os
def emit_mask(s):
    if not s: return
    print(f'::add-mask::{s}')

def emit_host_masks(s):
    if not s: return
    # To satisfy 'any case combination', we generate all permutations for short strings
    # or just upper/lower for longer ones to avoid performance issues.
    n = len(s)
    masks = set()
    if n <= 12:
        for i in range(1 << n):
            res = ''.join(s[j].upper() if (i >> j) & 1 else s[j].lower() for j in range(n))
            masks.add(res)
    else:
        masks.add(s)
        masks.add(s.lower())
        masks.add(s.upper())
    for m in sorted(masks):
        print(f'::add-mask::{m}')

emit_host_masks(os.environ.get('MASK_HOST_NAME'))
emit_mask(os.environ.get('MASK_YAML_FILE'))
emit_mask(os.environ.get('MASK_ENV_FILE'))

env_file_path = os.environ.get('MASK_ENV_FILE')
if env_file_path and os.path.exists(env_file_path):
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if line.startswith('export '): line = line[7:].strip()
            if '=' in line:
                parts = line.split('=', 1)
                value = parts[1].split(' #', 1)[0].strip()
                if value.startswith('Secret(') and value.endswith(')'):
                    secret = value[7:-1].strip().strip('\"\\'')
                    emit_mask(secret)
"
    unset MASK_HOST_NAME MASK_YAML_FILE MASK_ENV_FILE
fi

echo "=========================================================="
echo "Executing robotic tests for: $VARIANT_KEY"
echo "Using parameters: --yaml-file $YAML_FILE --host [HIDDEN] --env [HIDDEN]"
echo "Log level: $LOG_LEVEL"
echo "=========================================================="

# Ensure execution permissions on the original script
chmod +x ./run-robot.sh

# Trigger the existing, original wrapper script with the unpacked arguments
LOG_LEVEL="${LOG_LEVEL:-INFO}" ./run-robot.sh --yaml-file "$YAML_FILE" --host "$HOST_NAME" --env "$ENV_FILE"
