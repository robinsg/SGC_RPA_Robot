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
- **LPAR-Aware Captures**: Screen captures are automatically organised into folders named after the LPAR name with ISO timestamps.

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

**Example for Direct IP (`.env.pub400.com`):**

```env
# Credentials
TN5250_USER="YOUR_USERNAME"
TN5250_PASSWORD="YOUR_PASSWORD"

# Connection Settings
TN5250_MAP="285"   # Keymap (e.g., 285 for UK, 37 for US)
TN5250_SSL="on"    # "on" or "off"
TN5250_PORT=992    # Optional: defaults to 992 for SSL, 23 for non-SSL

# Supported Terminal Types:
# 27x132: IBM-3477-FC, IBM-3477-FG, IBM-3180-2
# 24x80:  IBM-3179-2, IBM-3196-A1, IBM-5292-2, IBM-5291-1, IBM-5251-11
TN5250_DEVICE_TYPE="IBM-3477-FC"

TN5250_DEVICE_NAME="ROBOT01" # Optional: Virtual station name
```

**Example for HMC Proxy:**

```env
HMC_HOST="hmc.example.com"
HMC_USER="hmc_admin"
HMC_PWD="hmc_password"
HMC_SYSNAME="MY_POWER_SYSTEM"
HMC_LPARNAME="MY_LPAR"
HMC_SESSION_KEY="session1" # Optional
TN5250_USER="MY_USER"
TN5250_PASSWORD="MY_PASSWORD"
```

### Step 3: Define the Automation Workflow

Create a YAML file defining your steps.

**`my_automation.yaml`:**

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

| Action | Description | Key Parameters |
| :--- | :--- | :--- |
| `wait_for_text` | Waits for text to appear. Supports coordinates and block searches. | `text`, `row`, `col`, `end_row`, `end_col`, `is_message_line`, `timeout_seconds` |
| `send_text` | Sends a string of text to the terminal. | `text` |
| `send_key` | Sends a special terminal key (e.g., `Enter`, `F3`, `Reset`, `Tab`, `Page_up`, `Help`). | `key` |
| `sleep` | Pauses execution for a specified number of seconds. | `seconds` |
| `capture` | Saves a screen capture to the `captures/` directory. | `filename` |
| `press_key_if_text_present` | Sends a key only if the specified text is found on screen. | `text`, `key`, `timeout_seconds` |
| `move_cursor` | Moves the terminal cursor to the specified coordinates. | `row`, `col` |
| `search_and_move_cursor` | Finds text in a block and moves the cursor to a target column on the same row. | `text`, `row`, `col`, `end_row`, `end_col`, `target_col` |
| `search_extract_and_send` | Finds text in a block, extracts data from the same row, and sends it. | `text`, `row`, `col`, `end_row`, `end_col`, `extract_col`, `extract_length` |
| `extract_at_cursor_and_send` | Extracts text from the current cursor position and sends it. | `length` |

**Coordinates**: 5250 coordinates are 1-indexed. Rows are 1-24 (80 col) or 1-27 (132 col).
**Message Line**: Setting `is_message_line: true` in wait actions automatically targets the status line (line 24 or 27).

### Step 4: Run the Robot

Execute the robot using the `run-robot.sh` script, providing the YAML file and the LPAR name.

```bash
./run-robot.sh my_automation.yaml pub400.com
```

#### Debug Mode

To see detailed logs and automatic screen captures for every step:

```bash
LOG_LEVEL=debug ./run-robot.sh my_automation.yaml pub400.com
```

Debug captures are stored in `logs/captures/<host>/`.

## 📁 Project Structure

- `robot_py/`: The core RPA engine logic (Python 3.12+).
- `run-robot.sh`: Main entry point. Handles environment loading, connectivity checks, and tmux session management.
- `example_script.yaml`: A sample automation workflow.
- `captures/`: Host-specific screen captures.
- `logs/`: Application logs and debug captures.
- `tests/`: Automated test suite for the engine and schema validation.
- `requirements.txt`: Python dependency list.
- `.env.<lpar>`: (Untracked) LPAR-specific configuration.
