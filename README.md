# 5250 RPA Robot

A simple, robust, and YAML-driven automation framework for IBM i (TN5250) systems. Designed for users who want to automate terminal tasks without writing code.

## 🚀 Key Features

- **YAML-First Automation**: Define your terminal steps in plain, structured YAML.
- **Persistent Sessions**: Runs inside `tmux`, allowing automation to continue even if the UI is disconnected.
- **Dynamic Variable Injection**: Use `${VARIABLE_NAME}` in your YAML, loaded directly from environment variables.
- **Conditional Logic**: Simple `press_key_if_text_present` action for handling optional screens like the "Sign On Information" display.
- **Screen State Guarding**: Mandatory wait conditions ensure the host is ready. Supports precise coordinates, rectangular blocks, and automatic message line detection.
- **Interactive Dashboard**: A modern React-based web interface for visualising scripts and configuration.
- **Advanced Debugging**: Optional `LOG_LEVEL=debug` mode that automatically captures screen states for every action into a dedicated logs directory.
- **LPAR-Aware Captures**: Screen captures are automatically organised into folders named after the host name (`TN5250_HOST`) with ISO timestamps.

## 🛠 Prerequisites

The machine running this application must have the following installed:

1. **tmux**: Used for persistent terminal session management.
2. **tn5250**: The standard C-based telnet 5250 emulator.
3. **Node.js (v18+)**: To run the RPA engine and dashboard.

## ⚙️ Step-by-Step Implementation Guide

Follow these steps to configure and run your first 5250 robot automation.

### Step 1: Install Prerequisites

The machine running the robot must have the required software installed. This involves installing standard packages from your distribution's package manager and compiling the `tn5250` emulator from source.

#### For Debian/Ubuntu-based systems:

1.  **Install Build Dependencies and Core Tools**:
    ```bash
    sudo apt update
    sudo apt install -y git build-essential automake autoconf libncurses-dev pkg-config tmux nodejs npm
    ```

2.  **Build and Install `tn5250` from Source**:
    ```bash
    # Clone the official repository
    git clone https://github.com/tn5250j/tn5250.git
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

#### Install Project Dependencies
Finally, install the Node.js packages required by the robot engine:
```bash
npm install
```

### Step 2: Configure the Environment

The robot loads its configuration from environment files that are specific to the system (LPAR) you are targeting.

1.  **Create an Environment File**: Create a file named `.env.<lpar_name>` (e.g., `.env.pub400.com`) in the project root.
2.  **Add Configuration Variables**:

    **Example for `.env.pub400.com`:**
    ```env
    # Credentials for the target system
    TN5250_USER="YOUR_USERNAME"
    TN5250_PASSWORD="YOUR_PASSWORD"

    # Connection Settings
    TN5250_MAP="285"   # Keymap (e.g., 285 for UK, 37 for US)
    TN5250_SSL="on"    # "on" or "off"
    
    # Supported Terminal Types:
    # 27x132: IBM-3477-FC, IBM-3477-FG, IBM-3180-2
    # 24x80:  IBM-3179-2, IBM-3196-A1, IBM-5292-2, IBM-5291-1, IBM-5251-11
    TN5250_DEVICE_TYPE="IBM-3477-FC"
    
    TN5250_DEVICE_NAME="ROBOT01" # Optional: Virtual station name
    ```

### Step 3: Define the Automation Workflow

Create a YAML file. The engine uses a structured format where steps are defined within a `steps` array.

**`my_automation.yaml`:**
```yaml
name: "Log in and Navigate"
description: "A sample script to log in and capture the main menu"
tmux_session: "robot-session" # Optional

steps:
  - type: "wait_for_text"
    text: "User"
    timeout_seconds: 10
    description: "Wait for login screen"
    
  - type: "send_text"
    text: "${TN5250_USER}" # Injects variable from .env file
    
  - type: "send_key"
    key: "Enter"
    
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

### Step 4: Run the Robot

Execute the robot using the `run-robot.sh` script.

```bash
chmod +x run-robot.sh
./run-robot.sh my_automation.yaml pub400.com
```

#### Debug Mode
To see detailed logs and automatic screen captures for every step:
```bash
LOG_LEVEL=debug ./run-robot.sh my_automation.yaml pub400.com
```
Debug captures are stored in `logs/captures/<host>/`.

## 🖥 Web Dashboard

The project includes a React-based dashboard for previewing scripts and visualising the automation state.

```bash
# Start the dashboard in development mode
npm run dev
```
Open `http://localhost:3000` to view the interface.

## 📁 Project Structure

- `/src/robot/`: The core RPA engine logic (TypeScript).
- `/src/`: React frontend application.
- `run-robot.sh`: The main entry point shell script.
- `example_script.yaml`: A sample automation workflow.
- `captures/`: Directory containing host-specific screen captures.
- `logs/`: Application logs and debug captures.
- `.env.<lpar>`: (Untracked) LPAR-specific configuration.

