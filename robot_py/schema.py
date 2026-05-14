from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import yaml
import os
import re


@dataclass
class Action:
    """Base class for all automation actions.

    Attributes:
        type: The type of action to perform.
        description: An optional human-readable description of the action.
    """

    type: str
    description: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Action":
        """Create an Action instance from a dictionary.

        Args:
            data: A dictionary containing action parameters, including 'type'.

        Returns:
            An instance of a specific Action subclass.

        Raises:
            ValueError: If the action type is unknown.
        """
        action_type = data.get("type")
        if action_type == "send_text":
            return SendTextAction(**data)
        elif action_type == "send_key":
            return SendKeyAction(**data)
        elif action_type == "wait_for_text":
            return WaitForTextAction(**data)
        elif action_type == "sleep":
            return SleepAction(**data)
        elif action_type == "capture":
            return CaptureAction(**data)
        elif action_type == "press_key_if_text_present":
            return PressKeyIfTextPresentAction(**data)
        elif action_type == "move_cursor":
            return MoveCursorAction(**data)
        elif action_type == "search_and_move_cursor":
            return SearchAndMoveCursorAction(**data)
        elif action_type == "search_extract_and_send":
            return SearchExtractAndSendAction(**data)
        elif action_type == "extract_at_cursor_and_send":
            return ExtractAtCursorAndSendAction(**data)
        else:
            raise ValueError(f"Unknown action type: {action_type}")


@dataclass
class SendTextAction(Action):
    """Action to send literal text to the terminal.

    Attributes:
        text: The string to be sent.
    """

    text: str = ""


@dataclass
class SendKeyAction(Action):
    """Action to send a special key (e.g., F3, Enter) to the terminal.

    Attributes:
        key: The logical name of the key to send.
    """

    key: str = ""


@dataclass
class WaitForTextAction(Action):
    """Action to wait for specific text to appear on the screen.

    Attributes:
        text: The string to wait for.
        row: Starting row for the search area (1-indexed).
        col: Starting column for the search area (1-indexed).
        end_row: Ending row for the search area (1-indexed).
        end_col: Ending column for the search area (1-indexed).
        is_message_line: If True, only search the terminal's message line.
        timeout_seconds: Maximum time to wait in seconds.
    """

    text: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    end_row: Optional[int] = None
    end_col: Optional[int] = None
    is_message_line: Optional[bool] = None
    timeout_seconds: int = 10


@dataclass
class SleepAction(Action):
    """Action to pause execution for a specified duration.

    Attributes:
        seconds: Number of seconds to sleep.
    """

    seconds: float = 0.0


@dataclass
class CaptureAction(Action):
    """Action to capture the current screen content to a file.

    Attributes:
        filename: Optional base name for the capture file.
    """

    filename: Optional[str] = None


@dataclass
class PressKeyIfTextPresentAction(Action):
    """Action to press a key only if specific text is present.

    Attributes:
        text: The string to look for.
        key: The key to press if the text is found.
        row: Starting row for the search area (1-indexed).
        col: Starting column for the search area (1-indexed).
        end_row: Ending row for the search area (1-indexed).
        end_col: Ending column for the search area (1-indexed).
        is_message_line: If True, only search the terminal's message line.
        wait_ms: Optional milliseconds to wait before checking.
        timeout_seconds: Maximum time to wait for the text to appear.
    """

    text: str = ""
    key: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    end_row: Optional[int] = None
    end_col: Optional[int] = None
    is_message_line: Optional[bool] = None
    wait_ms: Optional[int] = None
    timeout_seconds: int = 2


@dataclass
class MoveCursorAction(Action):
    """Action to move the cursor to specific coordinates.

    Attributes:
        row: Target row (1-indexed).
        col: Target column (1-indexed).
    """

    row: int = 1
    col: int = 1


@dataclass
class SearchAndMoveCursorAction(Action):
    """Action to find text in a block and move the cursor to that row.

    Attributes:
        text: The string to search for.
        row: Starting row for the search area (1-indexed).
        col: Starting column for the search area (1-indexed).
        end_row: Ending row for the search area (1-indexed).
        end_col: Ending column for the search area (1-indexed).
        target_col: The column to move the cursor to on the matching row.
        timeout_seconds: Maximum time to wait for the text.
    """

    text: str = ""
    row: int = 1
    col: int = 1
    end_row: int = 1
    end_col: int = 1
    target_col: int = 1
    timeout_seconds: int = 10


@dataclass
class SearchExtractAndSendAction(Action):
    """Action to find text, extract a value from the same row, and send it.

    Attributes:
        text: The string to search for.
        row: Starting row for the search area (1-indexed).
        col: Starting column for the search area (1-indexed).
        end_row: Ending row for the search area (1-indexed).
        end_col: Ending column for the search area (1-indexed).
        extract_col: The starting column to extract text from.
        extract_length: The number of characters to extract.
        timeout_seconds: Maximum time to wait for the search text.
    """

    text: str = ""
    row: int = 1
    col: int = 1
    end_row: int = 1
    end_col: int = 1
    extract_col: int = 1
    extract_length: int = 1
    timeout_seconds: int = 10


@dataclass
class ExtractAtCursorAndSendAction(Action):
    """Action to extract text at the current cursor position and send it.

    Attributes:
        length: Number of characters to extract.
    """

    length: int = 1


@dataclass
class RobotDefaults:
    """Default configuration values for the robot script.

    Attributes:
        wait_timeout: Default timeout for wait actions in seconds.
        typing_delay_ms: Default delay between keystrokes in milliseconds.
    """

    wait_timeout: int = 5
    typing_delay_ms: int = 50


@dataclass
class RobotScript:
    """Represents a complete automation script.

    Attributes:
        name: Name of the script.
        steps: List of Action objects to execute.
        description: Optional description of the script's purpose.
        tmux_session: Name of the tmux session to use.
        defaults: Default settings for the script.
    """

    name: str
    steps: List[Action]
    description: Optional[str] = None
    tmux_session: str = "5250_robot"
    defaults: RobotDefaults = field(default_factory=RobotDefaults)


def parse_robot_script(yaml_path: str) -> RobotScript:
    """Load and parse a YAML automation script.

    Environment variables in the YAML file (e.g., ${VAR_NAME} or
    ${VAR_NAME:-default}) are substituted during parsing.

    Args:
        yaml_path: Path to the YAML script file.

    Returns:
        A RobotScript object containing the parsed actions and metadata.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML content is invalid.
    """
    with open(yaml_path, "r") as f:
        content = f.read()

    # Process environment variables: ${VAR_NAME} or ${VAR_NAME:-default}
    def replace_env(match):
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) else ""
        return os.environ.get(var_name, default_val)

    processed_content = re.sub(r"\${(\w+)(?::-(.*?))?}", replace_env, content)

    data = yaml.safe_load(processed_content)

    steps = [Action.from_dict(step) for step in data.get("steps", [])]

    defaults_data = data.get("defaults", {})
    defaults = RobotDefaults(
        wait_timeout=defaults_data.get("wait_timeout", 5),
        typing_delay_ms=defaults_data.get("typing_delay_ms", 50),
    )

    return RobotScript(
        name=data.get("name", "Unnamed Robot"),
        description=data.get("description"),
        tmux_session=data.get("tmux_session", "5250_robot"),
        defaults=defaults,
        steps=steps,
    )
