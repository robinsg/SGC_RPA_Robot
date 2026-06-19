import os
from robot_py.logger import setup_logger
import logging


def test_setup_logger_creates_dir(tmp_path, monkeypatch):
    log_dir = tmp_path / "test_logs"
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("TN5250_HOST", "test_lpar")

    # Clear existing logger handlers if any to allow re-setup for test
    logger = logging.getLogger("robot")
    logger.handlers.clear()

    setup_logger()
    assert os.path.exists(log_dir)
    log_file = log_dir / "test_lpar.log"
    assert os.path.exists(log_file)
