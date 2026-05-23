import logging
import os
import re


class CustomFormatter(logging.Formatter):
    """Custom formatter for the console with colours and masking."""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s %(levelname)s: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensitive_patterns = []
        for key in ["TN5250_PASSWORD", "HMC_PWD"]:
            val = os.environ.get(key)
            if val and len(val) > 3:
                self.sensitive_patterns.append(re.escape(val))

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colours and mask sensitive data."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S.%3N")
        msg = formatter.format(record)

        for pattern in self.sensitive_patterns:
            msg = re.sub(pattern, "********", msg)
        return msg


def setup_logger() -> logging.Logger:
    """Initialise and configure the application logger."""
    lpar_name = os.environ.get("TN5250_HOST", "unknown-lpar")
    log_dir = os.environ.get("LOG_DIR", "logs")
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()

    log_level = getattr(logging, log_level_str, logging.INFO)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{lpar_name}.log")

    logger = logging.getLogger("robot")
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        f"%(asctime)s,{lpar_name},%(message)s", datefmt="%Y-%m-%d %H:%M:%S.%3N"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
