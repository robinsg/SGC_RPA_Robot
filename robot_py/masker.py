import os
import re

class LogMasker:
    """Utility class for masking sensitive data in log messages."""

    @staticmethod
    def _should_mask() -> bool:
        """Check if data masking should be applied based on environment variables.

        Masking is active if GITHUB_ACTIONS is true and LOG_LEVEL is DEBUG.

        Returns:
            True if data should be masked, False otherwise.
        """
        github_actions = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        log_level = os.environ.get("LOG_LEVEL", "").upper() == "DEBUG"
        return github_actions and log_level

    @classmethod
    def mask_message(cls, message: str) -> str:
        """Apply masking to a log message based on environment conditions.

        Args:
            message: The original log message.

        Returns:
            The masked log message.
        """
        masked_message = message

        # Apply conditional masking (hostnames, paths, etc.)
        if cls._should_mask():
            # Redact screens (content between markers used in engine.py)
            masked_message = re.sub(
                r"(--- .*? ---\n)(.*?)(\n--- End .*? ---)",
                r"\1[INFO: Full screen content redacted from stdout. Check log files on Runner server for details.]\3",
                masked_message,
                flags=re.DOTALL,
            )

            # Masking for parameters "--yaml-file /path/to/script.yaml" or "-f ..." or "-y ..."
            masked_message = re.sub(
                r"(--yaml-file|-f|-y)\s+[^\s]+",
                r"--yaml-file [MASKED_YAML_FILE]",
                masked_message,
            )
            # Masking for "--host <hostname>" or "-h ..."
            masked_message = re.sub(
                r"(--host|-h)\s+[^\s]+", r"--host [MASKED_HOST]", masked_message
            )
            # Masking for "--env /path/to/.env.file" or "-e ..."
            masked_message = re.sub(
                r"(--env|-e)\s+[^\s]+",
                r"--env [MASKED_ENV_FILE]",
                masked_message,
            )
            # Masking for "Loading environment variables from /path/to/.env.file"
            masked_message = re.sub(
                r"Loading environment variables from\s+[^\s]+",
                r"Loading environment variables from [MASKED_ENV_FILE]",
                masked_message,
            )
            # Masking for "Testing connectivity to <hostname>:<port>"
            masked_message = re.sub(
                r"Testing connectivity to\s+[^:]+:\d+",
                r"Testing connectivity to [MASKED_HOST]:[MASKED_PORT]",
                masked_message,
            )
            # Masking for "Starting new TN5250 session '<session-name>' for host: <hostname>"
            masked_message = re.sub(
                r"Starting new TN5250 session\s+\'[^\']+\'\s+for host:\s+[^\s]+",
                r"Starting new TN5250 session '[MASKED_SESSION_NAME]' for host: [MASKED_HOST]",
                masked_message,
            )
            # Masking for "Executing: tn5250 ... <hostname> with window size ..."
            masked_message = re.sub(
                r"(Executing:\s+tn5250\s+.*?)(?:ssl:)?([^\s:]+)(?::(\d+))?(\s+with window size)",
                r"\1[MASKED_HOST]\4",
                masked_message,
            )

            # Masking for HMC connection port
            masked_message = re.sub(
                r"(Connecting via HMC Proxy on port )\d+",
                r"\1[MASKED_PORT]",
                masked_message,
            )

            # Masking for debug capture paths
            masked_message = re.sub(
                r"(Screen saved to logs/captures/)[^/]+/",
                r"\1[MASKED_HOST]/",
                masked_message,
            )

            # Masking for search and move/extract results
            lpar_name = os.environ.get("TN5250_HOST", "")
            if lpar_name:
                # Mask LPAR name when it appears in quotes (found text)
                masked_message = re.sub(
                    rf'Found "{re.escape(lpar_name)}"',
                    r'Found "[MASKED_HOST]"',
                    masked_message,
                    flags=re.IGNORECASE,
                )

                # Masking for screen title LPAR name
                masked_message = re.sub(
                    rf"(\[Screen\].*?)\s+{re.escape(lpar_name)}\b",
                    r"\1 ***",
                    masked_message,
                    flags=re.IGNORECASE,
                )

            # Masking for capture file paths (simplify to filename)
            masked_message = re.sub(
                r"(\[Capture\] Saved to ).*/([^/]+)",
                r"\1file \2",
                masked_message,
            )

            # Masking for tmux session termination messages
            masked_message = re.sub(
                r"(Terminating tmux session:? (robot-)?'?)robot-[^ '.]+",
                r"\1robot-[MASKED_HOST]",
                masked_message,
            )
            masked_message = re.sub(
                r"(Session 'robot-)[^']+",
                r"\1[MASKED_HOST]",
                masked_message,
            )

        # Mask sensitive environment variables (Always active)
        sensitive_vars = ["TN5250_PASSWORD", "HMC_PWD"]
        custom_sensitive = os.environ.get("ROBOT_SENSITIVE_VARS", "")
        if custom_sensitive:
            sensitive_vars.extend(
                [v.strip() for v in custom_sensitive.split(",") if v.strip()]
            )

        for var_name in sensitive_vars:
            val = os.environ.get(var_name)
            if val:
                masked_message = masked_message.replace(val, "********")

        return masked_message

if __name__ == "__main__":
    import sys
    # Read from stdin if no arguments, otherwise join arguments
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        input_text = sys.stdin.read().strip()

    if input_text:
        print(LogMasker.mask_message(input_text))
