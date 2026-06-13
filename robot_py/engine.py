import subprocess
import os
import re
import time
from datetime import datetime
from typing import Optional, List, Tuple, Union, Dict, Any
from .schema import (
    parse_robot_script,
    Action,
    SendTextAction,
    SendKeyAction,
    WaitForTextAction,
    SleepAction,
    CaptureAction,
    PressKeyIfTextPresentAction,
    MoveCursorAction,
    SearchAndMoveCursorAction,
    SearchExtractAndSendAction,
    ExtractAtCursorAndSendAction,
    SearchAndCompareAction,
    CompareAction,
    TerminateAction,
)
from .logger import logger

KEY_MAP = {
    "Enter": "C-m",
    "Field_exit": "C-x",
    "Reset": "C-r",
    "Tab": "Tab",
    "F1": "F1",
    "F2": "F2",
    "F3": "F3",
    "F4": "F4",
    "F5": "F5",
    "F6": "F6",
    "F7": "F7",
    "F8": "F8",
    "F9": "F9",
    "F10": "F10",
    "F11": "F11",
    "F12": "F12",
    "F13": "S-F1",
    "F14": "S-F2",
    "F15": "S-F3",
    "F16": "S-F4",
    "F17": "S-F5",
    "F18": "S-F6",
    "F19": "S-F7",
    "F20": "S-F8",
    "F21": "S-F9",
    "F22": "S-F10",
    "F23": "S-F11",
    "F24": "S-F12",
    "Page_up": "PPage",
    "Page_down": "NPage",
    "Print": "C-p",
    "Help": "S-F1",
}

SUPPORTED_27x132 = ["IBM-3477-FC", "IBM-3477-FG", "IBM-3180-2"]
SUPPORTED_24x80 = [
    "IBM-3179-2",
    "IBM-3196-A1",
    "IBM-5292-2",
    "IBM-5291-1",
    "IBM-5251-11",
]


def validate_environment():
    """Validate that required environment variables are set and non-empty.

    Checks for required variables based on whether a direct IP connection
    or an HMC 5250 Proxy connection is being used. Also validates that
    TN5250_DEVICE_TYPE is a supported terminal type.

    Raises:
        ValueError: If any required environment variable is missing or empty,
            or if TN5250_DEVICE_TYPE is unsupported.
    """
    hmc_host = os.environ.get("HMC_HOST")
    missing_vars = []

    # Required for both
    common_required = ["TN5250_USER", "TN5250_PASSWORD"]
    for var in common_required:
        if not os.environ.get(var):
            missing_vars.append(var)

    if hmc_host:
        # HMC specific required variables
        hmc_required = [
            "HMC_USER",
            "HMC_PWD",
            "HMC_SYSNAME",
            "HMC_LPARNAME",
            "HMC_SESSION_KEY",
        ]
        for var in hmc_required:
            if not os.environ.get(var):
                missing_vars.append(var)
    else:
        # Direct IP specific required variables
        if not os.environ.get("TN5250_HOST"):
            missing_vars.append("TN5250_HOST")

    if missing_vars:
        mode = "HMC Proxy" if hmc_host else "Direct IP"
        raise ValueError(
            f"Missing required environment variables for {mode} connection: {', '.join(missing_vars)}"
        )

    # Validate device type if it's set
    device_type = os.environ.get("TN5250_DEVICE_TYPE")
    if device_type and device_type not in (SUPPORTED_27x132 + SUPPORTED_24x80):
        raise ValueError(f"Unsupported TN5250_DEVICE_TYPE: {device_type}")


class TerminationException(Exception):
    """Custom exception to signal that the robot should terminate immediately."""

    pass


