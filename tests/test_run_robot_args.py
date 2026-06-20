import subprocess
import os


def run_script(args):
    """Runs run-robot.sh with the given arguments and returns the result."""
    result = subprocess.run(["./run-robot.sh"] + args, capture_output=True, text=True)
    return result


def test_help_flag():
    result = run_script(["--help"])
    assert result.returncode == 0
    assert "Usage: ./run-robot.sh [OPTIONS]" in result.stdout
    assert "Options:" in result.stdout
    assert "-f, --yaml-file <path>" in result.stdout
    assert "-h, --host <name>" in result.stdout


def test_missing_all_args():
    result = run_script([])
    assert result.returncode == 1
    assert "Error: Both --yaml-file and --host are required." in result.stderr
    assert "Usage: ./run-robot.sh [OPTIONS]" in result.stdout


def test_missing_host_arg():
    result = run_script(["-f", "example_script.yaml"])
    assert result.returncode == 1
    assert "Error: Both --yaml-file and --host are required." in result.stderr


def test_missing_yaml_arg():
    result = run_script(["-h", "test_host"])
    assert result.returncode == 1
    assert "Error: Both --yaml-file and --host are required." in result.stderr


def test_unknown_argument():
    result = run_script(["--unknown"])
    assert result.returncode == 1
    assert "Error: Unknown or positional argument: --unknown" in result.stderr


def test_positional_argument():
    result = run_script(["example_script.yaml", "test_host"])
    assert result.returncode == 1
    assert "Error: Unknown or positional argument: example_script.yaml" in result.stderr


def test_missing_value_for_flag():
    result = run_script(["-f"])
    assert result.returncode == 1
    assert "Error: Argument for -f is missing" in result.stderr


def test_flag_followed_by_another_flag():
    result = run_script(["-f", "-h", "test_host"])
    assert result.returncode == 1
    assert "Error: Argument for -f is missing" in result.stderr


def test_yaml_file_not_found():
    # It should pass argument parsing but fail at file check
    result = run_script(["-f", "non_existent.yaml", "-h", "test_host"])
    assert result.returncode == 1
    assert (
        "Error: YAML file 'non_existent.yaml' not found (checked current directory and yaml_scripts/)."
        in result.stderr
    )


def test_yaml_file_in_yaml_scripts(tmp_path):
    # Create yaml_scripts directory and a test file
    yaml_scripts_dir = tmp_path / "yaml_scripts"
    yaml_scripts_dir.mkdir()
    yaml_file = yaml_scripts_dir / "test_in_scripts.yaml"
    yaml_file.write_text("name: test_in_scripts")

    # Change CWD to tmp_path to run the script
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # We need to copy run-robot.sh to tmp_path or point to it
        # Pointing to it is easier if we use absolute path
        script_path = os.path.join(original_cwd, "run-robot.sh")

        # We also need an .env file for the host check to get far enough
        env_file = tmp_path / ".env.test_host"
        env_file.write_text("TN5250_USER=test\nTN5250_PASSWORD=test")

        result = subprocess.run(
            [script_path, "-f", "test_in_scripts.yaml", "-h", "test_host"],
            capture_output=True,
            text=True,
        )

        # It should NOT fail with "file not found"
        assert "Error: YAML file 'test_in_scripts.yaml' not found" not in result.stderr
        # It might fail later due to missing tmux/tn5250 in the environment, but that's fine
    finally:
        os.chdir(original_cwd)


def test_valid_args_but_missing_env(tmp_path):
    # Use a real file for -f to get past that check
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test")

    result = run_script(["-f", str(yaml_file), "-h", "test_host"])
    # It should fail because .env.test_host is missing
    assert result.returncode == 1
    assert (
        "Error: Configuration file '.env.test_host' not found" in result.stdout
        or "Error: Configuration file '.env.test_host' not found" in result.stderr
    )


