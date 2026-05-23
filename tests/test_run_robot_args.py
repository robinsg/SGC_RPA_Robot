import subprocess
import pytest
import os

# Set environment variables for all tests in this module
@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("SKIP_PREREQ_CHECK", "true")
    monkeypatch.setenv("SKIP_CONN_CHECK", "true")

def run_script(args):
    """Runs run-robot.sh with the given arguments and returns the result."""
    result = subprocess.run(
        ["./run-robot.sh"] + args,
        capture_output=True,
        text=True
    )
    return result

def test_help_flag():
    result = run_script(["--help"])
    assert result.returncode == 0
    assert "Usage: ./run-robot.sh" in result.stdout
    assert "Options:" in result.stdout
    assert "-f, --yaml-file <path>" in result.stdout
    assert "-h, --host <name>" in result.stdout

def test_missing_all_args():
    result = run_script([])
    assert result.returncode == 1
    assert "Error: Both --yaml-file and --host are required." in result.stderr
    assert "Usage: ./run-robot.sh" in result.stdout

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
    assert "Error: YAML file 'non_existent.yaml' not found" in result.stderr

def test_valid_args_but_missing_env(tmp_path):
    # Use a real file for -f to get past that check
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test")

    result = run_script(["-f", str(yaml_file), "-h", "test_host"])
    # It should fail because .env.test_host is missing
    assert result.returncode == 1
    assert "Error: Configuration file '.env.test_host' not found" in result.stderr
