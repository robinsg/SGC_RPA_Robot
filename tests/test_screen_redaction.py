import logging
import os
import pytest
from robot_py.logger import CustomFormatter

REDACTED_MSG = "[INFO: Full screen content redacted from stdout. Check log files for details.]"

def test_screen_redaction_enabled(monkeypatch):
    """Test that screens are redacted when all conditions are met."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    formatter = CustomFormatter()
    record = logging.LogRecord(
        name="robot",
        level=logging.DEBUG,
        pathname="engine.py",
        lineno=100,
        msg="\n--- Before Enter ---\nLine 1\nLine 2\n--- End Before Enter ---",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert REDACTED_MSG in formatted
    assert "Line 1" not in formatted
    assert "Line 2" not in formatted
    assert "--- Before Enter ---" in formatted
    assert "--- End Before Enter ---" in formatted

def test_screen_redaction_works_without_hmc(monkeypatch):
    """Test that screens are redacted even if HMC_HOST is missing."""
    monkeypatch.delenv("HMC_HOST", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    formatter = CustomFormatter()
    record = logging.LogRecord(
        name="robot",
        level=logging.DEBUG,
        pathname="engine.py",
        lineno=100,
        msg="\n--- Before Enter ---\nLine 1\nLine 2\n--- End Before Enter ---",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert REDACTED_MSG in formatted
    assert "Line 1" not in formatted

def test_screen_redaction_disabled_no_github_actions(monkeypatch):
    """Test that screens are NOT redacted when GITHUB_ACTIONS is not true."""
    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    formatter = CustomFormatter()
    record = logging.LogRecord(
        name="robot",
        level=logging.DEBUG,
        pathname="engine.py",
        lineno=100,
        msg="\n--- Before Enter ---\nLine 1\nLine 2\n--- End Before Enter ---",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert REDACTED_MSG not in formatted
    assert "Line 1" in formatted

def test_screen_redaction_disabled_not_debug(monkeypatch):
    """Test that screens are NOT redacted when LOG_LEVEL is not DEBUG."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    formatter = CustomFormatter()
    record = logging.LogRecord(
        name="robot",
        level=logging.INFO,
        pathname="engine.py",
        lineno=100,
        msg="\n--- Before Enter ---\nLine 1\nLine 2\n--- End Before Enter ---",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert REDACTED_MSG not in formatted
    assert "Line 1" in formatted

def test_screen_redaction_multiple_screens(monkeypatch):
    """Test that multiple screens in a single message are all redacted."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    formatter = CustomFormatter()
    msg = (
        "Some text\n"
        "--- Before Enter ---\n"
        "Screen 1 content\n"
        "--- End Before Enter ---\n"
        "More text\n"
        "--- After Enter ---\n"
        "Screen 2 content\n"
        "--- End After Enter ---"
    )
    record = logging.LogRecord(
        name="robot",
        level=logging.DEBUG,
        pathname="engine.py",
        lineno=100,
        msg=msg,
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert formatted.count(REDACTED_MSG) == 2
    assert "Screen 1 content" not in formatted
    assert "Screen 2 content" not in formatted
    assert "Some text" in formatted
    assert "More text" in formatted
