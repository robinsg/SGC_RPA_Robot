from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Dict
import yaml
import os
import re

@dataclass
class Action:
    type: str
    description: Optional[str] = None
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Action':
        action_type = data.get('type')
        if action_type == 'send_text':
            return SendTextAction(**data)
        elif action_type == 'send_key':
            return SendKeyAction(**data)
        elif action_type == 'wait_for_text':
            return WaitForTextAction(**data)
        elif action_type == 'sleep':
            return SleepAction(**data)
        elif action_type == 'capture':
            return CaptureAction(**data)
        elif action_type == 'press_key_if_text_present':
            return PressKeyIfTextPresentAction(**data)
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

def parse_robot_script(yaml_path: str) -> RobotScript:
    with open(yaml_path, 'r') as f:
        content = f.read()
        
    # Process environment variables: ${VAR_NAME}
    def replace_env(match):
        var_name = match.group(1)
        return os.environ.get(var_name, '')
    
    processed_content = re.sub(r'\${(\w+)}', replace_env, content)
    
    data = yaml.safe_load(processed_content)
    
    steps = [Action.from_dict(step) for step in data.get('steps', [])]
    
    defaults_data = data.get('defaults', {})
    defaults = RobotDefaults(
        wait_timeout=defaults_data.get('wait_timeout', 5),
        typing_delay_ms=defaults_data.get('typing_delay_ms', 50)
    )
    
    return RobotScript(
        name=data.get('name', 'Unnamed Robot'),
        description=data.get('description'),
        tmux_session=data.get('tmux_session', '5250_robot'),
        defaults=defaults,
        steps=steps
    )
