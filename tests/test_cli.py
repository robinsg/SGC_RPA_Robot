import pytest
from unittest.mock import patch
from robot_py.cli import main

def test_cli_missing_args():
    with patch("sys.argv", ["cli.py"]), \
         patch("sys.exit") as mock_exit:
        # argparse prints to stderr and exits with 2 for missing required args
        mock_exit.side_effect = SystemExit(2)
        with pytest.raises(SystemExit) as e:
            main()

        assert e.value.code == 2
        mock_exit.assert_called_with(2)

def test_cli_success(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")

    with patch("sys.argv", ["cli.py", "--yaml-file", str(yaml_file)]), \
         patch("robot_py.engine.RobotEngine.run") as mock_run, \
         patch("robot_py.engine.RobotEngine.check_session_exists", return_value=True):
        main()
        mock_run.assert_called_once()

def test_cli_error_handling(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")

    with patch("sys.argv", ["cli.py", "--yaml-file", "non_existent.yaml"]), \
         patch("sys.exit") as mock_exit:
        mock_exit.side_effect = SystemExit(1)
        with pytest.raises(SystemExit) as e:
            main()
        
        assert e.value.code == 1
        mock_exit.assert_called_with(1)

