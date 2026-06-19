import logging
import os
from .masker import LogMasker


class CustomFormatter(logging.Formatter):
    """Custom formatter for the console with colours.

    This formatter applies ANSI escape codes to the log output based on the
    log level, providing a more readable and visually distinct console log.
    """

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

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colours and mask sensitive data.

        Also redacts full screen dumps if specific environment conditions are met.

        Args:
            record: The log record to format.

        Returns:
            The formatted log message as a string.
        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S.%3N")
        formatted_message = formatter.format(record)

        return LogMasker.mask_message(formatted_message)


def setup_logger() -> logging.Logger:
    """Initialise and configure the application logger.

    Sets up a logger with two handlers:
    1. A FileHandler that logs to a file named after the target host.
    2. A StreamHandler (console) that uses CustomFormatter for coloured output.

    Returns:
        The configured logging.Logger instance.
    """
    lpar_name = os.environ.get("TN5250_HOST", "unknown-lpar")
    log_dir = os.environ.get("LOG_DIR", "logs")
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()

    log_level = getattr(logging, log_level_str, logging.INFO)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{lpar_name}.log")

    logger = logging.getLogger("robot")
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    # File handler with the CSV-like format
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        f"%(asctime)s,{lpar_name},%(message)s", datefmt="%Y-%m-%d %H:%M:%S.%3N"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler with the readable format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
