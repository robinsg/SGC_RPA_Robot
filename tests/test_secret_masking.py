import os
import logging
from robot_py.logger import CustomFormatter
from robot_py.cli import load_env_file
import pytest

def test_secret_parsing(tmp_path):
    env_file = tmp_path / ".env.test"
    env_file.write_text('MY_SECRET=Secret("password123")\nOTHER_VAR=Secret(myval)\nNORMAL_VAR=normal')

    # Clean environment for test
    if "ROBOT_SENSITIVE_VARS" in os.environ:
        del os.environ["ROBOT_SENSITIVE_VARS"]

    load_env_file(str(env_file))

    assert os.environ.get("MY_SECRET") == "password123"
    assert os.environ.get("OTHER_VAR") == "myval"
    assert os.environ.get("NORMAL_VAR") == "normal"

    sensitive_vars = os.environ.get("ROBOT_SENSITIVE_VARS", "").split(",")
    assert "MY_SECRET" in sensitive_vars
    assert "OTHER_VAR" in sensitive_vars
    assert "NORMAL_VAR" not in sensitive_vars

def test_masking_logic(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "password123")
    monkeypatch.setenv("ROBOT_SENSITIVE_VARS", "MY_SECRET")
    monkeypatch.setenv("TN5250_PASSWORD", "hardcoded_secret")

    formatter = CustomFormatter()

    # Test custom secret masking
    record = logging.LogRecord("robot", logging.INFO, "test.py", 10, "Value is password123", None, None)
    formatted = formatter.format(record)
    assert "password123" not in formatted
    assert "********" in formatted

    # Test hardcoded secret masking (backward compatibility)
    record2 = logging.LogRecord("robot", logging.INFO, "test.py", 10, "Password is hardcoded_secret", None, None)
    formatted2 = formatter.format(record2)
    assert "hardcoded_secret" not in formatted2
    assert "********" in formatted2

    # Test non-sensitive var NOT masked
    monkeypatch.setenv("NORMAL_VAR", "normal_value")
    record3 = logging.LogRecord("robot", logging.INFO, "test.py", 10, "Value is normal_value", None, None)
    formatted3 = formatter.format(record3)
    assert "normal_value" in formatted3
    assert "********" not in formatted3
