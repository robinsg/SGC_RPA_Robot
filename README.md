# 5250 RPA Robot

A simple, robust, and YAML-driven automation framework for IBM i (TN5250) systems. Designed for users who want to automate terminal tasks without writing code.

## 🚀 Key Features

- **YAML-First Automation**: Define your terminal steps in plain, structured YAML.
- **HMC & Direct IP Support**: Connect directly via IP or through an HMC 5250 Proxy.
- **Managed Tmux Sessions**: Runs inside `tmux` for reliability, with automated session lifecycle management.
- **Dynamic Variable Injection**: Use `${VARIABLE_NAME}` or `${VAR:-default}` in your YAML, loaded from environment variables.
- **Conditional Logic**: Handle optional screens like "Sign On Information" with the `press_key_if_text_present` action.
- **Advanced Screen Interaction**: Move the cursor, search within rectangular blocks, and extract data from the screen to use in subsequent steps.
- **Screen State Guarding**: Mandatory wait conditions ensure the host is ready. Supports precise coordinates, rectangular blocks, and automatic message line detection.
- **Advanced Debugging**: Optional `LOG_LEVEL=debug` mode that captures screen states for every action into a dedicated logs directory.
- **LPAR-Aware Captures**: Screen captures are automatically organized into folders named after the LPAR name with ISO timestamps.
  - On successful sign-off, the _previous_ distinct screen is captured with "Sign off successful" appended.
  - If the robot encounters an error, the screen at the time of the error is captured and saved as `error_screen_<timestamp>.txt`.

## 🛠 Prerequisites

The machine running this application must have the following installed:

1. **tmux**: Used for persistent terminal session management.
2. **tn5250**: The standard C-based telnet 5250 emulator.
3. **Python (3.12+)**: To run the RPA engine.
4. **Python Dependencies**: `PyYAML` (listed in `requirements.txt`).

## ⚙️ Step-by-Step Implementation Guide

Follow these steps to configure and run your first 5250 robot automation.

### Step 1: Install Prerequisites

#### For Debian/Ubuntu-based systems

1. **Install Build Dependencies and Core Tools**:

   ```bash
   sudo apt update
   sudo apt install -y git build-essential automake autoconf libncurses-dev pkg-config tmux python3 python3-pip
   ```

2. **Install Python Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Build and Install `tn5250` from Source**:

   ```bash
   # Clone the official repository
   git clone https://github.com/tn5250/tn5250.git
   cd tn5250

   # Generate the configure script and build the project
   ./autogen.sh
   ./configure
   make
   sudo make install

   # Verify the installation and clean up
   which tn5250  # Should output /usr/local/bin/tn5250
   cd ..
   rm -rf tn5250
   ```

### Step 2: Configure the Environment

The robot loads its configuration from environment files specific to the system (LPAR) you are targeting. Create a file named `.env.<lpar_name>` (e.g., `.env.pub400.com`) in the project root.

#### Sensitive Data Masking

To prevent sensitive information (like passwords) from appearing in the robot's logs, you can wrap the values in the `Secret()` keyword. The robot will extract the value for use but will replace it with `********` in any log output.

**Example for Direct IP (`.env.pub400.com`):**

```env
# Credentials
TN5250_USER="YOUR_USERNAME"
TN5250_PASSWORD=Secret("YOUR_PASSWORD")

# Connection Settings
TN5250_MAP="285"   # Keymap (e.g., 285 for UK, 37 for US)
TN5250_SSL="on"    # "on" or "off" (SSL should be the default for direct IP connections. Connections via HMC are always SSL.)
TN5250_PORT=992    # Optional: defaults to 992 for SSL, 23 for non-SSL

# Supported Terminal Types:
# 27x132: IBM-3477-FC, IBM-3477-FG, IBM-3180-2
# 24x80:  IBM-3179-2, IBM-3196-A1, IBM-5292-2, IBM-5291-1, IBM-5251-11
TN5250_DEVICE_TYPE="IBM-3477-FC"

TN5250_DEVICE_NAME="ROBOT01" # Optional: Virtual station name
```

