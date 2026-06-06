# Technical Context: 5250 RPA Robot

## Tech Stack

- **Python**: Version 3.12+.
- **Terminal Emulator**: `tn5250` (C-based).
- **Session Management**: `tmux`.
- **Dependency Management**: `requirements.txt` (via `pip`).

## Python Code Quality Standards (`robot_py/`)

- **Syntax**: Target Python 3.12+.
- **Formatting & Linting**: All code must pass `ruff check` and `black --check` without errors.
- **Type Hinting**: Use type hints on all new function signatures.
- **Docstrings**: Use **Google-style docstrings** with `Args:`, `Returns:`, and `Raises:` sections on all functions and classes.
- **No `mypy`**: `mypy` is not part of the project's toolchain.

## Shell Script Quality Standards (`.sh` files)

- **Linting**: All `.sh` files must pass `shellcheck` without errors.
- **Boilerplate**: Begin every shell script with `set -euo pipefail`.
- **Variable Quoting**: Always quote variables: `"$VAR"` not `$VAR`.

## Security Guidelines

- **No Hardcoded Secrets**: Never hardcode credentials, hostnames, or passwords. All secrets must be loaded from `.env.<lpar>` environment files (which are git-ignored).
- **Environment Validation**: Validate that all required environment variables are present before the robot attempts any connection.

## Testing

- **Location**: Tests reside in `tests/`, mirroring the structure of `robot_py/`.
- **Mocking**: Unit tests must mock `libtmux` using `unittest.mock` or `pytest-mock`. Never write tests that require a live terminal or real IBM i connection.
- **Test Runner**: `pytest` is the test runner.

## GitHub Actions CI Compliance

Three CI workflows run on every push and pull request. All generated code must pass these checks:

- `lint.yml`: `ruff`, `black --check`, `shellcheck`
- `test.yml`: `pytest tests/`
- `security.yml`: `gitleaks`, `safety check`
