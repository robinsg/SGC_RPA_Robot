# RPA Engine Technical Design

This directory contains the core automation engine. It is designed to be modular, strictly typed, and resilient to terminal lag.

## 🏗 Architecture

The application follows a **driver-based** architecture:

1.  **Transport Engine**: The `tmux` command-line utility serves as the bridge between the Node.js engine and the persistent `tn5250` process.
2.  **Schema (schema.ts)**: Uses `Zod` to strictly validate the YAML input at runtime. This prevents "silent failures" caused by typos in the automation script.
3.  **Engine (engine.ts)**: The state machine that iterates through steps, captures the tmux buffer, and performs text-based verification.
4.  **CLI (cli.ts)**: A lightweight wrapper to launch the engine from any shell.

## 📜 YAML Schema Definition

Automation scripts support the following actions:

### `wait_for_text`
Guards the automation by waiting for a specific string to appear on screen.
- `text`: String to look for.
- `row` / `col` (Optional): Specific starting position (1-indexed).
- `end_row` / `end_col` (Optional): End coordinates for a rectangular block search.
- `is_message_line` (Optional): Set to `true` to automatically search the dynamic status/message line (last line).
- `timeout_seconds`: How long to wait before crashing (defaults to 10s).

### `send_text`
Types text into the terminal. Supports back-references like `${USERNAME}`.

### `send_key`
Sends a special key to the session.
- Supported: `Enter`, `Tab`, `F1` through `F24`, `PgUp`, `PgDn`.

### `press_key_if_text_present`
Performs a conditional action. If the specified text is found, it sends the specified key. If not found, it does nothing (no error).
- `text`: String to look for.
- `key`: Key to send if text is found.
- Supports same coordinate/block search as `wait_for_text`.

### `sleep`
Adds a hard delay in seconds. Use sparingly; `wait_for_text` is preferred.

### `capture`
Saves the current terminal buffer as a text file for auditing or debugging. 
- **Storage**: Files are saved in `/captures/{TN5250_HOST}/`.
- **Naming**: Filenames include an ISO timestamp (e.g., `capture_2024-04-27T05-21-34Z.txt`).
- **Options**: You can provide a custom `filename` prefix in the YAML step.

## 🛡 Stability & Error Handling

- **Input Throttling**: The engine can be configured with `typing_delay_ms` to avoid overwhelming legacy buffers.
- **Exception Hierarchy**: The engine throws detailed errors if a session is missing or a timeout occurs, preventing partially completed transactions.
- **State Capture**: Upon any failure, the engine is designed to capture the buffer as an artifact for post-mortem analysis.
