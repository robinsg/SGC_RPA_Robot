import subprocess
import os
import time
from datetime import datetime
from typing import Optional, List, Tuple
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
    """Validate that required environment variables are set and non-empty."""
    hmc_host = os.environ.get("HMC_HOST")
    missing_vars = []

    common_required = ["TN5250_USER", "TN5250_PASSWORD"]
    for var in common_required:
        if not os.environ.get(var):
            missing_vars.append(var)

    if hmc_host:
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
        if not os.environ.get("TN5250_HOST"):
            missing_vars.append("TN5250_HOST")

    if missing_vars:
        mode = "HMC Proxy" if hmc_host else "Direct IP"
        raise ValueError(
            f"Missing required environment variables for {mode} connection: {', '.join(missing_vars)}"
        )

    device_type = os.environ.get("TN5250_DEVICE_TYPE")
    if device_type and device_type not in (SUPPORTED_27x132 + SUPPORTED_24x80):
        raise ValueError(f"Unsupported TN5250_DEVICE_TYPE: {device_type}")


class TmuxInterface:
    """Handles low-level communication with the tmux session."""

    def __init__(self, session: str):
        self.session = session

    def run(self, args: List[str]) -> str:
        if not self.exists():
            raise RuntimeError(f"Tmux session '{self.session}' not found.")

        cmd = ["tmux"] + args
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_output = result.stderr or result.stdout or "No output"
            raise RuntimeError(
                f"Tmux command failed: [{' '.join(cmd)}]. Error: {error_output.strip()}"
            )

        return result.stdout

    def exists(self) -> bool:
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session], capture_output=True
        )
        return result.returncode == 0

    def terminate(self):
        if self.exists():
            logger.info(f"Terminating tmux session: {self.session}")
            subprocess.run(
                ["tmux", "kill-session", "-t", self.session], capture_output=True
            )

    def get_cursor(self) -> Tuple[int, int]:
        res = self.run(
            ["display-message", "-p", "-t", self.session, "#{cursor_y},#{cursor_x}"]
        )
        y, x = map(int, res.strip().split(","))
        return y + 1, x + 1

    def send_keys(self, *keys: str, literal: bool = False):
        cmd = ["send-keys"]
        if literal:
            cmd.append("-l")
        cmd.extend(["-t", self.session])
        cmd.extend(keys)
        self.run(cmd)

    def capture_pane(self, max_rows: int) -> str:
        return self.run(
            ["capture-pane", "-t", self.session, "-p", "-S", "0", "-E", str(max_rows - 1)]
        )


class Screen:
    """Represents and analyzes the state of the terminal screen."""

    def __init__(self, content: str, max_rows: int, max_cols: int):
        self.content = content
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.lines = content.splitlines()

    def get_title(self) -> str:
        for line in self.lines[:5]:
            trimmed = line.strip()
            if trimmed:
                return trimmed
        return ""

    def validate_coords(self, row: int, col: int):
        if not (1 <= row <= self.max_rows):
            raise ValueError(f"Row {row} out of bounds (1-{self.max_rows})")
        if not (1 <= col <= self.max_cols):
            raise ValueError(f"Column {col} out of bounds (1-{self.max_cols})")

    def find_text(
        self,
        text: str,
        row: Optional[int] = None,
        col: Optional[int] = None,
        end_row: Optional[int] = None,
        end_col: Optional[int] = None,
        is_message_line: Optional[bool] = None,
    ) -> bool:
        if is_message_line:
            message_line_index = 26 if self.max_rows == 27 else 23
            line = self.lines[message_line_index] if len(self.lines) > message_line_index else ""
            return text in line
        elif (
            row is not None
            and col is not None
            and end_row is not None
            and end_col is not None
        ):
            search_area_lines = self.lines[row - 1 : end_row]
            search_area = "\n".join(
                [line[col - 1 : end_col] for line in search_area_lines]
            )
            return text in search_area
        elif row is not None:
            line = self.lines[row - 1] if len(self.lines) > row - 1 else ""
            if col is not None:
                return text in line[col - 1 :]
            else:
                return text in line
        else:
            return text in self.content

    def find_row_in_block(
        self,
        text: str,
        row: int,
        col: int,
        end_row: int,
        end_col: int,
    ) -> Optional[int]:
        for i in range(row - 1, end_row):
            if i >= len(self.lines):
                break
            line_part = self.lines[i][col - 1 : end_col]
            if text in line_part:
                return i + 1
        return None

    def extract_text(self, row: int, col: int, length: int) -> str:
        if row - 1 >= len(self.lines):
            return ""
        return self.lines[row - 1][col - 1 : col - 1 + length].strip()


