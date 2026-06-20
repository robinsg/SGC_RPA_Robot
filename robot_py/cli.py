import sys
import os
import argparse
from .engine import RobotEngine
from .logger import logger


def load_env_file(filepath: str):
    """Loads environment variables from a file into os.environ.

    Args:
        filepath: The path to the environment file.

    Raises:
        FileNotFoundError: If the environment file does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Environment file not found: {filepath}")

    with open(filepath, "r") as f:
        for line in f:
            # Strip comments and whitespace
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

            # Remove 'export ' prefix if present
            if line.startswith("export "):
                line = line[len("export ") :].strip()

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Handle Secret() keyword
                if value.startswith("Secret(") and value.endswith(")"):
                    value = value[7:-1].strip()
                    # Add to ROBOT_SENSITIVE_VARS
                    current_sensitive = os.environ.get("ROBOT_SENSITIVE_VARS", "")
                    if current_sensitive:
                        sensitive_list = current_sensitive.split(",")
                        if key not in sensitive_list:
                            os.environ["ROBOT_SENSITIVE_VARS"] = (
                                f"{current_sensitive},{key}"
                            )
                    else:
                        os.environ["ROBOT_SENSITIVE_VARS"] = key

                # Remove optional quotes from the value
                value = value.strip("\"'")
                os.environ[key] = value


def main():
    """Main entry point for the robot_py CLI.

    Parses command-line arguments, optionally loads environment variables
    from a file, initialises the RobotEngine with the provided YAML script,
    and starts the automation.

    Raises:
        SystemExit: If no script path is provided or an error occurs.
    """
    parser = argparse.ArgumentParser(description="5250 RPA Robot Engine CLI")
    parser.add_argument(
        "-f", "--yaml-file", help="Path to the YAML automation script", required=True
    )
    parser.add_argument(
        "-e", "--env", help="Path to the environment file", required=False
    )

    args = parser.parse_args()
    yaml_arg = args.yaml_file
    env_arg = args.env

    # Log the parameters before any potential masking for file logs
    logger.debug(
        f"Using parameters: --yaml-file {yaml_arg} --host {os.environ.get('TN5250_HOST', '[NOT SET]')} --env {env_arg or '[NOT SET]'}"
    )

    try:
        if env_arg:
            load_env_file(env_arg)

        yaml_path = os.path.abspath(yaml_arg)
        engine = RobotEngine(yaml_path)
        engine.run()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if os.environ.get("LOG_LEVEL") == "DEBUG":
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
