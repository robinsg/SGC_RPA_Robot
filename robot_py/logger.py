import logging
import os
import re


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

    def _should_mask(self) -> bool:
        """Check if data masking should be applied based on environment variables.

        Masking is active if GITHUB_ACTIONS is true and LOG_LEVEL is DEBUG.

        Returns:
            True if data should be masked, False otherwise.
        """
        github_actions = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        log_level = os.environ.get("LOG_LEVEL", "").upper() == "DEBUG"
        return github_actions and log_level

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

        # Apply masking only if conditions are met
        if self._should_mask():
            # Redact screens (content between markers used in engine.py)
            formatted_message = re.sub(
                r"(--- .*? ---\n)(.*?)(\n--- End .*? ---)",
                r"\1[INFO: Full screen content redacted from stdout. Check log files on Runner server for details.]\3",
                formatted_message,
                flags=re.DOTALL,
            )

            # Masking for parameters "--yaml-file /path/to/script.yaml" or "-f ..." or "-y ..."
            formatted_message = re.sub(
                r"(--yaml-file|-f|-y)\s+[^\s]+",
                r"--yaml-file [MASKED_YAML_FILE]",
                formatted_message,
            )
            # Masking for "--host <hostname>" or "-h ..."
            formatted_message = re.sub(
                r"(--host|-h)\s+[^\s]+", r"--host [MASKED_HOST]", formatted_message
            )
            # Masking for "--env /path/to/.env.file" or "-e ..."
            formatted_message = re.sub(
                r"(--env|-e)\s+[^\s]+",
                r"--env [MASKED_ENV_FILE]",
                formatted_message,
            )
            # Masking for "Loading environment variables from /path/to/.env.file"
            formatted_message = re.sub(
                r"Loading environment variables from\s+[^\s]+",
                r"Loading environment variables from [MASKED_ENV_FILE]",
                formatted_message,
            )
            # Masking for "Testing connectivity to <hostname>:<port>"
            formatted_message = re.sub(
                r"Testing connectivity to\s+[^:]+:\d+",
                r"Testing connectivity to [MASKED_HOST]:[MASKED_PORT]",
                formatted_message,
            )
            # Masking for "Starting new TN5250 session '<session-name>' for host: <hostname>"
            formatted_message = re.sub(
                r"Starting new TN5250 session\s+\'[^\']+\'\s+for host:\s+[^\s]+",
                r"Starting new TN5250 session '[MASKED_SESSION_NAME]' for host: [MASKED_HOST]",
                formatted_message,
            )
            # Masking for "Executing: tn5250 ... <hostname> with window size ..."
            formatted_message = re.sub(
                r"Executing:\s+tn5250\s+.*?\s+([^\s]+)\s+with window size",
                r"Executing: tn5250 ... [MASKED_HOST] with window size",
                formatted_message,
            )

            # Masking for "HMC_HOST detected. Connecting via HMC Proxy on port 2301."
            formatted_message = re.sub(
                r"(Connecting via HMC Proxy on port )\d+",
                r"\1[MASKED_PORT]",
                formatted_message,
            )

            # Masking for "[Debug Capture] Screen saved to logs/captures/eur400e/..."
            formatted_message = re.sub(
                r"(Screen saved to logs/captures/)[^/]+/",
                r"\1[MASKED_HOST]/",
                formatted_message,
            )

            # Masking for "[SearchMove] Found "EUR400E" at row 14."
            # and "[SearchExtract] Found "EUR400E" at row 14."
            lpar_name = os.environ.get("TN5250_HOST", "")
            if lpar_name:
                # Mask LPAR name when it appears in quotes (found text)
                formatted_message = re.sub(
                    rf'Found "{re.escape(lpar_name)}"',
                    r'Found "[MASKED_HOST]"',
                    formatted_message,
                    flags=re.IGNORECASE,
                )

            # Masking for "INFO: [Screen] Work with Active Jobs                     EUR400E"
            if lpar_name:
                formatted_message = re.sub(
                    rf"(\[Screen\].*?)\s+{re.escape(lpar_name)}\b",
                    r"\1 ***",
                    formatted_message,
                    flags=re.IGNORECASE,
                )

            # Masking for "[Capture] Saved to /full/path/to/last_screen.txt"
            # Simplify to just the filename
            formatted_message = re.sub(
                r"(\[Capture\] Saved to ).*/([^/]+)",
                r"\1file \2",
                formatted_message,
            )

            # Masking for "Terminating tmux session: robot-eur400e"
            # and "Session 'robot-eur400e' already terminated."
            formatted_message = re.sub(
                r"(Terminating tmux session:? robot-)[^\s]+",
                r"\1[MASKED_HOST]",
                formatted_message,
            )
            formatted_message = re.sub(
                r"(Session 'robot-)[^']+",
                r"\1[MASKED_HOST]",
                formatted_message,
            )

        # Mask sensitive environment variables
        sensitive_vars = ["TN5250_PASSWORD", "HMC_PWD"]
        custom_sensitive = os.environ.get("ROBOT_SENSITIVE_VARS", "")
        if custom_sensitive:
            sensitive_vars.extend(
                [v.strip() for v in custom_sensitive.split(",") if v.strip()]
            )

        for var_name in sensitive_vars:
            val = os.environ.get(var_name)
            if val:
                formatted_message = formatted_message.replace(val, "********")

        return formatted_message


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
