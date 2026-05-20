# Operational Guidelines for 5250 RPA Robot

## Core Principles

- **Terminal Reliability**: Always prioritise robust screen state detection. Never assume a screen has loaded without a matching `wait_for_text` or similar guard.
- **YAML First**: All automation logic must reside in YAML configuration. The Python engine must remain generic and driven by the schema.
- **YAML Scripts**: All YAML scripts to be located in director yaml_scripts.
- **Environment Isolation**: Screens vary by LPAR. Use `TN5250_HOST` to segment configuration and output (like captures).

## Technical Implementation Rules

- **Schema Enforcement**: Any new automation action MUST start with an update to `robot_py/schema.py` using dataclasses.
- **Error Handling**: When a terminal error occurs (timeout, missing session), include the current tmux pane content in the error message or log.
- **Capture Pathing**: Stick to the standard `/captures/{host}/{filename}_{timestamp}.txt` format.
- **Tmux Interaction**: Only use `send-keys` and `capture-pane`. Avoid complex tmux scripting that makes debugging difficult.

## Design Patterns

- **Page Object Model (Mental)**: Treat different screens as objects. Though logic is in YAML, the YAML steps should be structured to represent a clear transition from one screen to the next.
- **Conditional Handling**: Use `press_key_if_text_present` for optional screens (Sign On Info, Password Expiry warnings) rather than hard branching.

## Project Structure — Do Not Change

The repo structure is intentional. **Never reorganise it.**

- `robot_py/` — all Python source code. Do not move files out of here.
- `run-robot.sh` — the main entry point shell script. Do not rename or replace it.
- `requirements.txt` — manages Python dependencies. Do not migrate to Poetry or any pyproject.toml-based dependency tool.

**Never propose or implement:**

- Restructuring Python code into a `src/` layout
- Migrating from `requirements.txt` to Poetry
- Converting `run-robot.sh` to a Python entry point
- Touching anything in `ts_backup/`

## Code Quality Standards

### Python

- Target Python 3.12+ syntax.
- All Python must pass `ruff check` and `black --check` without errors.
- Use type hints on all new function signatures.
- Do not add `mypy` — it is not part of this project's toolchain.
- Use **Google-style docstrings** with `Args:`, `Returns:`, and `Raises:` sections on all functions and classes.

### Shell Scripts

- All `.sh` files must pass `shellcheck` without errors.
- Begin every shell script with `set -euo pipefail`.
- Always quote variables: `"$VAR"` not `$VAR`.

### Security

- Never hardcode credentials, hostnames, or passwords.
- All secrets must be loaded from `.env.<lpar>` environment files (which are git-ignored).
- Validate that all required environment variables are present before the robot attempts any connection.

### Testing

- Tests live in `tests/`, mirroring the structure of `robot_py/`.
- Because this project uses live `libtmux` sessions, unit tests must mock `libtmux` using `unittest.mock` or `pytest-mock`. Never write tests that require a live terminal or real IBM i connection.
- Use `pytest` as the test runner.

## GitHub Actions Compliance

Three CI workflows run on every push and pull request:

- `lint.yml` — `ruff`, `black --check`, `shellcheck`
- `test.yml` — `pytest tests/`
- `security.yml` — `gitleaks`, `safety check`

All generated code must pass these checks. Do not suggest commits or PRs that would fail CI.
