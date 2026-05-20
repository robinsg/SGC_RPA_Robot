import sys
import os
import argparse
from .engine import RobotEngine
from .logger import logger


def main():
    """Main entry point for the robot_py CLI.

    Parses command-line arguments, initialises the RobotEngine with the
    provided YAML script, and starts the automation.

    Raises:
        SystemExit: If no script path is provided or an error occurs.
    """
    parser = argparse.ArgumentParser(description="5250 RPA Robot Engine CLI")
    parser.add_argument(
        "-f", "--yaml-file", help="Path to the YAML automation script", required=True
    )

    args = parser.parse_args()
    yaml_arg = args.yaml_file

    try:
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
