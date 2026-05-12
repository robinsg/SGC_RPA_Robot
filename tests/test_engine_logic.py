import pytest
from unittest.mock import MagicMock
from robot_py.engine import RobotEngine, SUPPORTED_24x80

@pytest.fixture
def mock_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    # Force 24x80 for consistent testing
    monkeypatch.setenv("TN5250_DEVICE_TYPE", SUPPORTED_24x80[0])

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    return RobotEngine(str(yaml_file))

def test_validate_coords(mock_engine):
    # 24x80
    mock_engine.validate_coords(1, 1)
    mock_engine.validate_coords(24, 80)

    with pytest.raises(ValueError, match="Row 0 out of bounds"):
        mock_engine.validate_coords(0, 1)
    with pytest.raises(ValueError, match="Row 25 out of bounds"):
        mock_engine.validate_coords(25, 1)
    with pytest.raises(ValueError, match="Column 0 out of bounds"):
        mock_engine.validate_coords(1, 0)
    with pytest.raises(ValueError, match="Column 81 out of bounds"):
        mock_engine.validate_coords(1, 81)

def test_validate_coords_132(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", "IBM-3477-FC")

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    engine = RobotEngine(str(yaml_file))
    engine.validate_coords(27, 132)
    with pytest.raises(ValueError, match="Row 28 out of bounds"):
        engine.validate_coords(28, 1)
    with pytest.raises(ValueError, match="Column 133 out of bounds"):
        engine.validate_coords(1, 133)

def test_validate_block(mock_engine):
    mock_engine.validate_block(1, 1, 10, 10)
    with pytest.raises(ValueError, match="Invalid block"):
        mock_engine.validate_block(10, 10, 1, 1)

def test_find_text_in_buffer_global(mock_engine):
    pane_content = "Line 1\nLine 2 with target text\nLine 3"
    assert mock_engine.find_text_in_buffer(pane_content, "target text") is True
    assert mock_engine.find_text_in_buffer(pane_content, "missing") is False

def test_find_text_in_buffer_row(mock_engine):
    pane_content = "Line 1\nLine 2 with target text\nLine 3"
    assert mock_engine.find_text_in_buffer(pane_content, "target text", row=2) is True
    assert mock_engine.find_text_in_buffer(pane_content, "target text", row=1) is False

def test_find_text_in_buffer_block(mock_engine):
    pane_content = "0123456789\n0123TARGET\n0123456789"
    # TARGET is at row 2, col 5-10 (1-indexed)
    assert mock_engine.find_text_in_buffer(pane_content, "TARGET", row=2, col=5, end_row=2, end_col=10) is True
    assert mock_engine.find_text_in_buffer(pane_content, "TARGET", row=2, col=1, end_row=2, end_col=4) is False

def test_find_text_in_buffer_message_line(mock_engine):
    # 24x80, message line is row 24 (index 23)
    lines = ["line"] * 24
    lines[23] = "Error message here"
    pane_content = "\n".join(lines)
    assert mock_engine.find_text_in_buffer(pane_content, "Error", is_message_line=True) is True
    assert mock_engine.find_text_in_buffer(pane_content, "line", is_message_line=True) is False

def test_find_text_in_buffer_message_line_132(tmp_path, monkeypatch):
    monkeypatch.setenv("TN5250_HOST", "test_host")
    monkeypatch.setenv("TN5250_USER", "test_user")
    monkeypatch.setenv("TN5250_PASSWORD", "test_password")
    monkeypatch.setenv("TN5250_DEVICE_TYPE", "IBM-3477-FC")

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: Test\nsteps: []")

    engine = RobotEngine(str(yaml_file))
    # 27x132, message line is row 27 (index 26)
    lines = ["line"] * 27
    lines[26] = "Error message here"
    pane_content = "\n".join(lines)
    assert engine.find_text_in_buffer(pane_content, "Error", is_message_line=True) is True

def test_find_text_in_block(mock_engine):
    pane_content = "Line 1\nTarget Row\nTarget Row\nLine 4"
    # Search for "Target" in rows 1-3
    match_row = mock_engine.find_text_in_block(pane_content, "Target", row=1, col=1, end_row=3, end_col=80)
    assert match_row == 2

    # Search for "Target" starting from row 3
    match_row = mock_engine.find_text_in_block(pane_content, "Target", row=3, col=1, end_row=4, end_col=80)
    assert match_row == 3

    assert mock_engine.find_text_in_block(pane_content, "Missing", row=1, col=1, end_row=4, end_col=80) is None
