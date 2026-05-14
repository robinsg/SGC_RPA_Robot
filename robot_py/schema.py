from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import yaml
import os
import re


@dataclass
class Action:
    type: str
    description: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Action":
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
    text: str = ""


@dataclass
class SendKeyAction(Action):
    key: str = ""


@dataclass
class WaitForTextAction(Action):
    text: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    end_row: Optional[int] = None
    end_col: Optional[int] = None
    is_message_line: Optional[bool] = None
    timeout_seconds: int = 10


@dataclass
class SleepAction(Action):
    seconds: float = 0.0


@dataclass
class CaptureAction(Action):
    filename: Optional[str] = None


@dataclass
class PressKeyIfTextPresentAction(Action):
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
    row: int = 1
    col: int = 1


@dataclass
class SearchAndMoveCursorAction(Action):
    text: str = ""
    row: int = 1
    col: int = 1
    end_row: int = 1
    end_col: int = 1
    target_col: int = 1
    timeout_seconds: int = 10


@dataclass
class SearchExtractAndSendAction(Action):
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
    length: int = 1


@dataclass
class RobotDefaults:
    wait_timeout: int = 5
    typing_delay_ms: int = 50


@dataclass
class RobotScript:
    name: str
    steps: List[Action]
    description: Optional[str] = None
    tmux_session: str = "5250_robot"
    defaults: RobotDefaults = field(default_factory=RobotDefaults)


class RobotLoader(yaml.SafeLoader):
    """Custom YAML loader to support !include tags and track file root."""

    def __init__(self, stream: Any) -> None:
        """Initialises the loader and determines the root directory.

        Args:
            stream: The input stream.
        """
        self._root = os.path.split(stream.name)[0] if hasattr(stream, "name") else "."
        super().__init__(stream)

    @property
    def root(self) -> str:
        """Returns the root directory of the file being parsed."""
        return self._root


def include_constructor(loader: RobotLoader, node: yaml.Node) -> Any:
    """Constructor for the !include tag.

    Args:
        loader: The RobotLoader instance.
        node: The YAML node.

    Returns:
        The content of the included file.
    """
    filename = loader.construct_scalar(node)
    filepath = os.path.join(loader.root, filename)
    return load_robot_yaml_data(filepath)


yaml.add_constructor("!include", include_constructor, Loader=RobotLoader)


def load_robot_yaml_data(filepath: str) -> Any:
    """Loads robot YAML data with environment substitution and inheritance.

    Args:
        filepath: Path to the YAML file.

    Returns:
        The processed YAML data.
    """
    with open(filepath, "r") as f:
        content = f.read()

    processed_content = substitute_env_vars(content)

    # Use a StringIO to simulate a file with a .name attribute for RobotLoader
    from io import StringIO

    stream = StringIO(processed_content)
    stream.name = filepath

    data = yaml.load(stream, Loader=RobotLoader)

    if isinstance(data, dict) and "include" in data:
        base_path = os.path.join(os.path.dirname(filepath), data["include"])
        base_data = load_robot_yaml_data(base_path)

        # Merge base_data into data
        if isinstance(base_data, dict):
            merged = base_data.copy()
            for key, value in data.items():
                if key == "include":
                    continue
                if key == "defaults" and isinstance(value, dict) and "defaults" in merged:
                    merged["defaults"] = {**merged["defaults"], **value}
                else:
                    merged[key] = value
            return merged

    return data


def substitute_env_vars(content: str) -> str:
    """Substitutes environment variables in a string.

    Args:
        content: The string to process.

    Returns:
        The string with environment variables substituted.
    """

    def replace_env(match):
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) else ""
        return os.environ.get(var_name, default_val)

    return re.sub(r"\${(\w+)(?::-(.*?))?}", replace_env, content)


def _flatten_steps(steps: List[Any]) -> List[Dict[str, Any]]:
    """Recursively flattens a list of steps.

    Args:
        steps: The list of steps to flatten.

    Returns:
        A flattened list of step dictionaries.
    """
    flattened = []
    for step in steps:
        if isinstance(step, list):
            flattened.extend(_flatten_steps(step))
        else:
            flattened.append(step)
    return flattened


def parse_robot_script(yaml_path: str) -> RobotScript:
    """Parses a robot YAML script into a RobotScript object.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        The parsed RobotScript object.
    """
    data = load_robot_yaml_data(yaml_path)

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
