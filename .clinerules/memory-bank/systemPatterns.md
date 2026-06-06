# System Patterns: 5250 RPA Robot

## Architecture & Core Principles

- **YAML-First Automation**: All automation logic resides in YAML configuration files. The Python engine remains generic, driven by a well-defined schema (`robot_py/schema.py`).
- **Terminal Reliability**: Robust screen state detection is paramount. `wait_for_text` or similar guards are mandatory before assuming a screen has loaded.
- **Environment Isolation**: Configurations and outputs are segmented by LPAR using `TN5250_HOST` to account for screen variations.
- **Schema Enforcement**: All new automation actions must begin with an update to `robot_py/schema.py` using dataclasses.

## Design Patterns

- **Page Object Model (Mental)**: Different 5250 screens are treated as objects. YAML steps are structured to represent clear transitions between screens.
- **Conditional Handling**: `press_key_if_text_present` is preferred for optional screens (e.g., Sign On Info, Password Expiry warnings) over complex branching logic.

## Technical Implementation Rules

- **Tmux Interaction**: Only `send-keys` and `capture-pane` are permitted for tmux interaction. Complex tmux scripting is to be avoided.
- **Error Handling**: Terminal errors (timeout, missing session) must include the current tmux pane content in the error message or log.
- **Capture Pathing**: Screen captures follow a standard format: `/captures/{host}/{filename}_{timestamp}.txt`.
- **5250 Coordinates**: Coordinates are 1-indexed (Row 1-24/27, Col 1-80/132). Always verify against standard IBM i layouts.

## Project Structure (Immutable)

The repository structure is intentional and **must not be reorganized**.

- `robot_py/`: All Python source code resides here.
- `run-robot.sh`: The main entry point shell script.
- `requirements.txt`: Manages Python dependencies (no migration to Poetry).
- `yaml_scripts/`: All YAML automation scripts are located here.
- `ts_backup/`: Archived TypeScript/React code. **Never edit or generate code here.**