#### Minimum Set of Permissions

To ensure the robot operates with appropriate security, the IBM i user profile it uses should adhere to the principle of least privilege. This means granting only the necessary permissions for the robot to perform its automated tasks.

- The IBM i user profile should have `*USER` class.
- Limit capabilities with `LMTCPB(*YES)` if the robot only needs to run specific commands.
- Use specific `GRTOBJAUT` commands to grant access only to the libraries, files, and programs required for automation.
- Avoid `*ALLOBJ` or `*SECADM` special authorities unless strictly necessary.

````

**Example for HMC Proxy:**

```env
HMC_HOST="hmc.example.com"
HMC_USER="hmc_admin"
HMC_PWD=Secret("hmc_password")
HMC_SYSNAME="MY_POWER_SYSTEM"
HMC_LPARNAME="MY_LPAR"
HMC_SESSION_KEY=Secret("my_session_key")
TN5250_USER="MY_USER"
TN5250_PASSWORD=Secret("MY_PASSWORD")
````

### Step 3: Define the Automation Workflow

Create a YAML file defining your steps. All automation scripts should be stored in the `yaml_scripts/` directory.

**`yaml_scripts/my_automation.yaml`:**

```yaml
name: "Log in and Navigate"
description: "A sample script to log in and capture the main menu"

steps:
  - type: "wait_for_text"
    text: "User"
    timeout_seconds: 10
    description: "Wait for login screen"

  - type: "send_text"
    text: "${TN5250_USER}" # Injects variable from .env file

  - type: "send_key"
    key: "Tab"

  - type: "wait_for_text"
    text: "Password"

  - type: "send_text"
    text: "${TN5250_PASSWORD}"

  - type: "send_key"
    key: "Enter"

  - type: "press_key_if_text_present"
    text: "Sign On Information"
    key: "Enter"
    description: "Skip optional info screen"

  - type: "wait_for_text"
    text: "IBM i Main Menu"
    row: 1
    col: 33

  - type: "capture"
    filename: "main_menu"
```

### Supported Actions

| Action                       | Description                                                                                                                                                            | Key Parameters                                                                                                                              |
| :--------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `wait_for_text`              | Waits for text to appear. Supports coordinates and block searches.                                                                                                     | `text`, `row`, `col`, `end_row`, `end_col`, `is_message_line`, `timeout_seconds`                                                            |
| `send_text`                  | Sends a string of text to the terminal.                                                                                                                                | `text`                                                                                                                                      |
| `send_key`                   | Sends a special terminal key (e.g., `Enter`, `F3`, `Reset`, `Tab`, `Page_up`, `Help`).                                                                                 | `key`                                                                                                                                       |
| `sleep`                      | Pauses execution for a specified number of seconds.                                                                                                                    | `seconds`                                                                                                                                   |
| `capture`                    | Saves a screen capture to the `captures/` directory. If the final screen is "Sign On", the previous distinct screen is captured and tagged with "Sign off successful". | `filename`                                                                                                                                  |
| `press_key_if_text_present`  | Sends a key only if the specified text is found on screen.                                                                                                             | `text`, `key`, `timeout_seconds`                                                                                                            |
| `move_cursor`                | Moves the terminal cursor to the specified coordinates.                                                                                                                | `row`, `col`                                                                                                                                |
| `search_and_move_cursor`     | Finds text in a block and moves the cursor to a target column on the same row.                                                                                         | `text`, `row`, `col`, `end_row`, `end_col`, `target_col`                                                                                    |
| `search_extract_and_send`    | Finds text in a block, extracts data from the same row, and sends it.                                                                                                  | `text`, `row`, `col`, `end_row`, `end_col`, `extract_col`, `extract_length`                                                                 |
| `extract_at_cursor_and_send` | Extracts text from the current cursor position and sends it.                                                                                                           | `length`                                                                                                                                    |
| `search_and_compare`         | Searches for text and executes conditional steps. Supports single/multiple search strings and Line, Positional, or Block checks.                                       | `text`, `row`, `col`, `end_row`, `end_col`, `is_message_line`, `if_true`, `if_false`                                                        |
| `compare`                    | Extracts text from the screen and compares it against an expected value. Executes conditional steps based on the result. Supports absolute and relative extraction.    | `expected`, `operator`, `row`, `col`, `length`, `search_text`, `end_row`, `end_col`, `extract_col`, `extract_length`, `if_true`, `if_false` |
| `terminate`                  | Immediately stops the robot's execution. Useful within `if_true` or `if_false` blocks.                                                                                 | `reason`                                                                                                                                    |

**Coordinates**: 5250 coordinates are 1-indexed. Rows are 1-24 (80 col) or 1-27 (132 col).
**Message Line**: Setting `is_message_line: true` in wait actions automatically targets the status line (line 24 or 27).

## Examples

### Compare Action

#### Absolute Extraction

Extract a value from a fixed position (Row 7, Col 35) and compare it against a literal value.

```yaml
- type: "compare"
  description: "Check if system security level is 40"
  row: 7
  col: 35
  length: 2
  expected: "40"
  operator: "EQ"
  if_true:
    - type: "send_key"
      key: "Enter"
  if_false:
    - type: "terminate"
      reason: "Security level is not 40"