class RobotEngine:
    """The core engine responsible for executing automation scripts.

    This class manages the interaction with a tmux session, sends keystrokes,
    and captures/analyzes the terminal screen.

    Attributes:
        script: The parsed RobotScript object.
        session: The name of the tmux session.
        host: The target host for the 5250 connection.
        log_level: The current logging level.
        last_logged_title: The title of the last captured screen.
        max_rows: Maximum rows for the terminal device type.
        max_cols: Maximum columns for the terminal device type.
    """

    def _is_hmc_sensitive(self, pane_content: str) -> bool:
        """Check if the current screen is a sensitive HMC selection screen.

        Condition: HMC_HOST is set, GITHUB_ACTIONS is true, LOG_LEVEL is debug,
        and the screen contains sensitive headings on line 1. Heading list is
        configurable via ROBOT_REDACTED_SCREENS environment variable.

        Args:
            pane_content: The raw captured pane content.

        Returns:
            True if the screen is sensitive and should be redacted.
        """
        if not (
            os.environ.get("HMC_HOST")
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and self.log_level == "DEBUG"
        ):
            return False

        lines = pane_content.splitlines()
        if not lines:
            return False

        line_1 = lines[0]
        sensitive_headings = [
            "Remote 5250 Console System Selection",
            "Remote 5250 Console Partition Selection",
        ]
        # Add custom redacted screens from environment variable
        custom_redacted = os.environ.get("ROBOT_REDACTED_SCREENS", "")
        if custom_redacted:
            sensitive_headings.extend(
                [s.strip() for s in custom_redacted.split(",") if s.strip()]
            )

        return any(heading in line_1 for heading in sensitive_headings)

    def _get_redacted_content(self, pane_content: str) -> str:
        """Return a redacted version of the screen content if it's sensitive.

        Args:
            pane_content: The raw captured pane content.

        Returns:
            Redacted explanatory message if sensitive, original content otherwise.
        """
        if self._is_hmc_sensitive(pane_content):
            lines = pane_content.splitlines()
            title = lines[0].strip() if lines else "HMC Selection Screen"
            return f"--- SENSITIVE HMC SCREEN REDACTED ---\nScreen: {title}\nThis screen contains customer-specific configuration and has been hidden for security in GitHub Actions logs.\n--- END REDACTION ---"
        return pane_content

    def __init__(self, yaml_path: str):
        """Initialize the RobotEngine.

        Args:
            yaml_path: Path to the YAML script file.

        Raises:
            ValueError: If the environment is invalid or the device type is unsupported.
        """
        validate_environment()
        self.script = parse_robot_script(yaml_path)
        self.session = os.environ.get("TMUX_SESSION", self.script.tmux_session)
        self.host = os.environ.get("TN5250_HOST", "unknown_host")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.last_logged_title = ""
        self.history_screens: List[str] = []  # Initialize screen history
        self.runtime_variables: Dict[str, str] = {
            k: str(v) for k, v in os.environ.items()
        }

        device_type = os.environ.get("TN5250_DEVICE_TYPE", "IBM-3477-FC")
        if device_type in SUPPORTED_27x132:
            self.max_rows = 27
            self.max_cols = 132
        elif device_type in SUPPORTED_24x80:
            self.max_rows = 24
            self.max_cols = 80
        else:
            raise ValueError(f"Unsupported TN5250_DEVICE_TYPE: {device_type}")

    def _get_screen_title(
        self, pane_content: str, current_rows: Optional[int] = None
    ) -> str:
        """Extracts the screen title from the pane content.

        Args:
            pane_content: The raw text content of the pane.
            current_rows: The current active row count to restrict title scanning to.

        Returns:
            The detected screen title, or an empty string if no title is found.
        """
        lines = pane_content.splitlines()
        scan_limit = 5
        if current_rows is not None:
            scan_limit = min(5, current_rows)
        for line in lines[
            :scan_limit
        ]:  # Only scan up to the first 5 or current_rows lines for a title.
            trimmed = line.strip()
            if trimmed:
                return trimmed
        return ""

    def run_tmux(self, args: List[str]) -> str:
        """Execute a tmux command and return its output.

        Args:
            args: List of arguments for the tmux command.

        Returns:
            The standard output of the tmux command.

        Raises:
            RuntimeError: If the tmux session does not exist or the command fails.
        """
        # Always check if the tmux session exists before attempting any command.
        if not self.check_session_exists():
            raise RuntimeError(f"Tmux session '{self.session}' not found.")

        cmd = ["tmux"] + args
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_output = result.stderr or result.stdout or "No output"
            raise RuntimeError(
                f"Tmux command failed: [{' '.join(cmd)}]. Error: {error_output.strip()}"
            )

        return result.stdout

    def check_session_exists(self) -> bool:
        """Check if the configured tmux session exists.

        Returns:
            True if the session exists, False otherwise.
        """
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session], capture_output=True
        )
        return result.returncode == 0

    def terminate_session(self):
        """Kill the tmux session associated with this robot."""
        if self.check_session_exists():
            logger.info(f"Terminating tmux session: {self.session}")
            subprocess.run(
                ["tmux", "kill-session", "-t", self.session], capture_output=True
            )
        else:
            logger.debug(f"Session {self.session} already gone, no need to terminate.")

    def _perform_comparison(
        self, actual: str, expected: str, operator: str, raw_expected: str = ""
    ) -> bool:
        """Perform a comparison between an extracted value and an expected value.

        Supports numeric and string operators. Numeric operators (EQ, NE, LE, LT, GE, GT)
        cast values to float. String operators are SAME, CONTAINS, NOT_SAME, NOT_CONTAINS.

        Args:
            actual: The value extracted from the screen.
            expected: The value to compare against (substituted).
            operator: The comparison operator.
            raw_expected: The original expected value (unsubstituted, for error reporting).

        Returns:
            True if the comparison is successful, False otherwise.

        Raises:
            TerminationException: If numeric conversion fails for numeric operators.
            ValueError: If an unknown operator is provided.
        """
        numeric_operators = ["EQ", "NE", "LE", "LT", "GE", "GT"]
        string_operators = ["SAME", "CONTAINS", "NOT_SAME", "NOT_CONTAINS"]

        if operator in numeric_operators:
            try:
                actual_num = float(actual)
            except ValueError:
                raise TerminationException(
                    f"Compare data is incompatible: Extracted value '{actual}' is not numeric for operator {operator}"
                )
            try:
                expected_num = float(expected)
            except ValueError:
                if "{{" in raw_expected:
                    source = f"run time variable '{raw_expected}'"
                else:
                    source = f"expected value '{raw_expected}'" if raw_expected else "expected value"
                raise TerminationException(
                    f"Compare data is incompatible: The {source} resolved to '{expected}', which is not numeric for operator {operator}"
                )

            if operator == "EQ":
                return actual_num == expected_num
            elif operator == "NE":
                return actual_num != expected_num
            elif operator == "LE":
                return actual_num <= expected_num
            elif operator == "LT":
                return actual_num < expected_num
            elif operator == "GE":
                return actual_num >= expected_num
            elif operator == "GT":
                return actual_num > expected_num
        elif operator in string_operators:
            if operator == "SAME":
                return actual == expected
            elif operator == "NOT_SAME":
                return actual != expected
            elif operator == "CONTAINS":
                return expected in actual
            elif operator == "NOT_CONTAINS":
                return expected not in actual
        else:
            raise ValueError(f"Unknown comparison operator: {operator}")

        return False

    def _substitute_runtime_vars(self, data: Any) -> Any:
        """Recursively substitute runtime variables in strings or lists.

        Supports {{VAR_NAME}}.

        Args:
            data: The data structure to process (str, list, or dict).

        Returns:
            The data structure with runtime variables substituted.
        """
        if isinstance(data, dict):
            return {k: self._substitute_runtime_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_runtime_vars(item) for item in data]
        elif isinstance(data, str):

            def replace_var(match):
                var_name = match.group(1)
                return self.runtime_variables.get(var_name, match.group(0))

            return re.sub(r"\{\{(\w+)\}\}", replace_var, data)
        return data

    def validate_coords(self, row: int, col: int):
        """Validate that the given coordinates are within terminal bounds.

        Args:
            row: The row number (1-indexed).
            col: The column number (1-indexed).

        Raises:
            ValueError: If the coordinates are out of bounds.
        """
        if not (1 <= row <= self.max_rows):
            raise ValueError(f"Row {row} out of bounds (1-{self.max_rows})")
        if not (1 <= col <= self.max_cols):
            raise ValueError(f"Column {col} out of bounds (1-{self.max_cols})")

    def validate_block(self, row: int, col: int, end_row: int, end_col: int):
        """Validate that the given block coordinates are valid and within bounds.

        Args:
            row: Starting row (1-indexed).
            col: Starting column (1-indexed).
            end_row: Ending row (1-indexed).
            end_col: Ending column (1-indexed).

        Raises:
            ValueError: If any coordinate is out of bounds or the block is invalid.
        """
        self.validate_coords(row, col)
        self.validate_coords(end_row, end_col)
        if row > end_row or col > end_col:
            raise ValueError(f"Invalid block: ({row},{col}) to ({end_row},{end_col})")

    def get_cursor_position(self) -> Tuple[int, int]:
        """Get the current cursor position in the tmux pane.

        Returns:
            A tuple of (row, col), both 1-indexed.
        """
        # tmux uses 0-indexed coords, robot uses 1-indexed
        res = self.run_tmux(
            ["display-message", "-p", "-t", self.session, "#{cursor_y},#{cursor_x}"]
        )
        y, x = map(int, res.strip().split(","))
        return y + 1, x + 1

    def move_cursor(self, target_row: int, target_col: int):
        """Move the cursor to the specified coordinates using arrow keys.

        Args:
            target_row: Target row (1-indexed).
            target_col: Target column (1-indexed).
        """
        self.validate_coords(target_row, target_col)
        curr_row, curr_col = self.get_cursor_position()

        row_diff = target_row - curr_row
        col_diff = target_col - curr_col

        if row_diff > 0:
            for _ in range(row_diff):
                self.run_tmux(["send-keys", "-t", self.session, "Down"])
        elif row_diff < 0:
            for _ in range(-row_diff):
                self.run_tmux(["send-keys", "-t", self.session, "Up"])

        if col_diff > 0:
            for _ in range(col_diff):
                self.run_tmux(["send-keys", "-t", self.session, "Right"])
        elif col_diff < 0:
            for _ in range(-col_diff):
                self.run_tmux(["send-keys", "-t", self.session, "Left"])

    def _detect_current_screen_dimensions(self, pane_content: str) -> Tuple[int, int]:
        """Detect current active screen dimensions based on 5250 status line.

        For 27x132 capable devices, checks if the status line has '/' at col 76 on line 28 (DS4)
        or line 25 (DS3). Defaults to 24x80 if not found or if the device is a 24x80 only device.

        Args:
            pane_content: The raw captured pane content.

        Returns:
            Tuple of (rows, cols) representing current mode.
        """
        if self.max_rows < 27:
            return 24, 80

        lines = pane_content.splitlines()

        # Check line 28 (0-indexed 27) for 27x132 screen
        if len(lines) >= 28:
            line_28 = lines[27]
            if len(line_28) >= 76 and line_28[75] == "/":
                return 27, 132

        # Check line 25 (0-indexed 24) for 24x80 screen
        if len(lines) >= 25:
            line_25 = lines[24]
            if len(line_25) >= 76 and line_25[75] == "/":
                return 24, 80

        return 24, 80

    def capture_pane(self) -> str:
        """Capture the current content of the tmux pane.

        Also detects and logs screen title changes based on the first few lines.

        Returns:
            The raw text content of the pane.
        """
        # Capture the entire possible buffer up to self.max_rows plus any extra status lines (e.g., 28 lines)
        # To capture status line at row 28, we need 28 lines (indices 0 to 27)
        max_capture_rows = 28 if self.max_rows == 27 else 25
        pane_content = self.run_tmux(
            [
                "capture-pane",
                "-t",
                self.session,
                "-p",
                "-S",
                "0",
                "-E",
                str(max_capture_rows - 1),
            ]
        )
        current_rows, _ = self._detect_current_screen_dimensions(pane_content)
        new_title = self._get_screen_title(pane_content, current_rows)

        # Apply redaction for logging and history if needed
        redacted_content = self._get_redacted_content(pane_content)
        is_redacted = redacted_content != pane_content

        if new_title and new_title != self.last_logged_title:
            display_title = (
                "[REDACTED]" if is_redacted else new_title
            )
            logger.info(f"[Screen] {display_title}")
            self.last_logged_title = new_title
            # Store unique screens in history (using redacted content if applicable)
            if not self.history_screens or self.history_screens[-1] != redacted_content:
                self.history_screens.append(redacted_content)
            # Keep history to a reasonable size, e.g., last 20 screens
            if len(self.history_screens) > 20:
                self.history_screens.pop(0)

        return pane_content

    def find_text_in_buffer(
        self,
        pane_content: str,
        text: Union[str, List[str]],
        row: Optional[int] = None,
        col: Optional[int] = None,
        end_row: Optional[int] = None,
        end_col: Optional[int] = None,
        is_message_line: Optional[bool] = None,
    ) -> bool:
        """Search for text within a specific area of the pane content.

        Supports searching for a single string or any string in a list.

        Args:
            pane_content: The raw text content of the pane.
            text: The string or list of strings to search for.
            row: Starting row (1-indexed).
            col: Starting column (1-indexed).
            end_row: Ending row (1-indexed).
            end_col: Ending column (1-indexed).
            is_message_line: If True, search only the message line.

        Returns:
            True if any of the search strings were found, False otherwise.
        """
        search_texts = [text] if isinstance(text, str) else text
        for t in search_texts:
            if self._find_single_text_in_buffer(
                pane_content, t, row, col, end_row, end_col, is_message_line
            ):
                return True
        return False

    def _find_single_text_in_buffer(
        self,
        pane_content: str,
        text: str,
        row: Optional[int] = None,
        col: Optional[int] = None,
        end_row: Optional[int] = None,
        end_col: Optional[int] = None,
        is_message_line: Optional[bool] = None,
    ) -> bool:
        """Helper to search for a single text string."""
        current_rows, current_cols = self._detect_current_screen_dimensions(
            pane_content
        )
        lines = pane_content.splitlines()[:current_rows]

        if is_message_line:
            message_line_index = current_rows - 1
            line = lines[message_line_index] if len(lines) > message_line_index else ""
            return text in line
        elif (
            row is not None
            and col is not None
            and end_row is not None
            and end_col is not None
        ):
            # Coordinates are 1-indexed in YAML
            # Validate against dynamic screen dimensions to prevent reading beyond
            if (
                row > current_rows
                or end_row > current_rows
                or col > current_cols
                or end_col > current_cols
            ):
                raise ValueError(
                    f"Block coordinates ({row},{col}) to ({end_row},{end_col}) out of active bounds for {current_rows}x{current_cols} screen"
                )
            search_area_lines = lines[row - 1 : end_row]
            search_area = "\n".join(
                [line[col - 1 : end_col] for line in search_area_lines]
            )
            return text in search_area
        elif row is not None:
            if row > current_rows or (col is not None and col > current_cols):
                raise ValueError(
                    f"Coordinates ({row},{col or 1}) out of active bounds for {current_rows}x{current_cols} screen"
                )
            line = lines[row - 1] if len(lines) > row - 1 else ""
            if col is not None:
                return text in line[col - 1 :]
            else:
                return text in line
        else:
            # For full buffer search, search only the actively displayed lines
            trimmed_content = "\n".join(lines)
            return text in trimmed_content

    def find_text_in_block(
        self,
        pane_content: str,
        text: str,
        row: int,
        col: int,
        end_row: int,
        end_col: int,
    ) -> Optional[int]:
        """Find the row number of a text string within a specified block.

        Args:
            pane_content: The raw text content of the pane.
            text: The string to search for.
            row: Starting row (1-indexed).
            col: Starting column (1-indexed).
            end_row: Ending row (1-indexed).
            end_col: Ending column (1-indexed).

        Returns:
            The 1-indexed row number if found, None otherwise.
        """
        self.validate_block(row, col, end_row, end_col)
        lines = pane_content.splitlines()
        for i in range(row - 1, end_row):
            if i >= len(lines):
                break
            line_part = lines[i][col - 1 : end_col]
            if text in line_part:
                return i + 1
        return None

    def wait_for_text_internal(
        self,
        text: Union[str, List[str]],
        timeout: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
        end_row: Optional[int] = None,
        end_col: Optional[int] = None,
        is_message_line: Optional[bool] = None,
    ) -> Tuple[bool, str]:
        """Wait for text to appear, returning success status and last content.

        Args:
            text: The string to wait for.
            timeout: Maximum wait time in seconds.
            row: Starting row (1-indexed).
            col: Starting column (1-indexed).
            end_row: Ending row (1-indexed).
            end_col: Ending column (1-indexed).
            is_message_line: If True, search only the message line.

        Returns:
            A tuple of (found, last_pane_content).
        """
        start_time = time.time()
        expiry = start_time + timeout
        last_content = ""

        while time.time() < expiry:
            last_content = self.capture_pane()
            if self.find_text_in_buffer(
                last_content, text, row, col, end_row, end_col, is_message_line
            ):
                return True, last_content
            time.sleep(0.5)

        return False, last_content

    def wait_for_text(
        self,
        text: str,
        timeout: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
        end_row: Optional[int] = None,
        end_col: Optional[int] = None,
        is_message_line: Optional[bool] = None,
    ):
        """Wait for text to appear, raising an error if it doesn't within the timeout.

        Args:
            text: The string to wait for.
            timeout: Maximum wait time in seconds.
            row: Starting row (1-indexed).
            col: Starting column (1-indexed).
            end_row: Ending row (1-indexed).
            end_col: Ending column (1-indexed).
            is_message_line: If True, search only the message line.

        Raises:
            RuntimeError: If the text is not found within the timeout.
        """
        found, last_content = self.wait_for_text_internal(
            text, timeout, row, col, end_row, end_col, is_message_line
        )
        if found:
            return

        error_msg = f'Timeout waiting for text: "{text}" after {timeout}s.\n--- Current Screen Content ---\n{last_content}\n--- End Content ---'
        raise RuntimeError(error_msg)

    def capture_debug_screen(self, action_name: str):
        """Capture the screen content for debugging purposes.

        Only captures if the log level is set to DEBUG.

        Args:
            action_name: A name for the capture, used in the filename.
        """
        if self.log_level != "DEBUG":
            return
        try:
            pane_content = self.capture_pane()
            redacted_content = self._get_redacted_content(pane_content)

            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            capture_dir = os.path.join(os.getcwd(), "logs", "captures", self.host)
            os.makedirs(capture_dir, exist_ok=True)

            filename = f"{timestamp}_{action_name}.txt"
            save_path = os.path.join(capture_dir, filename)

            with open(save_path, "w") as f:
                f.write(redacted_content)
            logger.debug(
                f"[Debug Capture] Screen saved to {os.path.relpath(save_path)}"
            )
        except Exception as e:
            logger.warning(f"[Debug Capture] Failed to capture screen: {str(e)}")

    def execute_steps(self, steps: List[Action]):
        """Execute a sequence of automation steps.

        Args:
            steps: List of Action objects to execute.
        """
        for i, step in enumerate(steps):
            description = self._substitute_runtime_vars(step.description)
            desc = f" ({description})" if description else ""
            logger.info(f"[Step {i + 1}/{len(steps)}] {step.type}{desc}")
            self.execute_step(step)
            self.capture_pane()

    def execute_step(self, step: Action):
        """Execute a single automation step.

        Args:
            step: The Action object to perform.
        """
        if isinstance(step, SendTextAction):
            text = self._substitute_runtime_vars(step.text)
            self.run_tmux(["send-keys", "-l", "-t", self.session, text])
        elif isinstance(step, SendKeyAction):
            key = self._substitute_runtime_vars(step.key)
            key_to_send = KEY_MAP.get(key, key)
            logger.debug(f"[Key Send] Sending key: '{key}' -> tmux: '{key_to_send}'")

            if self.log_level == "DEBUG":
                before = self.capture_pane()
                redacted_before = self._get_redacted_content(before)
                logger.debug(
                    f"\n--- Before {key} ---\n{redacted_before}\n--- End Before {key} ---"
                )

            self.run_tmux(["send-keys", "-t", self.session, key_to_send])
            time.sleep(0.25)

            if self.log_level == "DEBUG":
                after = self.capture_pane()
                redacted_after = self._get_redacted_content(after)
                logger.debug(
                    f"\n--- After {key} ---\n{redacted_after}\n--- End After {key} ---"
                )

            self.capture_debug_screen(f"after_send_key_{key}")
        elif isinstance(step, SleepAction):
            time.sleep(step.seconds)
        elif isinstance(step, CaptureAction):
            current_screen_content = self.capture_pane()
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            host_dir = os.path.join(os.getcwd(), "captures", self.host)
            os.makedirs(host_dir, exist_ok=True)

            filename = self._substitute_runtime_vars(step.filename)
            base_name = filename or "capture"

            if "Sign On" in current_screen_content:
                # Find the last but one screen from history
                prev_screen_content = ""
                for i in range(len(self.history_screens) - 2, -1, -1):
                    if self._get_screen_title(
                        self.history_screens[i]
                    ) != self._get_screen_title(current_screen_content):
                        prev_screen_content = self.history_screens[i]
                        break

                if prev_screen_content:
                    capture_content = (
                        prev_screen_content.rstrip() + "\n\nSign off successful\n"
                    )
                    final_filename = f"{base_name}_signoff_success_{timestamp}.txt"
                else:
                    # Fallback if no distinct previous screen found, but still sign on
                    capture_content = (
                        current_screen_content.rstrip() + "\n\nSign off successful\n"
                    )
                    final_filename = (
                        f"{base_name}_signoff_success_fallback_{timestamp}.txt"
                    )
            else:
                capture_content = self._get_redacted_content(current_screen_content)
                final_filename = f"{base_name}_{timestamp}.txt"

            save_path = os.path.join(host_dir, final_filename)

            with open(save_path, "w") as f:
                f.write(capture_content)
            logger.info(f"[Capture] Saved to {save_path}")
        elif isinstance(step, WaitForTextAction):
            text = self._substitute_runtime_vars(step.text)
            self.wait_for_text(
                text,
                step.timeout_seconds,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
                step.is_message_line,
            )
            safe_text = "".join([c if c.isalnum() else "_" for c in text])
            self.capture_debug_screen(f"after_wait_for_{safe_text}")
        elif isinstance(step, PressKeyIfTextPresentAction):
            settle_time = step.wait_ms / 1000.0 if step.wait_ms is not None else 0.25
            if settle_time > 0:
                time.sleep(settle_time)

            text = self._substitute_runtime_vars(step.text)
            key = self._substitute_runtime_vars(step.key)
            found, last_content = self.wait_for_text_internal(
                text,
                step.timeout_seconds,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
                step.is_message_line,
            )

            if found:
                press_key = KEY_MAP.get(key, key)
                logger.info(
                    f'[Condition] Text "{text}" found. Sending key: {key} -> tmux: {press_key}'
                )
                self.run_tmux(["send-keys", "-t", self.session, press_key])
                time.sleep(0.25)
            else:
                logger.info(
                    f'[Condition] Text "{text}" not found after {step.timeout_seconds}s. Skipping.'
                )
        elif isinstance(step, MoveCursorAction):
            logger.info(f"[Cursor] Moving to row {step.row}, col {step.col}")
            self.move_cursor(step.row, step.col)
        elif isinstance(step, SearchAndMoveCursorAction):
            text = self._substitute_runtime_vars(step.text)
            found, last_content = self.wait_for_text_internal(
                text,
                step.timeout_seconds,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
            )
            if not found:
                raise RuntimeError(
                    f'Timeout waiting for "{text}" in block for SearchAndMoveCursorAction'
                )

            match_row = self.find_text_in_block(
                last_content,
                text,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
            )
            logger.info(
                f'[SearchMove] Found "{text}" at row {match_row}. Moving cursor to col {step.target_col}'
            )
            self.move_cursor(match_row, step.target_col)
        elif isinstance(step, SearchExtractAndSendAction):
            text = self._substitute_runtime_vars(step.text)
            found, last_content = self.wait_for_text_internal(
                text,
                step.timeout_seconds,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
            )
            if not found:
                raise RuntimeError(
                    f'Timeout waiting for "{text}" in block for SearchExtractAndSendAction'
                )

            match_row = self.find_text_in_block(
                last_content,
                text,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
            )
            lines = last_content.splitlines()
            extracted = lines[match_row - 1][
                step.extract_col - 1 : step.extract_col - 1 + step.extract_length
            ].strip()
            logger.info(
                f'[SearchExtract] Found "{text}" at row {match_row}. Extracted "{extracted}" from col {step.extract_col}'
            )
            self.run_tmux(["send-keys", "-l", "-t", self.session, extracted])
        elif isinstance(step, ExtractAtCursorAndSendAction):
            row, col = self.get_cursor_position()
            last_content = self.capture_pane()
            lines = last_content.splitlines()
            extracted = lines[row - 1][col - 1 : col - 1 + step.length].strip()
            logger.info(
                f'[CursorExtract] Extracted "{extracted}" from row {row}, col {col}'
            )
            self.run_tmux(["send-keys", "-l", "-t", self.session, extracted])
        elif isinstance(step, CompareAction):
            expected = self._substitute_runtime_vars(step.expected)
            operator = step.operator
            extracted = ""

            if step.search_text:
                # Relative extraction
                search_text = self._substitute_runtime_vars(step.search_text)
                found, last_content = self.wait_for_text_internal(
                    search_text,
                    step.timeout_seconds,
                    step.row,
                    step.col,
                    step.end_row,
                    step.end_col,
                )
                if not found:
                    raise RuntimeError(
                        f'Timeout waiting for "{search_text}" in block for CompareAction'
                    )

                match_row = self.find_text_in_block(
                    last_content,
                    search_text,
                    step.row,
                    step.col,
                    step.end_row,
                    step.end_col,
                )
                lines = last_content.splitlines()
                extracted = lines[match_row - 1][
                    step.extract_col - 1 : step.extract_col - 1 + step.extract_length
                ].strip()
            elif (
                step.row is not None
                and step.col is not None
                and step.length is not None
            ):
                # Absolute extraction
                last_content = self.capture_pane()
                lines = last_content.splitlines()
                self.validate_coords(step.row, step.col + step.length - 1)
                extracted = lines[step.row - 1][
                    step.col - 1 : step.col - 1 + step.length
                ].strip()
            else:
                raise ValueError(
                    "CompareAction must specify either search_text or row/col/length"
                )

            logger.info(
                f"[Compare] Extracted '{extracted}', expected '{expected}' (operator: {operator})"
            )

            if self._perform_comparison(extracted, expected, operator, step.expected):
                logger.info("[Compare] Comparison succeeded.")
                self.execute_steps(step.if_true)
            else:
                logger.info("[Compare] Comparison failed.")
                self.execute_steps(step.if_false)
        elif isinstance(step, SearchAndCompareAction):
            text = self._substitute_runtime_vars(step.text)
            found, last_content = self.wait_for_text_internal(
                text,
                step.timeout_seconds,
                step.row,
                step.col,
                step.end_row,
                step.end_col,
                step.is_message_line,
            )

            if found:
                logger.info(f'[Compare] Search for "{text}" succeeded.')
                self.execute_steps(step.if_true)
            else:
                logger.info(f'[Compare] Search for "{text}" failed.')

                # Check if it was a line or positional check to report actual value
                # (either row is set, or is_message_line is set)
                is_block = (
                    step.row is not None
                    and step.col is not None
                    and step.end_row is not None
                    and step.end_col is not None
                )

                if not is_block:
                    lines = last_content.splitlines()
                    actual_value = ""
                    search_texts = (
                        [text] if isinstance(text, str) else text
                    )
                    max_len = max((len(t) for t in search_texts), default=0)

                    if step.is_message_line:
                        message_line_index = 26 if self.max_rows == 27 else 23
                        actual_value = (
                            lines[message_line_index]
                            if len(lines) > message_line_index
                            else ""
                        )
                    elif step.row is not None and step.col is not None:
                        # Positional check
                        if 1 <= step.row <= len(lines):
                            line = lines[step.row - 1]
                            actual_value = line[step.col - 1 : step.col - 1 + max_len]
                    elif step.row is not None:
                        # Line check
                        if 1 <= step.row <= len(lines):
                            actual_value = lines[step.row - 1]

                    msg = f'Search for text failed to find "{text}". Actual value found: "{actual_value}".'
                    logger.info(msg)
                    print(msg)

                self.execute_steps(step.if_false)
        elif isinstance(step, TerminateAction):
            reason = self._substitute_runtime_vars(step.reason)
            reason_str = f" Reason: {reason}" if reason else ""
            logger.info(f"[Terminate] Robot terminating.{reason_str}")
            raise TerminationException(reason)

    def run(self):
        """Execute all steps defined in the robot script.

        Iterates through the steps in self.script.steps and performs
        the corresponding actions.
        """
        name = self._substitute_runtime_vars(self.script.name)
        logger.info(f"Starting Robot: {name}")
        if self.script.description:
            description = self._substitute_runtime_vars(self.script.description)
            logger.info(f"Description: {description}")

        try:
            if not self.check_session_exists():
                logger.error(f"Error: Tmux session '{self.session}' not found.")
                logger.info(
                    f'Hint: Start your 5250 session in tmux: tmux new-session -s {self.session} "tn5250 <host>"'
                )
                return

            initial_pane_content = self.capture_pane()
            self.history_screens.append(initial_pane_content)

            self.execute_steps(self.script.steps)

            logger.info("Automation complete!")

        except TerminationException as e:
            logger.info(f"Automation terminated: {str(e)}")
        except Exception as e:
            logger.error(f"Error during automation: {str(e)}")
            try:
                error_pane_content = self.capture_pane()
                timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
                host_dir = os.path.join(os.getcwd(), "captures", self.host)
                os.makedirs(host_dir, exist_ok=True)
                error_filename = f"error_screen_{timestamp}.txt"
                error_save_path = os.path.join(host_dir, error_filename)
                with open(error_save_path, "w") as f:
                    f.write(error_pane_content.rstrip() + "\n\nError occurred\n")
                logger.error(f"[Error Capture] Screen saved to {error_save_path}")
            except Exception as capture_e:
                logger.warning(
                    f"Failed to capture screen during error: {str(capture_e)}"
                )
            raise  # Re-raise the original exception after capture

        finally:
            self.terminate_session()