def test_env_arg_invalid_name():
    result = run_script(
        ["-f", "example_script.yaml", "-h", "test_host", "-e", "custom.env"]
    )
    assert result.returncode == 1
    assert "Error: Environment file name must start with '.env'" in result.stderr


def test_env_arg_not_found():
    result = run_script(
        ["-f", "example_script.yaml", "-h", "test_host", "-e", ".env.notfound"]
    )
    assert result.returncode == 1
    assert (
        "Error: Configuration file '.env.notfound' not found" in result.stdout
        or "Error: Configuration file '.env.notfound' not found" in result.stderr
    )


def test_env_arg_success(tmp_path):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test")
    env_file = tmp_path / ".env.custom"
    env_file.write_text("TN5250_USER=test\nTN5250_PASSWORD=test")

    # Change CWD to tmp_path to run the script
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        script_path = os.path.join(original_cwd, "run-robot.sh")
        # We use a non-existent host but provide a valid env file.
        # It should try to load .env.custom instead of .env.wronghost
        result = subprocess.run(
            [script_path, "-f", "test.yaml", "-h", "wronghost", "-e", ".env.custom"],
            capture_output=True,
            text=True,
        )
        # It should NOT fail with "Configuration file '.env.wronghost' not found"
        assert (
            "Error: Configuration file '.env.wronghost' not found" not in result.stdout
        )
        assert "Loading environment variables" in result.stdout
        # It should NOT show the path by default
        assert ".env.custom" not in result.stdout
    finally:
        os.chdir(original_cwd)


def test_debug_log_level_masked(tmp_path):
    """Verify masking when GITHUB_ACTIONS=true and LOG_LEVEL=debug."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\nsteps: []")
    env_file = tmp_path / ".env.debug"
    # Provide all required vars to avoid engine validation errors
    env_file.write_text(
        "TN5250_USER=test\n"
        "TN5250_PASSWORD=test\n"
        "LOG_LEVEL=debug\n"
        "HMC_HOST=hmchost\n"
        "HMC_USER=user\n"
        "HMC_PWD=pwd\n"
        "HMC_SYSNAME=sys\n"
        "HMC_LPARNAME=lpar\n"
        "HMC_SESSION_KEY=key"
    )

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        script_path = os.path.join(original_cwd, "run-robot.sh")
        result = subprocess.run(
            [
                script_path,
                "-f",
                "test.yaml",
                "-h",
                "debughost",
                "-e",
                ".env.debug",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "LOG_LEVEL": "debug",
                "GITHUB_ACTIONS": "true",
            },
        )
        # Verify masking of env file, host, and port
        assert "Loading environment variables from [MASKED_ENV_FILE]" in result.stdout
        assert "Dry run mode enabled. Skipping connectivity check." in result.stdout
        # Verify HMC host masking (as it was set in .env.debug)
        assert "hmchost" not in result.stdout
        # Verify debughost masking
        assert "debughost" not in result.stdout
        # In dry run mode, [MASKED_HOST] appears in the Python parameters log (stderr)
        assert "[MASKED_HOST]" in result.stderr
    finally:
        os.chdir(original_cwd)


def test_debug_log_level_unmasked(tmp_path):
    """Verify no masking when GITHUB_ACTIONS=false and LOG_LEVEL=debug."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\nsteps: []")
    env_file = tmp_path / ".env.debug"
    env_file.write_text("TN5250_USER=test\nTN5250_PASSWORD=test\nLOG_LEVEL=debug")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        script_path = os.path.join(original_cwd, "run-robot.sh")
        result = subprocess.run(
            [
                script_path,
                "-f",
                "test.yaml",
                "-h",
                "debughost",
                "-e",
                ".env.debug",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "LOG_LEVEL": "debug",
                "GITHUB_ACTIONS": "false",
            },
        )
        # Verify NO masking
        assert "Loading environment variables from .env.debug" in result.stdout
        assert "Dry run mode enabled. Skipping connectivity check." in result.stdout
        assert "debughost" in result.stderr
    finally:
        os.chdir(original_cwd)
