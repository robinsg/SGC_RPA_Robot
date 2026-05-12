import pytest
import os
import yaml
from robot_py.schema import (
    parse_robot_script,
    Action,
    SendTextAction,
    SendKeyAction,
    WaitForTextAction,
    SleepAction,
    CaptureAction,
    PressKeyIfTextPresentAction,
    MoveCursorAction,
    SearchAndMoveCursorAction,
    SearchExtractAndSendAction,
    ExtractAtCursorAndSendAction,
    RobotScript,
)

def test_action_from_dict_all_types():
    actions = [
        {"type": "send_text", "text": "hello"},
        {"type": "send_key", "key": "Enter"},
        {"type": "wait_for_text", "text": "Ready"},
        {"type": "sleep", "seconds": 1.5},
        {"type": "capture", "filename": "screen"},
        {"type": "press_key_if_text_present", "text": "Error", "key": "Reset"},
        {"type": "move_cursor", "row": 10, "col": 20},
        {"type": "search_and_move_cursor", "text": "User", "row": 1, "col": 1, "end_row": 24, "end_col": 80, "target_col": 10},
        {"type": "search_extract_and_send", "text": "ID:", "row": 1, "col": 1, "end_row": 24, "end_col": 80, "extract_col": 10, "extract_length": 5},
        {"type": "extract_at_cursor_and_send", "length": 10},
    ]

    assert isinstance(Action.from_dict(actions[0]), SendTextAction)
    assert isinstance(Action.from_dict(actions[1]), SendKeyAction)
    assert isinstance(Action.from_dict(actions[2]), WaitForTextAction)
    assert isinstance(Action.from_dict(actions[3]), SleepAction)
    assert isinstance(Action.from_dict(actions[4]), CaptureAction)
    assert isinstance(Action.from_dict(actions[5]), PressKeyIfTextPresentAction)
    assert isinstance(Action.from_dict(actions[6]), MoveCursorAction)
    assert isinstance(Action.from_dict(actions[7]), SearchAndMoveCursorAction)
    assert isinstance(Action.from_dict(actions[8]), SearchExtractAndSendAction)
    assert isinstance(Action.from_dict(actions[9]), ExtractAtCursorAndSendAction)

def test_action_from_dict_unknown_type():
    with pytest.raises(ValueError, match="Unknown action type: unknown"):
        Action.from_dict({"type": "unknown"})

def test_parse_robot_script_basic(tmp_path):
    yaml_content = """
name: Test Robot
description: A test robot script
tmux_session: test_session
defaults:
  wait_timeout: 10
  typing_delay_ms: 100
steps:
  - type: send_text
    text: "hello"
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    script = parse_robot_script(str(yaml_file))

    assert script.name == "Test Robot"
    assert script.description == "A test robot script"
    assert script.tmux_session == "test_session"
    assert script.defaults.wait_timeout == 10
    assert script.defaults.typing_delay_ms == 100
    assert len(script.steps) == 1
    assert isinstance(script.steps[0], SendTextAction)
    assert script.steps[0].text == "hello"

def test_parse_robot_script_env_substitution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_VAR", "substituted_value")
    yaml_content = """
name: ${TEST_VAR}
steps:
  - type: send_text
    text: "${UNDEFINED_VAR:-default_value}"
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    script = parse_robot_script(str(yaml_file))

    assert script.name == "substituted_value"
    assert script.steps[0].text == "default_value"

def test_parse_robot_script_missing_env_no_default(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    yaml_content = """
name: "${MISSING_VAR}"
steps: []
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    script = parse_robot_script(str(yaml_file))
    # re.sub with empty string for missing env var should result in an empty string in YAML
    assert script.name == ""
