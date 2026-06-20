import pytest
from unittest.mock import patch, MagicMock
from robot_py.engine import RobotEngine
from robot_py.schema import SendTextAction


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


def test_send_text_with_single_key(engine):
    action = SendTextAction(type="send_text", text="wrkactjob", key="Enter")

    with patch.object(engine, "run_tmux") as mock_run, patch(
        "time.sleep"
    ) as mock_sleep, patch.object(
        engine, "check_session_exists", return_value=True
    ), patch.object(
        engine, "capture_pane", return_value="screen content"
    ):

        engine.execute_step(action)

        # Verify text sent first
        mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "wrkactjob"])

        # Verify delay after text
        mock_sleep.assert_any_call(0.25)

        # Verify key sent after delay
        # Enter -> C-m
        mock_run.assert_any_call(["send-keys", "-t", engine.session, "C-m"])

        # Total 2 sleeps: one after text, one in _send_single_key
        assert mock_sleep.call_count == 2


def test_send_text_with_multiple_keys(engine):
    action = SendTextAction(
        type="send_text", text="signoff", key=["Field_exit", "Enter"]
    )

    with patch.object(engine, "run_tmux") as mock_run, patch(
        "time.sleep"
    ) as mock_sleep, patch.object(
        engine, "check_session_exists", return_value=True
    ), patch.object(
        engine, "capture_pane", return_value="screen content"
    ):

        engine.execute_step(action)

        # Verify text sent first
        mock_run.assert_any_call(["send-keys", "-l", "-t", engine.session, "signoff"])

        # Verify keys sent in order
        # Field_exit -> C-x
        # Enter -> C-m
        mock_run.assert_any_call(["send-keys", "-t", engine.session, "C-x"])
        mock_run.assert_any_call(["send-keys", "-t", engine.session, "C-m"])

        # Verify sleeps: 1 after text, 1 after each key (total 3)
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(0.25)


def test_send_text_without_keys(engine):
    action = SendTextAction(type="send_text", text="just text")

    with patch.object(engine, "run_tmux") as mock_run, patch(
        "time.sleep"
    ) as mock_sleep, patch.object(
        engine, "check_session_exists", return_value=True
    ), patch.object(
        engine, "capture_pane", return_value="screen content"
    ):

        engine.execute_step(action)

        mock_run.assert_called_once_with(
            ["send-keys", "-l", "-t", engine.session, "just text"]
        )
        assert mock_sleep.call_count == 0


def test_send_text_with_runtime_variable_keys(engine):
    engine.runtime_variables["MY_KEY"] = "F3"
    action = SendTextAction(type="send_text", text="exit", key="{{MY_KEY}}")

    with patch.object(engine, "run_tmux") as mock_run, patch(
        "time.sleep"
    ) as mock_sleep, patch.object(
        engine, "check_session_exists", return_value=True
    ), patch.object(
        engine, "capture_pane", return_value="screen content"
    ):

        engine.execute_step(action)

        # F3 -> F3 (logical to tmux)
        mock_run.assert_any_call(["send-keys", "-t", engine.session, "F3"])
        assert mock_sleep.call_count == 2