class ActionDispatcher:
    """Dispatches YAML actions to the appropriate engine logic."""

    def __init__(self, engine: "RobotEngine"):
        self.engine = engine

    def dispatch(self, action: Action):
        method_name = f"execute_{action.action_type}"
        method = getattr(self, method_name, None)
        if method:
            method(action)
        else:
            raise NotImplementedError(f"Action type '{action.action_type}' not implemented.")

    def execute_send_text(self, action: SendTextAction):
        self.engine.tmux.send_keys(action.text, literal=True)

    def execute_send_key(self, action: SendKeyAction):
        key_to_send = KEY_MAP.get(action.key, action.key)
        self.engine.tmux.send_keys(key_to_send)
        time.sleep(0.25)
        self.engine.capture_debug_screen(f"after_send_key_{action.key}")

    def execute_sleep(self, action: SleepAction):
        time.sleep(action.seconds)

    def execute_capture(self, action: CaptureAction):
        self.engine.save_capture(action.filename)

    def execute_wait_for_text(self, action: WaitForTextAction):
        self.engine.wait_for_text(
            action.text,
            action.timeout_seconds,
            row=action.row,
            col=action.col,
            end_row=action.end_row,
            end_col=action.end_col,
            is_message_line=action.is_message_line,
        )
        safe_text = "".join([c if c.isalnum() else "_" for c in action.text])
        self.engine.capture_debug_screen(f"after_wait_for_{safe_text}")

    def execute_press_key_if_text_present(self, action: PressKeyIfTextPresentAction):
        settle_time = (action.wait_ms / 1000.0 if action.wait_ms is not None else 0.25)
        if settle_time > 0:
            time.sleep(settle_time)

        found, _ = self.engine.wait_for_text_internal(
            action.text,
            action.timeout_seconds,
            row=action.row,
            col=action.col,
            end_row=action.end_row,
            end_col=action.end_col,
            is_message_line=action.is_message_line,
        )

        if found:
            press_key = KEY_MAP.get(action.key, action.key)
            logger.info(f'[Condition] Text "{action.text}" found. Sending key: {action.key}')
            self.engine.tmux.send_keys(press_key)
            time.sleep(0.25)
        else:
            logger.info(f'[Condition] Text "{action.text}" not found. Skipping.')

    def execute_move_cursor(self, action: MoveCursorAction):
        self.engine.move_cursor(action.row, action.col)

    def execute_search_and_move_cursor(self, action: SearchAndMoveCursorAction):
        found, screen = self.engine.wait_for_text_internal(
            action.text, action.timeout_seconds, row=action.row, col=action.col, end_row=action.end_row, end_col=action.end_col
        )
        if not found:
            raise RuntimeError(f'Timeout waiting for "{action.text}" in block')

        match_row = screen.find_row_in_block(
            action.text, action.row, action.col, action.end_row, action.end_col
        )
        self.engine.move_cursor(match_row, action.target_col)

    def execute_search_extract_and_send(self, action: SearchExtractAndSendAction):
        found, screen = self.engine.wait_for_text_internal(
            action.text, action.timeout_seconds, row=action.row, col=action.col, end_row=action.end_row, end_col=action.end_col
        )
        if not found:
            raise RuntimeError(f'Timeout waiting for "{action.text}" in block')

        match_row = screen.find_row_in_block(
            action.text, action.row, action.col, action.end_row, action.end_col
        )
        extracted = screen.extract_text(match_row, action.extract_col, action.extract_length)
        self.engine.tmux.send_keys(extracted, literal=True)

    def execute_extract_at_cursor_and_send(self, action: ExtractAtCursorAndSendAction):
        row, col = self.engine.tmux.get_cursor()
        screen = self.engine.refresh_screen()
        extracted = screen.extract_text(row, col, action.length)
        self.engine.tmux.send_keys(extracted, literal=True)


