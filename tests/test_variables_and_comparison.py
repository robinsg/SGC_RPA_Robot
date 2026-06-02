import pytest
import os
from unittest.mock import patch, MagicMock
from robot_py.engine import RobotEngine
from robot_py.schema import (
    SearchExtractAndSendAction, ExtractAtCursorAndSendAction, CompareAction, SendTextAction
)

@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        return RobotEngine(str(yaml_file))

def test_variable_storage_and_substitution(engine):
    # Test SearchExtractAndSendAction with store_as
    action1 = SearchExtractAndSendAction(
        type="search_extract_and_send",
        text="ID:",
        row=1, col=1, end_row=5, end_col=80,
        extract_col=5, extract_length=3,
        store_as="MY_ID"
    )
    # Test substitution in a subsequent action
    action2 = SendTextAction(
        type="send_text",
        text="Found ID: {{MY_ID}}"
    )
    engine.script.steps = [action1, action2]

    pane_content = "Line 1\nID: 12345\nLine 3"

    with patch.object(engine, "check_session_exists", return_value=True),          patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)),          patch.object(engine, "run_tmux") as mock_run,          patch.object(engine, "capture_pane", return_value=pane_content):

        engine.run()

        # Verify MY_ID was stored
        assert engine.runtime_variables["MY_ID"] == "123"

        # Verify substitution in action2
        mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "Found ID: 123"])

def test_compare_action_numeric(engine):
    # Test numeric GE comparison
    action = CompareAction(
        type="compare",
        row=1, col=5, length=2,
        operator="GE",
        expected="40",
        store_as="SEC_LEVEL"
    )
    engine.script.steps = [action]

    pane_content = "VAL 50 remainder" # Position 1,5 has "50"

    with patch.object(engine, "check_session_exists", return_value=True),          patch.object(engine, "capture_pane", return_value=pane_content),          patch("robot_py.engine.logger.info") as mock_log_info:

         engine.run()

         assert engine.runtime_variables["SEC_LEVEL"] == "50"
         mock_log_info.assert_any_call("[Compare] Success: '50' GE '40'")

def test_compare_action_numeric_fail(engine):
    # Test numeric LT comparison failing
    action = CompareAction(
        type="compare",
        value="100",
        operator="LT",
        expected="50"
    )
    engine.script.steps = [action]

    with patch.object(engine, "check_session_exists", return_value=True),          patch.object(engine, "capture_pane", return_value=""),          patch("robot_py.engine.logger.error") as mock_log_error:

         engine.run()
         mock_log_error.assert_any_call("[Compare] Failed: '100' LT '50'")

def test_compare_action_string(engine):
    # Test string CONTAINS comparison
    action = CompareAction(
        type="compare",
        search_text="Status:",
        row=1, col=1, end_row=5, end_col=80,
        extract_col=9, extract_length=6,
        operator="CONTAINS",
        expected="ACTIVE"
    )
    engine.script.steps = [action]

    pane_content = "Status: ACTIVE-JOBS"

    with patch.object(engine, "check_session_exists", return_value=True),          patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)),          patch.object(engine, "capture_pane", return_value=pane_content),          patch("robot_py.engine.logger.info") as mock_log_info:

         engine.run()
         mock_log_info.assert_any_call("[Compare] Success: 'ACTIVE' CONTAINS 'ACTIVE'")

def test_runtime_variable_precedence(engine):
    # Ensure {{VAR}} substitutes correctly and doesn't interfere with ${VAR}

    engine.runtime_variables["USER"] = "runtime_user"
    os.environ["USER"] = "env_user"

    action = SendTextAction(type="send_text", text="Hello {{USER}}")
    engine.script.steps = [action]

    with patch.object(engine, "check_session_exists", return_value=True),          patch.object(engine, "capture_pane", return_value=""),          patch.object(engine, "run_tmux") as mock_run:

         engine.run()
         mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "Hello runtime_user"])
