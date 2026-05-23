import pytest
import subprocess
import os
from unittest.mock import patch, MagicMock, mock_open
from robot_py.engine import RobotEngine, Screen
from robot_py.schema import (
    SendTextAction, SendKeyAction, SleepAction, CaptureAction,
    WaitForTextAction, SearchExtractAndSendAction, ExtractAtCursorAndSendAction,
    PressKeyIfTextPresentAction, MoveCursorAction, SearchAndMoveCursorAction
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

def test_run_tmux_success(engine):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0), # check_session_exists
            MagicMock(returncode=0, stdout="output\n") # run_tmux
        ]
        result = engine.run_tmux(["display-message", "hello"])
        assert result == "output\n"
        mock_run.assert_any_call(["tmux", "display-message", "hello"], capture_output=True, text=True)

def test_run_tmux_failure(engine):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0), # check_session_exists
            MagicMock(returncode=1, stderr="error message") # run_tmux
        ]
        with pytest.raises(RuntimeError, match="Tmux command failed"):
            engine.run_tmux(["invalid-cmd"])

def test_move_cursor(engine):
    with patch.object(engine.tmux, "get_cursor", return_value=(1, 1)), \
         patch.object(engine.tmux, "exists", return_value=True), \
         patch.object(engine.tmux, "send_keys") as mock_send:
        engine.move_cursor(3, 5)
        assert mock_send.call_count == 6

def test_wait_for_text_retry(engine):
    with patch.object(engine, "refresh_screen") as mock_refresh, \
         patch("time.sleep") as mock_sleep, \
         patch("time.time") as mock_time:

        mock_refresh.side_effect = [
            Screen("wrong", 24, 80),
            Screen("wrong", 24, 80),
            Screen("target text", 24, 80)
        ]
        mock_time.side_effect = [100, 100.1, 100.2, 100.3, 100.4, 100.5, 100.6, 100.7]

        engine.wait_for_text("target text", timeout=5)
        assert mock_refresh.call_count == 3
        assert mock_sleep.call_count == 2

def test_wait_for_text_timeout(engine):
    with patch.object(engine, "refresh_screen", return_value=Screen("wrong", 24, 80)), \
         patch("time.sleep"), \
         patch("time.time", side_effect=[100, 106, 107]):

        with pytest.raises(RuntimeError, match="Timeout waiting for text"):
            engine.wait_for_text("target", timeout=5)

def test_search_extract_and_send_action(engine):
    action = SearchExtractAndSendAction(
        type="search_extract_and_send", text="FindMe", row=1, col=1, end_row=5, end_col=80,
        extract_col=10, extract_length=5
    )
    engine.script.steps = [action]

    pane_content = "FindMe   EXTRACTED remainder"
    mock_screen = Screen(pane_content, 24, 80)

    with patch.object(engine.tmux, "exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, mock_screen)), \
         patch.object(engine.tmux, "send_keys") as mock_send:

        engine.run()
        # "FindMe   E" -> E is index 9 (col 10). "EXTRA" is length 5.
        mock_send.assert_any_call("EXTRA", literal=True)

def test_extract_at_cursor_and_send_action(engine):
    action = ExtractAtCursorAndSendAction(type="extract_at_cursor_and_send", length=4)
    engine.script.steps = [action]

    pane_content = "Data: ABCD remainder"
    mock_screen = Screen(pane_content, 24, 80)

    with patch.object(engine.tmux, "exists", return_value=True), \
         patch.object(engine.tmux, "get_cursor", return_value=(1, 7)), \
         patch.object(engine, "refresh_screen", return_value=mock_screen), \
         patch.object(engine.tmux, "send_keys") as mock_send:

        engine.run()
        mock_send.assert_any_call("ABCD", literal=True)

def test_engine_run_various_actions(engine, tmp_path):
    actions = [
        SendTextAction(type="send_text", text="input"),
        SendKeyAction(type="send_key", key="Enter"),
        SleepAction(type="sleep", seconds=0.1),
        CaptureAction(type="capture", filename="test_cap"),
        WaitForTextAction(type="wait_for_text", text="ready"),
        PressKeyIfTextPresentAction(type="press_key_if_text_present", text="ready", key="F3"),
        MoveCursorAction(type="move_cursor", row=5, col=5),
        SearchAndMoveCursorAction(type="search_and_move_cursor", text="target", row=1, col=1, end_row=10, end_col=80, target_col=20)
    ]
    engine.script.steps = actions

    pane_content = "some content\ntarget here\nready"
    mock_screen = Screen(pane_content, 24, 80)

    with patch.object(engine.tmux, "exists", return_value=True), \
         patch.object(engine.tmux, "send_keys") as mock_send, \
         patch.object(engine, "refresh_screen", return_value=mock_screen), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, mock_screen)), \
         patch.object(engine.tmux, "get_cursor", return_value=(1, 1)), \
         patch("time.sleep"), \
         patch("os.makedirs"), \
         patch("builtins.open", mock_open()):

        engine.run()

        mock_send.assert_any_call("input", literal=True)
        mock_send.assert_any_call("C-m")
        mock_send.assert_any_call("F3")

def test_terminate_session(engine):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        engine.terminate_session()
        mock_run.assert_any_call(["tmux", "kill-session", "-t", engine.session], capture_output=True)

def test_engine_run_session_not_found(engine):
    with patch.object(engine.tmux, "exists", return_value=False), \
         patch("robot_py.engine.logger.error") as mock_log_error:
        engine.run()
        mock_log_error.assert_any_call(f"Error: Tmux session '{engine.session}' not found.")

def test_capture_debug_screen(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    engine.log_level = "DEBUG"

    pane_content = "debug screen content"
    mock_screen = Screen(pane_content, 24, 80)
    with patch.object(engine, "refresh_screen", return_value=mock_screen), \
         patch("os.makedirs"), \
         patch("builtins.open", mock_open()) as m:
        engine.capture_debug_screen("test_action")
        m().write.assert_called_once_with(pane_content)