class RobotEngine:
    """The core engine responsible for executing automation scripts."""

    def __init__(self, yaml_path: str):
        validate_environment()
        self.script = parse_robot_script(yaml_path)
        session_name = os.environ.get("TMUX_SESSION", self.script.tmux_session)
        self.tmux = TmuxInterface(session_name)
        self.host = os.environ.get("TN5250_HOST", "unknown_host")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.last_logged_title = ""
        self.history_screens: List[Screen] = []
        self.dispatcher = ActionDispatcher(self)

        device_type = os.environ.get("TN5250_DEVICE_TYPE", "IBM-3477-FC")
        if device_type in SUPPORTED_27x132:
            self.max_rows, self.max_cols = 27, 132
        elif device_type in SUPPORTED_24x80:
            self.max_rows, self.max_cols = 24, 80
        else:
            raise ValueError(f"Unsupported device type: {device_type}")

    @property
    def session(self) -> str:
        return self.tmux.session

    def refresh_screen(self) -> Screen:
        try:
            content = self.tmux.capture_pane(self.max_rows)
        except RuntimeError:
            content = ""

        screen = Screen(content, self.max_rows, self.max_cols)

        new_title = screen.get_title()
        if new_title and new_title != self.last_logged_title:
            logger.info(f"[Screen] {new_title}")
            self.last_logged_title = new_title

            if not self.history_screens or self.history_screens[-1].content != content:
                self.history_screens.append(screen)
            if len(self.history_screens) > 20:
                self.history_screens.pop(0)

        return screen

    def move_cursor(self, target_row: int, target_col: int):
        curr_row, curr_col = self.tmux.get_cursor()
        row_diff, col_diff = target_row - curr_row, target_col - curr_col

        for _ in range(abs(row_diff)):
            self.tmux.send_keys("Down" if row_diff > 0 else "Up")
        for _ in range(abs(col_diff)):
            self.tmux.send_keys("Right" if col_diff > 0 else "Left")

    def wait_for_text_internal(self, text: str, timeout: int, **kwargs) -> Tuple[bool, Screen]:
        expiry = time.time() + timeout
        last_screen = None
        while time.time() < expiry:
            last_screen = self.refresh_screen()
            if last_screen.find_text(text, **kwargs):
                return True, last_screen
            time.sleep(0.5)
        return False, last_screen or self.refresh_screen()

    def wait_for_text(self, text: str, timeout: int, **kwargs):
        found, screen = self.wait_for_text_internal(text, timeout, **kwargs)
        if not found:
            error_msg = f'Timeout waiting for text: "{text}" after {timeout}s.\n--- Current Screen ---\n{screen.content}\n--- End ---'
            raise RuntimeError(error_msg)

    def capture_debug_screen(self, action_name: str):
        if self.log_level != "DEBUG":
            return
        try:
            screen = self.refresh_screen()
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            capture_dir = os.path.join(os.getcwd(), "logs", "captures", self.host)
            os.makedirs(capture_dir, exist_ok=True)
            save_path = os.path.join(capture_dir, f"{timestamp}_{action_name}.txt")
            with open(save_path, "w") as f:
                f.write(screen.content)
            logger.debug(f"[Debug Capture] Saved to {os.path.relpath(save_path)}")
        except Exception as e:
            logger.warning(f"[Debug Capture] Failed: {str(e)}")

    def save_capture(self, filename: Optional[str]):
        screen = self.refresh_screen()
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        host_dir = os.path.join(os.getcwd(), "captures", self.host)
        os.makedirs(host_dir, exist_ok=True)
        base_name = filename or "capture"

        if "Sign On" in screen.content:
            prev_content = ""
            for i in range(len(self.history_screens) - 2, -1, -1):
                if self.history_screens[i].get_title() != screen.get_title():
                    prev_content = self.history_screens[i].content
                    break

            content = (prev_content or screen.content).rstrip() + "\n\nSign off successful\n"
            final_filename = f"{base_name}_signoff_success_{timestamp}.txt"
        else:
            content = screen.content
            final_filename = f"{base_name}_{timestamp}.txt"

        save_path = os.path.join(host_dir, final_filename)
        with open(save_path, "w") as f:
            f.write(content)
        logger.info(f"[Capture] Saved to {save_path}")

    def run(self):
        logger.info(f"Starting Robot: {self.script.name}")
        try:
            if not self.tmux.exists():
                logger.error(f"Error: Tmux session '{self.tmux.session}' not found.")
                return

            self.refresh_screen()
            for i, step in enumerate(self.script.steps):
                desc = f" ({step.description})" if step.description else ""
                logger.info(f"[Step {i + 1}/{len(self.script.steps)}] {step.type}{desc}")
                self.dispatcher.dispatch(step)
                self.refresh_screen()

            logger.info("Automation complete!")

        except Exception as e:
            logger.error(f"Error during automation: {str(e)}")
            try:
                screen = self.refresh_screen()
                timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
                save_path = os.path.join(os.getcwd(), "captures", self.host, f"error_screen_{timestamp}.txt")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w") as f:
                    f.write(screen.content.rstrip() + "\n\nError occurred\n")
                logger.error(f"[Error Capture] Saved to {save_path}")
            except Exception:
                pass
            raise
        finally:
            self.tmux.terminate()

    # Legacy methods for test compatibility
    def check_session_exists(self) -> bool:
        return self.tmux.exists()

    def terminate_session(self):
        self.tmux.terminate()

    def run_tmux(self, args: List[str]) -> str:
        return self.tmux.run(args)

    def validate_coords(self, row: int, col: int):
        Screen("", self.max_rows, self.max_cols).validate_coords(row, col)

    def validate_block(self, row: int, col: int, end_row: int, end_col: int):
        s = Screen("", self.max_rows, self.max_cols)
        s.validate_coords(row, col)
        s.validate_coords(end_row, end_col)
        if row > end_row or col > end_col:
            raise ValueError(f"Invalid block: ({row},{col}) to ({end_row},{end_col})")

    def find_text_in_buffer(self, content: str, text: str, **kwargs) -> bool:
        return Screen(content, self.max_rows, self.max_cols).find_text(text, **kwargs)

    def find_text_in_block(self, content: str, text: str, **kwargs) -> Optional[int]:
        return Screen(content, self.max_rows, self.max_cols).find_row_in_block(text, **kwargs)

    def capture_pane(self) -> str:
        return self.tmux.capture_pane(self.max_rows)

    def get_cursor_position(self) -> Tuple[int, int]:
        return self.tmux.get_cursor()
