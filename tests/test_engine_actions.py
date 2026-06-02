import pytest
import subprocess
import os
from unittest.mock import patch, MagicMock, mock_open
from robot_py.engine import RobotEngine
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
            engine.run_tmux(["invalid"])

def test_move_cursor(engine):
    with patch.object(engine, "get_cursor_position", return_value=(1, 1)), \
         patch.object(engine, "run_tmux") as mock_run:
        engine.move_cursor(3, 3)
        # 1,1 to 3,3 requires 2 Down and 2 Right
        assert mock_run.call_count == 4
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert calls.count(["send-keys", "-t", engine.session, "Down"]) == 2
        assert calls.count(["send-keys", "-t", engine.session, "Right"]) == 2

        # Test moving Up and Left
        mock_run.reset_mock()
        with patch.object(engine, "get_cursor_position", return_value=(5, 5)):
            engine.move_cursor(3, 3)
            calls = [c[0][0] for c in mock_run.call_args_list]
            assert calls.count(["send-keys", "-t", engine.session, "Up"]) == 2
            assert calls.count(["send-keys", "-t", engine.session, "Left"]) == 2

def test_wait_for_text_retry(engine):
    with patch.object(engine, "capture_pane") as mock_capture, \
         patch("time.sleep") as mock_sleep, \
         patch("time.time") as mock_time:

        mock_capture.side_effect = ["wrong", "wrong", "target text"]
        mock_time.side_effect = [100, 100.1, 100.2, 100.3, 100.4, 100.5] # start, check1, sleep, check2, sleep, check3

        engine.wait_for_text("target text", timeout=5)
        assert mock_capture.call_count == 3
        assert mock_sleep.call_count == 2

def test_wait_for_text_timeout(engine):
    with patch.object(engine, "capture_pane", return_value="never found"), \
         patch("time.sleep"), \
         patch("time.time") as mock_time:

        mock_time.side_effect = [100, 106] # start, check (already expired)

        with pytest.raises(RuntimeError, match="Timeout waiting for text"):
            engine.wait_for_text("target text", timeout=5)

def test_search_extract_and_send_action(engine):
    action = SearchExtractAndSendAction(
        type="search_extract_and_send",
        text="ID:",
        row=1, col=1, end_row=5, end_col=80,
        extract_col=5, extract_length=3
    )
    engine.script.steps = [action]

    pane_content = "Line 1\nID: 12345\nLine 3"

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "run_tmux") as mock_run, \
         patch.object(engine, "capture_pane", return_value=pane_content):

        engine.run()
        # Row 2 (index 1), extract_col 5 (index 4) for length 3 -> "123"
        mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "123"])

def test_extract_at_cursor_and_send_action(engine):
    action = ExtractAtCursorAndSendAction(type="extract_at_cursor_and_send", length=4)
    engine.script.steps = [action]

    pane_content = "Data: ABCD remainder"

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "get_cursor_position", return_value=(1, 7)), \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch.object(engine, "run_tmux") as mock_run:

        # Row 1 (index 0), Col 7 (index 6) for length 4 -> "ABCD"
        engine.run()
        mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "ABCD"])

def test_engine_run_various_actions(engine, tmp_path):
    # Test remaining actions in engine.run
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

    # We need to mock run_tmux to return different things based on call
    def mock_run_tmux_impl(args):
        if "display-message" in args:
            return "0,0" # return cursor at 1,1
        return pane_content

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "run_tmux", side_effect=mock_run_tmux_impl) as mock_run_tmux, \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch("time.sleep"), \
         patch("os.makedirs"), \
         patch("builtins.open", mock_open()):

        engine.run()

        # Verify calls
        mock_run_tmux.assert_any_call(["send-keys", "-l", "-t", engine.session, "input"])
        mock_run_tmux.assert_any_call(["send-keys", "-t", engine.session, "C-m"])
        mock_run_tmux.assert_any_call(["send-keys", "-t", engine.session, "F3"])

def test_terminate_session(engine):
    with patch("subprocess.run") as mock_run:
        # Session exists
        mock_run.return_value = MagicMock(returncode=0)
        engine.terminate_session()
        mock_run.assert_any_call(["tmux", "kill-session", "-t", engine.session], capture_output=True)

        # Session doesn't exist
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=1)
        engine.terminate_session()
        assert not any(call[0][0] == ["tmux", "kill-session", "-t", engine.session] for call in mock_run.call_args_list)

def test_engine_init_unsupported_device_type(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", "UNSUPPORTED")

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    # We need to bypass validate_environment for this test if it also checks device type
    # Actually validate_environment DOES check device type, so we expect ValueError from it or engine init
    with pytest.raises(ValueError, match="Unsupported TN5250_DEVICE_TYPE"):
        RobotEngine(str(yaml_file))

def test_engine_run_session_not_found(engine):
    with patch.object(engine, "check_session_exists", return_value=False), \
         patch("robot_py.engine.logger.error") as mock_log_error:
        engine.run()
        mock_log_error.assert_any_call(f"Error: Tmux session '{engine.session}' not found.")

def test_capture_debug_screen(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    engine.log_level = "DEBUG"

    pane_content = "debug screen content"
    with patch.object(engine, "capture_pane", return_value=pane_content), \
         patch("os.makedirs"), \
         patch("builtins.open", mock_open()) as m:
        engine.capture_debug_screen("test_action")
        m().write.assert_called_once_with(pane_content)
