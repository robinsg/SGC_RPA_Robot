# AI Development Guidelines

## Project Context

This project is an RPA (Robotic Process Automation) engine for IBM i (AS/400) systems. It bridges modern AI capabilities with legacy green-screen terminals via `tmux` and `tn5250`.

**Language Preference:** All responses and generated documentation must be in UK English.

## YAML Scripting & Prompting Guidelines

- **Variable Injection:** When generating automation scripts, use the back-reference syntax `${VAR_NAME}` for sensitive credentials.
- **Description:** Always include a `description` for each YAML step to explain the "why" to the user.
- **Coordinate System:** 5250 coordinates are 1-indexed (Row 1-24/27, Col 1-80/132). Always verify coordinates against standard IBM i layouts.
- **Valid Actions:** Only use supported actions:
  - `wait_for_text`: Waits for text to appear (optionally at specific coordinates).
  - `send_text`: Sends a string of text. Supports an optional `key` (string or list of strings) to be sent after the text with a 0.25s delay.
  - `send_key`: Sends a special key (e.g., `Enter`, `F3`).
  - `sleep`: Pauses for a specified number of seconds.
  - `capture`: Saves a screen capture to a file.
  - `press_key_if_text_present`: Conditional key press based on text presence.
  - `move_cursor`: Moves the cursor to (row, col).
  - `search_and_move_cursor`: Finds text in a block and moves the cursor to a target column on the same row.
  - `search_extract_and_send`: Finds text in a block, extracts text from a specific column on the same row, and sends it.
  - `extract_at_cursor_and_send`: Extracts text from the current cursor position and sends it.
- **State Guarding (Terminal Reliability):** Always prioritise robust screen state detection. Never assume a screen has loaded without a matching `wait_for_text` or similar guard.
- **Targeting:** Prefer rectangular block searches (`row`, `col`, `end_row`, `end_col`) over global searches when targeting specific fields to reduce false positives.
- **Conditional Logic:** Use `press_key_if_text_present` for optional screens (e.g., Sign On Info, Password Expiry warnings) rather than hard branching.
- **Mental Model:** Treat different screens as objects (Page Object Model). The YAML steps should represent a clear transition from one screen to the next.
- **YAML Script files**: YAML script files to be located in `yaml_scripts/`.

## Python Engine Development

- **Terminal Emulation (`env.TERM`):**
  - Validate that `env.TERM` uses one of the following supported types:
    - **27x132:** `IBM-3477-FC`, `IBM-3477-FG`, `IBM-3180-2`.
    - **24x80:** `IBM-3179-2`, `IBM-3196-A1`, `IBM-5292-2`, `IBM-5291-1`, `IBM-5251-11`.
  - Ensure the `tmux` buffer is correctly sized to match the terminal type (either 24x80 or 27x132) before starting the `tn5250` session.
- **Schema Enforcement:** The Python engine uses `dataclasses` and manual validation in `robot_py/schema.py`. The engine must remain generic and driven by the YAML schema.
- **Tmux Interactions:** Only use `send-keys` and `capture-pane`. Avoid complex tmux scripting that makes debugging difficult.
- **Tmux Session Safety:** Always check if the tmux session defined in the YAML exists before attempting to send keys or capture content.
- **Error Handling:** When a terminal error occurs (e.g., timeout, missing session), include the current tmux pane content in the error message or log.
- **Environment Isolation:** Screens vary by LPAR. Use `TN5250_HOST` to segment configuration.
- **Capture Pathing:** Stick to the standard `/captures/{host}/{filename}_{timestamp}.txt` format.

## Vision and Capture Analysis

- If using multimodal models to analyse screen captures, ensure the model understands the fixed-width nature of 5250 terminals (typically 24x80 or 27x132).
- Remind the model that "Sign On" screens often have hidden input fields for passwords.

## Project Structure — Do Not Change

The repo structure is intentional. Do not reorganise it.

- `robot_py/` — the Python RPA engine. All Python code lives here.
- `run-robot.sh` — the main entry point. Do not rename or relocate it.
- `ts_backup/` — archived TypeScript/React code. **Do not edit, lint, or generate code in this directory.**
- `requirements.txt` — dependency management. Do not migrate to Poetry or pyproject.toml-based dependency management.
- YAML files in the root are user-facing automation scripts, not config for the engine.

**Never suggest or implement:**

- Moving Python code to a `src/` layout
- Migrating from `requirements.txt` to Poetry
- Refactoring `run-robot.sh` into a Python entry point

## Code Quality Standards

When generating or modifying Python code in `robot_py/`, always conform to the following:

### Formatting & Linting

- Target **Python 3.12+** syntax.
- All code must pass `ruff check` and `black` formatting without errors.
- Do not introduce `mypy` strict type checking — it is not used in this project.
- Use type hints on all new function signatures, but do not add `mypy` to CI or tooling.

### Docstrings

- Use **Google-style docstrings** on all functions and classes.
- Always include `Args:`, `Returns:`, and `Raises:` sections where applicable.

Example:

```python
def load_script(path: str) -> dict:
    """Load and validate a YAML automation script.

    Args:
        path: Absolute or relative path to the YAML script file.

    Returns:
        A dictionary representing the parsed script.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the YAML is invalid or missing required fields.
    """
```

### Shell Scripts

- `run-robot.sh` and any other `.sh` files must pass `shellcheck` without errors.
- Use `set -euo pipefail` at the top of all shell scripts.
- Always quote variables: use `"$VAR"` not `$VAR`.

### Security

- Never hardcode credentials, hostnames, or passwords in Python or shell files.
- All credentials must be loaded from environment variables (`.env.<lpar>` files, excluded from git).
- Validate that required environment variables are present before the robot starts.

### Testing

- Tests live in `tests/` and mirror the structure of `robot_py/`.
- Unit tests must mock external processes or tmux interactions using `unittest.mock`, `pytest-mock`, or dry-run mode. Do not write tests that require a live terminal session.
- Use `pytest` as the test runner.

Example test structure:

```python
from unittest.mock import MagicMock, patch

def test_send_key_enters_command():
    with patch("robot_py.engine.get_tmux_session") as mock_session:
        mock_pane = MagicMock()
        mock_session.return_value.attached_window.attached_pane = mock_pane
        # call function under test
        mock_pane.send_keys.assert_called_once_with("Enter")
```

## GitHub Actions CI

The following workflows exist in `.github/workflows/`. Do not remove or bypass them:

- `lint.yml` — runs `ruff`, `black --check`, and `shellcheck` on push/PR.
- `test.yml` — runs `pytest tests/` on push/PR.
- `security.yml` — runs `gitleaks` (secrets scan) and `safety check` (dependency vulnerabilities).

When generating code, ensure it will pass all three workflows before suggesting a commit.
