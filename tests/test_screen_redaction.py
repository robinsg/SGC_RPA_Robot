import logging
import os
import pytest
from robot_py.logger import CustomFormatter

def test_screen_redaction_enabled(monkeypatch):
    """Test that screens are redacted when all conditions are met."""
    monkeypatch.setenv("HMC_HOST", "hmc.example.com")
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
    assert "[SCREEN REDACTED]" in formatted
    assert "Line 1" not in formatted
    assert "Line 2" not in formatted
    assert "--- Before Enter ---" in formatted
    assert "--- End Before Enter ---" in formatted

def test_screen_redaction_disabled_no_hmc(monkeypatch):
    """Test that screens are NOT redacted when HMC_HOST is missing."""
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
    assert "[SCREEN REDACTED]" not in formatted
    assert "Line 1" in formatted
    assert "Line 2" in formatted

def test_screen_redaction_disabled_no_github_actions(monkeypatch):
    """Test that screens are NOT redacted when GITHUB_ACTIONS is not true."""
    monkeypatch.setenv("HMC_HOST", "hmc.example.com")
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
    assert "[SCREEN REDACTED]" not in formatted
    assert "Line 1" in formatted

def test_screen_redaction_disabled_not_debug(monkeypatch):
    """Test that screens are NOT redacted when LOG_LEVEL is not DEBUG."""
    # Even if LOG_LEVEL env var is INFO, the formatter might still be called
    # if the record level is higher, but the check is explicitly on the env var.
    monkeypatch.setenv("HMC_HOST", "hmc.example.com")
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
    assert "[SCREEN REDACTED]" not in formatted
    assert "Line 1" in formatted

def test_screen_redaction_multiple_screens(monkeypatch):
    """Test that multiple screens in a single message are all redacted."""
    monkeypatch.setenv("HMC_HOST", "hmc.example.com")
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
    assert formatted.count("[SCREEN REDACTED]") == 2
    assert "Screen 1 content" not in formatted
    assert "Screen 2 content" not in formatted
    assert "Some text" in formatted
    assert "More text" in formatted
