# 5250 RPA Robot

A simple, robust, and YAML-driven automation framework for IBM i (TN5250) systems. Designed for users who want to automate terminal tasks without writing code.

## 🚀 Key Features

- **YAML-First Automation**: Define your terminal steps in plain YAML.
- **Persistent Sessions**: Runs inside `tmux`, allowing automation to continue even if the UI is disconnected.
- **Dynamic Variable Injection**: Use `${VARIABLE_NAME}` in your YAML, loaded directly from environment variables.
- **Conditional Logic**: Simple `press_key_if_text_present` action for handling optional screens like the "Sign On Information" display.
- **Screen State Guarding**: Mandatory wait conditions ensure the host is ready. Supports precise coordinates, rectangular blocks, and automatic message line detection.
- **Auto-Provisioning**: The shell wrapper automatically launches the `tn5250` session if it's not already running.
- **LPAR-Aware Captures**: Screen captures are automatically organized into folders named after the host name (`TN5250_HOST`) with ISO timestamps.

## 🛠 Prerequisites

The machine running this application must have the following installed:

1. **tmux**: Used for persistent terminal session management.
2. **tn5250**: The standard C-based telnet 5250 emulator.
3. **Node.js**: To run the RPA engine.

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure your settings:

```env
# RPA Credentials
USERNAME="MYUSER"
PASSWORD="MYPASSWORD"

# TN5250 Configuration
TN5250_HOST="as400.company.com"
TN5250_MAP="23"
TN5250_SSL="on"
TN5250_DEVICE_TYPE="IBM-3477-FC"
TN5250_DEVICE_NAME="ROBOT01"
```

## 🏃 How to Run

Simply use the provided robust bash script:

```bash
chmod +x run-robot.sh
./run-robot.sh your_script.yaml
```

If no script is provided, it defaults to `example_script.yaml`.

## 📁 Project Structure

- `/src/robot/`: The core RPA engine logic (TypeScript).
- `run-robot.sh`: The main entry point shell script.
- `example_script.yaml`: A sample automation workflow.
- `captures/`: (Generated) Directory containing host-specific screen captures.
- `.env`: (Untracked) Local configuration and secrets.
