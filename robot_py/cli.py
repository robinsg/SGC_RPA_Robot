import sys
import os
from .engine import RobotEngine
from .logger import logger


def main():
    """Main entry point for the robot_py CLI.

    Parses command-line arguments, initialises the RobotEngine with the
    provided YAML script, and starts the automation.

    Raises:
        SystemExit: If no script path is provided or an error occurs.
    """
    if len(sys.argv) < 2:
        print("Usage: python3 -m robot_py.cli <path_to_yaml>")
        sys.exit(1)

    yaml_arg = sys.argv[1]
    try:
        if os.path.isfile(yaml_arg):
            yaml_path = os.path.abspath(yaml_arg)
        elif os.path.isfile(os.path.join("yaml_scripts", yaml_arg)):
            yaml_path = os.path.abspath(os.path.join("yaml_scripts", yaml_arg))
        else:
            yaml_path = os.path.abspath(yaml_arg)  # Fallback to absolute path for error reporting

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
