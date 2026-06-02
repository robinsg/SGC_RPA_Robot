import pytest
from unittest.mock import patch, MagicMock
from robot_py.engine import RobotEngine, TerminationException
from robot_py.schema import SearchAndCompareAction, TerminateAction, SendKeyAction

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

def test_search_and_compare_success_line(engine):
    # Search for "Programming" on Row 9
    action = SearchAndCompareAction(
        type="search_and_compare",
        text="Programming",
        row=9,
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    pane_content = "\n" * 8 + "   Programming   " + "\n" * 15

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_search_and_compare_failure_line(engine, capsys):
    # Search for "Dummy Text" on Row 9
    action = SearchAndCompareAction(
        type="search_and_compare",
        text="Dummy Text",
        row=9,
        if_false=[SendKeyAction(type="send_key", key="F3")]
    )

    actual_content = "Actual Row Content"
    pane_content = "\n" * 8 + actual_content + "\n" * 15

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(False, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_false)

        captured = capsys.readouterr()
        assert f'Search for text failed to find "{action.text}". Actual value found: "{actual_content}".' in captured.out

def test_search_and_compare_success_positional(engine):
    # Search for "Programming" at Row 9 column 10
    action = SearchAndCompareAction(
        type="search_and_compare",
        text="Programming",
        row=9,
        col=10,
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    # "Programming" starts at column 10 (index 9)
    pane_content = "\n" * 8 + (" " * 9) + "Programming" + "\n" * 15

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_search_and_compare_failure_positional(engine, capsys):
    # Search for "Dummy Text" at Row 9 column 10
    action = SearchAndCompareAction(
        type="search_and_compare",
        text="Dummy Text",
        row=9,
        col=10
    )

    actual_at_pos = "Wrong Text"
    pane_content = "\n" * 8 + (" " * 9) + actual_at_pos + "\n" * 15

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(False, pane_content)):

        engine.execute_step(action)

        captured = capsys.readouterr()
        # It should extract the length of the search string (Dummy Text = 10 chars)
        assert f'Search for text failed to find "{action.text}". Actual value found: "{actual_at_pos}".' in captured.out

def test_search_and_compare_success_block(engine):
    # Search for "Programming" in Block (5,10) to (15,38)
    action = SearchAndCompareAction(
        type="search_and_compare",
        text="Programming",
        row=5, col=10, end_row=15, end_col=38,
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    # "Programming" is within the block on row 7
    pane_content = "\n" * 6 + (" " * 15) + "Programming" + "\n" * 17

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_search_and_compare_list_of_values(engine):
    # Search for ["Value1", "Value2"]
    action = SearchAndCompareAction(
        type="search_and_compare",
        text=["Value1", "Value2"],
        row=1,
        if_true=[SendKeyAction(type="send_key", key="Enter")]
    )

    # Found Value2
    pane_content = "Some Value2 here\n" + "\n" * 23

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_terminate_action(engine):
    action = TerminateAction(type="terminate", reason="Test termination")

    with pytest.raises(TerminationException, match="Test termination"):
        engine.execute_step(action)

def test_engine_run_termination(engine):
    engine.script.steps = [TerminateAction(type="terminate", reason="Stop now")]

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=""), \
         patch("robot_py.engine.logger.info") as mock_info:

        engine.run()
        mock_info.assert_any_call("Automation terminated as requested.")
