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

#### For Fedora/RHEL-based systems:

1.  **Install Build Dependencies and Core Tools**:
    ```bash
    sudo dnf install -y git automake autoconf ncurses-devel pkgconfig tmux nodejs npm
    sudo dnf groupinstall -y "Development Tools"
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

> **Node.js Version**: If the `nodejs` version from your package manager is too old, consider using a version manager like [nvm](https://github.com/nvm-sh/nvm) to install a more recent LTS release.

#### Install Project Dependencies
Finally, install the Node.js packages required by the robot engine:
```bash
npm install
```

### Step 2: Configure the Environment

The robot loads its configuration from environment files that are specific to the system (LPAR) you are targeting. This allows you to manage connections and credentials for multiple hosts securely.

1.  **Create an Environment File**: For each host you want to automate, create a `.env` file in the project root named `.env.<lpar_name>`. The name must be lowercase.
    - For example, to connect to `pub400.com`, you would create a file named `.env.pub400.com`.

2.  **Add Configuration Variables**: Open your new `.env` file and add the necessary variables.

    **Example for `.env.pub400.com`:**
    ```env
    # Credentials for the target system
    TN5250_USER="YOUR_USERNAME"
    TN5250_PASSWORD="YOUR_PASSWORD"

    # TN5250 Connection Settings (Optional)
    # The IP address or DNS name of the host. The script will set this automatically
    # from the LPAR name, but you can override it here if they differ.
    # TN5250_HOST="pub400.com" 

    TN5250_MAP="23"
    TN5250_SSL="on" # Use "on" or "off"
    TN5250_DEVICE_TYPE="IBM-3477-FC"
    TN5250_DEVICE_NAME="ROBOT01" # Optional: if not set, this parameter is omitted
    ```

### Step 3: Define the Automation Workflow

Create a YAML file that defines the sequence of actions the robot should perform. See `example_script.yaml` for a detailed example.

**`my_automation.yaml`:**
```yaml
- name: "Log in and Navigate"
  actions:
    - wait_for_text:
        text: "User"
        timeout: 10
    - send_text:
        text: "${TN5250_USER}" # Injects variable from .env file
    - send_key: "Enter"
    - wait_for_text:
        text: "Password"
    - send_text:
        text: "${TN5250_PASSWORD}"
        secret: true
    - send_key: "Enter"
    - wait_for_text:
        text: "IBM i Main Menu"
    - capture: "main_menu"
```

### Step 4: Run the Robot

Execute the robot using the `run-robot.sh` script. You must provide the path to your YAML script as the first argument and the LPAR name as the second argument (which tells the script which `.env` file to load).

```bash
# Make the script executable
chmod +x run-robot.sh

# Run the robot with the default example script against the 'pub400.com' LPAR
./run-robot.sh example_script.yaml pub400.com

# Run a specific automation script against a different LPAR
./run-robot.sh my_automation.yaml mylpar
```

The script will automatically start a `tmux` session, connect the `tn5250` emulator, and then hand off control to the Node.js automation engine.

## 🏃 How to Run

Simply use the provided robust bash script, passing the path to the YAML script and the LPAR name as arguments. Both are required.

```bash
chmod +x run-robot.sh
./run-robot.sh <path_to_yaml_script> <LPAR_NAME>
```

## 📁 Project Structure

- `/src/robot/`: The core RPA engine logic (TypeScript).
- `run-robot.sh`: The main entry point shell script.
- `example_script.yaml`: A sample automation workflow.
- `captures/`: (Generated) Directory containing host-specific screen captures.
- `.env`: (Untracked) Local configuration and secrets.