```

#### Relative Extraction

Find a row containing "QSECURITY" and extract the value at Column 35. Compare it against an environment variable.

```yaml
- type: "compare"
  description: "Verify QSECURITY system value using relative search"
  search_text: "QSECURITY"
  row: 1
  col: 1
  end_row: 20
  end_col: 80
  extract_col: 35
  extract_length: 2
  expected: "{{SEC_QSECURITY}}"
  operator: "EQ"
  if_false:
    - type: "terminate"
      reason: "System security level does not match expected value"
```

### Sensitive Data Masking

Using the `Secret()` keyword in your `.env` file ensures that passwords and other sensitive values are automatically masked in the robot's logs.

**`.env.pub400.com`**:

```env
MY_APP_SECRET=Secret("very-secret-pwd")
```

**`yaml_scripts/my_automation.yaml`**:

```yaml
- type: "send_text"
  text: "${MY_APP_SECRET}"
  description:
    "Sending secret password" # The log will show: Sending secret token
    # and any echoed value in debug logs will be masked.
```

When the robot runs, any appearance of `"very-secret-pwd"` in the logs (both console and file) will be replaced with `********`.

### Step 4: Run the Robot

Execute the robot using the `run-robot.sh` script, providing the YAML file and the LPAR name via named arguments.

```bash
./run-robot.sh --yaml-file my_automation.yaml --host pub400.com
```

#### Custom Environment Files

By default, the robot looks for a file named `.env.<host>` (e.g., `.env.pub400.com`). You can specify a custom environment file using the `-e` or `--env` flag.

**Requirements for custom environment files:**

- The filename **must** start with `.env` (e.g., `.env.production`, `.env.test.local`) to ensure it is ignored by git.
- The file must contain valid `KEY=VALUE` pairs.

### Environment Security

To further secure the robot's execution environment, follow these recommendations:

1. **Run under a Dedicated Service Account**:

   It is recommended to create a dedicated, unprivileged service account for running the robot. This limits the potential damage if the robot or its environment is compromised.

   ```bash
   sudo useradd --system --no-create-home --shell /bin/false robot_user
   sudo mkdir /opt/SGC_RPA_Robot
   sudo chown robot_user:robot_user /opt/SGC_RPA_Robot
   # Example: To run the robot as this user (assuming your script is in /opt/SGC_RPA_Robot)
   # sudo -u robot_user /opt/robot_user/run-robot.sh ...
   ```

2. **Set Strict File Permissions on Project Directory**:

   Restrict access to the robot's project directory to prevent unauthorized reading or modification.

   ```bash
   chmod 700 /opt/SGC_RPA_Robot # Adjust path as necessary
   ```

3. **Ensure `.env` Files are Secure**:

   Environment files containing sensitive information should have very strict permissions.

   ```bash
   chmod 600 /opt/SGC_RPA_Robot/.env.<lpar_name> # Adjust path and filename
   ```

#### Transport Security: Certificate Checking with `tn5250`

To prevent Man-in-the-Middle (MITM) attacks, it is highly recommended to use certificate checking with `tn5250` when connecting via SSL. This ensures that the robot is communicating with a trusted IBM i host.

**Importing Self-Signed CA and Server Certificates**:

If your IBM i system uses self-signed certificates or certificates issued by an internal Certificate Authority (CA), you need to import these certificates into the system's trust store where `tn5250` can access them. The exact method depends on your operating system, but typically involves:

1.  **Obtain the Certificates**:
    Get the CA certificate (if applicable) and the server certificate from your IBM i system administrator.

2.  **Convert to PEM Format (if necessary)**:
    `tn5250` typically expects certificates in PEM format. If your certificates are in DER or PFX format, you may need to convert them using `openssl`.

    ```bash
    # Example: Convert DER to PEM
    openssl x509 -inform DER -in certificate.cer -out certificate.pem
    ```

3.  **Place Certificates in a Trusted Location**:
    Common locations include `/etc/ssl/certs/` or a custom directory. Ensure the `tn5250` client is configured to look in these locations.

4.  **Configure `tn5250` for Certificate Checking**:
    You might need to set environment variables or `tn5250` configuration options to enable certificate validation. Consult the `tn5250` documentation for specifics, but generally, `tn5250` uses the system's default certificate store or paths specified by `SSL_CERT_FILE` or `SSL_CERT_DIR`.

    ```bash
    # Example: Set environment variables before running the robot
    export SSL_CERT_FILE="/path/to/your/ca-bundle.pem"
    export TN5250_SSL_VERIFY_SERVER_CERT=on
    ./run-robot.sh ...
    ```

    Ensure that `TN5250_SSL="on"` is always set in your `.env` file when using certificate checking.

```bash
./run-robot.sh -f my_automation.yaml -h pub400.com -e .env.custom
```

### CI/CD with Self-Hosted GitHub Runner

This project supports execution on self-hosted GitHub runners for secure, internal IBM i environments.

#### Configuration

To maintain security:

- Environment-specific details are kept outside of version control in a JSON configuration file on the runner.
- Arguments passed to run_robot.sh are masked on the runner.
- Any variables in the .env.<lpar_name> files using Secret() are masked on the runner.

1. **Location**: `/home/github-runner/customer_config.json`
2. **Format**:

   ```json
   {
     "a-hmc": {
       "yaml_file": "ops_hmc.yaml",
       "host": "<lpar_name>",
       "env_file": ".env.<lpar_name>_hmc",
       "log_level": "debug"
     },
     "t-direct": {
       "yaml_file": "verify_system_integrity.yaml",
       "host": "<lpar_name>",
       "env_file": ".env.<lpar_name>_direct",
       "log_level": "info"
     }
   }
   ```

#### Workflow

The workflow `.github/workflows/self-hosted-tests.yml` uses a matrix strategy to loop through generic keys (e.g., `a-hmc`, `t-direct`). These keys are passed to `tests/run_github_robot.sh`, which resolves the actual LPAR details from the local JSON file.

### Error Captures

If the robot script encounters an error (e.g., a timeout waiting for text), the screen content at the point of failure is automatically captured to `captures/<host>/error_screen_<timestamp>.txt`.

#### Debug Mode

To see detailed logs and automatic screen captures for every step:

```bash
LOG_LEVEL=debug ./run-robot.sh -f my_automation.yaml -h pub400.com
```

Debug captures are stored in `logs/captures/<host>/`.

## 📁 Project Structure

- `robot_py/`: The core RPA engine logic (Python 3.12+).
- `run-robot.sh`: Main entry point. Handles environment loading, connectivity checks, and tmux session management.
- `yaml_scripts/`: Directory containing all YAML automation scripts and common components.
- `captures/`: Host-specific screen captures.
- `logs/`: Application logs and debug captures.
- `tests/`: Automated test suite for the engine and schema validation, including the GitHub Actions orchestrator.
- `requirements.txt`: Python dependency list.
- `.env.<lpar>`: (Untracked) LPAR-specific configuration.
