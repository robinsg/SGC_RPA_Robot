#!/QOpenSys/usr/bin/bash

# robot_client.sh
# This script is intended to be run in the IBM i PASE environment.
# It invokes the SGC_RPA_Robot on a remote Ubuntu VM via SSH.

ROBOT_SERVER="your-ubuntu-vm-ip"
ROBOT_USER="robotuser"
ROBOT_PATH="/path/to/SGC_RPA_Robot"

YAML_SCRIPT="$1"
LPAR_NAME="$2"

if [ -z "$YAML_SCRIPT" ] || [ -z "$LPAR_NAME" ]; then
    echo "Usage: $0 <yaml_script> <lpar_name>"
    exit 1
fi

# 1. Invoke the robot via SSH with the --json flag
# We capture the output to a variable.
echo "Invoking robot for $LPAR_NAME..."
RESPONSE=$(ssh "${ROBOT_USER}@${ROBOT_SERVER}" "${ROBOT_PATH}/run-robot.sh --json $YAML_SCRIPT $LPAR_NAME")
EXIT_CODE=$?

# 2. Check for SSH success before parsing
if [ $EXIT_CODE -ne 0 ] && [ -z "$RESPONSE" ]; then
    echo "SSH connection failed or remote script crashed."
    exit $EXIT_CODE
fi

# 3. Parse the JSON response using Python (native in IBM i PASE)
STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'failure'))")
LOG_FILE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('log_file', ''))")

echo "Robot Status: $STATUS"
echo "Exit Code: $EXIT_CODE"

# 3. If it failed, retrieve the full log file via SCP
if [ "$EXIT_CODE" -ne 0 ] || [ "$STATUS" = "failure" ]; then
    echo "Automation failed. Retrieving full log details..."
    scp "${ROBOT_USER}@${ROBOT_SERVER}:${LOG_FILE}" "/tmp/${LPAR_NAME}_robot_failure.log"
    echo "Log retrieved to /tmp/${LPAR_NAME}_robot_failure.log"

    # You can now use 'system' command to send this to a DB2 table or message queue
    # system "CPYFRMSTMF FROMSTMF('/tmp/${LPAR_NAME}_robot_failure.log') TOMBR('/QSYS.LIB/MYLIB.LIB/ROBOTLOGS.FILE/LOG.MBR')"
else
    echo "Automation completed successfully."
fi

exit $EXIT_CODE
