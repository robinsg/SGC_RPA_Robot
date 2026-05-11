import sys
import os
from .engine import RobotEngine
from .logger import logger


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m robot_py.cli <path_to_yaml>")
        sys.exit(1)

    yaml_arg = sys.argv[1]
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
