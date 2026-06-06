import pytest
from unittest.mock import patch, MagicMock
from robot_py.engine import RobotEngine, TerminationException
from robot_py.schema import CompareAction, SendKeyAction

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

def test_compare_numeric_eq_success(engine):
    action = CompareAction(
        type="compare",
        expected="40",
        operator="EQ",
        row=7, col=35, length=2,
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    # Mock screen content with "40" at (7, 35)
    pane_content = "\n" * 6 + " " * 34 + "40" + "\n" * 17

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_compare_numeric_gt_failure(engine):
    action = CompareAction(
        type="compare",
        expected="50",
        operator="GT",
        row=7, col=35, length=2,
        if_false=[SendKeyAction(type="send_key", key="F3")]
    )

    # "40" is NOT greater than "50"
    pane_content = "\n" * 6 + " " * 34 + "40" + "\n" * 17

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_false)

def test_compare_string_contains_success(engine):
    action = CompareAction(
        type="compare",
        expected="READY",
        operator="CONTAINS",
        row=10, col=1, length=20,
        if_true=[SendKeyAction(type="send_key", key="Enter")]
    )

    pane_content = "\n" * 9 + "SYSTEM IS READY NOW " + "\n" * 14

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_compare_relative_extraction_success(engine):
    action = CompareAction(
        type="compare",
        search_text="QSECURITY",
        row=1, col=1, end_row=20, end_col=80,
        extract_col=35, extract_length=2,
        expected="40",
        operator="EQ",
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    # Row 7 contains QSECURITY and 40 at col 35
    pane_content = "\n" * 6 + "QSECURITY" + " " * 25 + "40" + "\n" * 17

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "wait_for_text_internal", return_value=(True, pane_content)), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)

def test_compare_numeric_conversion_error_actual(engine):
    action = CompareAction(
        type="compare",
        expected="40",
        operator="EQ",
        row=1, col=1, length=5
    )

    pane_content = "ABCDE" + "\n" * 23

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content):

        with pytest.raises(TerminationException, match="Compare data is incompatible: Extracted value 'ABCDE' is not numeric"):
            engine.execute_step(action)

def test_compare_numeric_conversion_error_expected(engine):
    action = CompareAction(
        type="compare",
        expected="FORTY",
        operator="EQ",
        row=1, col=1, length=2
    )

    pane_content = "40" + "\n" * 23

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content):

        with pytest.raises(TerminationException, match="Compare data is incompatible: The expected value 'FORTY' resolved to 'FORTY', which is not numeric"):
            engine.execute_step(action)


def test_compare_numeric_conversion_error_variable(engine):
    engine.runtime_variables["SEC_LEVEL"] = "XX"
    action = CompareAction(
        type="compare",
        expected="{{SEC_LEVEL}}",
        operator="EQ",
        row=1, col=1, length=2
    )

    pane_content = "40" + "\n" * 23

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content):

        with pytest.raises(TerminationException, match="Compare data is incompatible: The run time variable '{{SEC_LEVEL}}' resolved to 'XX', which is not numeric"):
            engine.execute_step(action)

def test_engine_run_termination_logging(engine):
    # Setup a CompareAction that will fail numeric conversion
    engine.runtime_variables["SEC_LEVEL"] = "XX"
    action = CompareAction(
        type="compare",
        expected="{{SEC_LEVEL}}",
        operator="EQ",
        row=1, col=1, length=2
    )
    engine.script.steps = [action]

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value="40" + "\n" * 23), \
         patch("robot_py.engine.logger.info") as mock_info:

        engine.run()
        # Verify that the specific termination message was logged in run()
        expected_msg = "Automation terminated: Compare data is incompatible: The run time variable '{{SEC_LEVEL}}' resolved to 'XX', which is not numeric for operator EQ"
        mock_info.assert_any_call(expected_msg)


def test_compare_with_runtime_variable(engine):
    engine.runtime_variables["SEC_LEVEL"] = "40"
    action = CompareAction(
        type="compare",
        expected="{{SEC_LEVEL}}",
        operator="EQ",
        row=1, col=1, length=2,
        if_true=[SendKeyAction(type="send_key", key="F1")]
    )

    pane_content = "40" + "\n" * 23

    with patch.object(engine, "check_session_exists", return_value=True), \
         patch.object(engine, "capture_pane", return_value=pane_content), \
         patch.object(engine, "execute_steps") as mock_execute_steps:

        engine.execute_step(action)
        mock_execute_steps.assert_called_once_with(action.if_true)
