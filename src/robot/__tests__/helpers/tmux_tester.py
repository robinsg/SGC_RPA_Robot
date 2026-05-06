import subprocess
import time
import sys
import os
import uuid

def run_tmux(args):
    cmd = ['tmux'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Tmux error: {result.stderr}", file=sys.stderr)
    return result.stdout

def main():
    if len(sys.argv) < 2:
        print("Usage: python tmux_tester.py <tmux_key>")
        sys.exit(1)

    key_to_send = sys.argv[1]
    unique_id = str(uuid.uuid4())[:8]
    session_name = f"test-session-{unique_id}"
    output_file = f"output-{session_name}.txt"

    try:
        # Start a tmux session running a command that logs raw input
        # 'cat -v' is good for showing escape sequences
        run_tmux(['new-session', '-d', '-s', session_name, f'cat -v > {output_file}'])

        # Wait for session to start
        time.sleep(0.5)

        # Send the key
        run_tmux(['send-keys', '-t', session_name, key_to_send])

        # Send a sentinel to mark the end of the tested key
        run_tmux(['send-keys', '-t', session_name, 'DONE'])
        run_tmux(['send-keys', '-t', session_name, 'Enter'])

        # Wait for key to be processed
        time.sleep(0.5)

    finally:
        # Kill the session
        run_tmux(['kill-session', '-t', session_name])

    # Read the output
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            content = f.read().strip()
        os.remove(output_file)
        print(content)
    else:
        print(f"Error: Output file {output_file} not found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
