from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Type, ClassVar
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

    _registry: ClassVar[Dict[str, Type["Action"]]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "action_type"):
            Action._registry[cls.action_type] = cls

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
        data_copy = data.copy()
        action_type = data_copy.get("type")
        action_class = Action._registry.get(action_type)
        if action_class:
            return action_class(**data_copy)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def validate(self):
        """Basic validation for all actions. Overridden by subclasses."""
        pass


@dataclass
class SendTextAction(Action):
    """Action to send literal text to the terminal.

    Attributes:
        text: The string to be sent.
    """

    action_type = "send_text"
    text: str = ""


@dataclass
class SendKeyAction(Action):
    """Action to send a special key (e.g., F3, Enter) to the terminal.

    Attributes:
        key: The logical name of the key to send.
    """

    action_type = "send_key"
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

    action_type = "wait_for_text"
    text: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    end_row: Optional[int] = None
    end_col: Optional[int] = None
    is_message_line: Optional[bool] = None
    timeout_seconds: int = 10

    def __post_init__(self):
        if self.row is not None and self.row < 1:
            raise ValueError(f"Row must be >= 1, got {self.row}")
        if self.col is not None and self.col < 1:
            raise ValueError(f"Col must be >= 1, got {self.col}")


@dataclass
class SleepAction(Action):
    """Action to pause execution for a specified duration.

    Attributes:
        seconds: Number of seconds to sleep.
    """

    action_type = "sleep"
    seconds: float = 0.0


@dataclass
class CaptureAction(Action):
    """Action to capture the current screen content to a file.

    Attributes:
        filename: Optional base name for the capture file.
    """

    action_type = "capture"
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

    action_type = "press_key_if_text_present"
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

    action_type = "move_cursor"
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

    action_type = "search_and_move_cursor"
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

    action_type = "search_extract_and_send"
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

    action_type = "extract_at_cursor_and_send"
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


class RobotLoader(yaml.SafeLoader):
    """Custom YAML loader that supports the !include tag.

    Attributes:
        _root: The directory containing the YAML file being parsed.
    """

    def __init__(self, stream: Any):
        """Initialize the loader and set the root directory.

        Args:
            stream: The input stream (file object).
        """
        self._root = os.path.dirname(os.path.abspath(stream.name))
        super().__init__(stream)


def _include_tag_constructor(loader: RobotLoader, node: yaml.nodes.ScalarNode) -> Any:
    """Constructor for the !include tag.

    Args:
        loader: The RobotLoader instance.
        node: The YAML node representing the include path.

    Returns:
        The parsed content of the included file.
    """
    filename = loader.construct_scalar(node)
    filepath = os.path.join(loader._root, filename)
    with open(filepath, "r") as f:
        return yaml.load(f, RobotLoader)


yaml.add_constructor("!include", _include_tag_constructor, RobotLoader)


def _substitute_env_vars(data: Any) -> Any:
    """Recursively substitute environment variables in strings.

    Supports ${VAR_NAME} or ${VAR_NAME:-default}.

    Args:
        data: The data structure to process.

    Returns:
        The data structure with environment variables substituted.
    """
    if isinstance(data, dict):
        return {k: _substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str):

        def replace_env(match):
            var_name = match.group(1)
            default_val = match.group(2) if match.group(2) else ""
            return os.environ.get(var_name, default_val)

        return re.sub(r"\${(\w+)(?::-(.*?))?}", replace_env, data)
    return data


def _flatten_steps(steps: List[Any]) -> List[Dict[str, Any]]:
    """Recursively flatten a list of steps.

    If an include returns a list of actions, they are flattened into the main sequence.

    Args:
        steps: The list of steps to flatten.

    Returns:
        A flattened list of step dictionaries.
    """
    flat_steps = []
    for step in steps:
        if isinstance(step, list):
            flat_steps.extend(_flatten_steps(step))
        elif isinstance(step, dict):
            flat_steps.append(step)
    return flat_steps


def _load_yaml_with_inheritance(yaml_path: str) -> Dict[str, Any]:
    """Load a YAML file and handle the top-level 'include' key for inheritance.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        A dictionary containing the merged YAML data.
    """
    with open(yaml_path, "r") as f:
        data = yaml.load(f, RobotLoader)

    if not isinstance(data, dict):
        return data

    if "include" in data:
        include_path = data.pop("include")
        if not os.path.isabs(include_path):
            include_path = os.path.join(
                os.path.dirname(os.path.abspath(yaml_path)), include_path
            )

        parent_data = _load_yaml_with_inheritance(include_path)

        # Merge logic
        merged = parent_data.copy()
        for key, value in data.items():
            if key == "steps":
                merged["steps"] = parent_data.get("steps", []) + value
            elif (
                key == "defaults"
                and isinstance(value, dict)
                and isinstance(merged.get("defaults"), dict)
            ):
                merged["defaults"].update(value)
            else:
                merged[key] = value
        return merged

    return data


def parse_robot_script(yaml_path: str) -> RobotScript:
    """Load and parse a YAML automation script with includes and inheritance.

    Args:
        yaml_path: Path to the YAML script file.

    Returns:
        A RobotScript object containing the parsed actions and metadata.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML content is invalid.
    """
    raw_data = _load_yaml_with_inheritance(yaml_path)
    data = _substitute_env_vars(raw_data)

    raw_steps = data.get("steps", [])
    flattened_steps = _flatten_steps(raw_steps)
    steps = [Action.from_dict(step) for step in flattened_steps]

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
