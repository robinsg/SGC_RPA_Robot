# AI Development Guidelines

## Project Context
This project is an RPA (Robotic Process Automation) engine for IBM i (AS/400) systems. It bridges modern AI capabilities with legacy green-screen terminals via `tmux` and `tn5250`.

**Language Preference:** All responses and generated documentation must be in UK English.

## YAML Scripting & Prompting Guidelines
- **Variable Injection:** When generating automation scripts, use the back-reference syntax `${VAR_NAME}` for sensitive credentials.
- **Description:** Always include a `description` for each YAML step to explain the "why" to the user.
- **Coordinate System:** 5250 coordinates are 1-indexed (Row 1-24/27, Col 1-80/132). Always verify coordinates against standard IBM i layouts.
- **Valid Actions:** Only use supported actions: `wait_for_text`, `send_text`, `send_key`, `sleep`, `capture`, `press_key_if_text_present`.
- **State Guarding (Terminal Reliability):** Always prioritise robust screen state detection. Never assume a screen has loaded without a matching `wait_for_text` or similar guard.
- **Targeting:** Prefer rectangular block searches (`row`, `col`, `end_row`, `end_col`) over global searches when targeting specific fields to reduce false positives.
- **Conditional Logic:** Use `press_key_if_text_present` for optional screens (e.g., Sign On Info, Password Expiry warnings) rather than hard branching.
- **Mental Model:** Treat different screens as objects (Page Object Model). The YAML steps should represent a clear transition from one screen to the next.

## TypeScript Engine Development
- **Terminal Emulation (`env.TERM`):**
    - Validate that `env.TERM` uses one of the following supported types:
        - **27x132:** `IBM-3477-FC`, `IBM-3477-FG`, `IBM-3180-2`.
        - **24x80:** `IBM-3179-2`, `IBM-3196-A1`, `IBM-5292-2`, `IBM-5291-1`, `IBM-5251-11`.
    - Ensure the `tmux` buffer is correctly sized to match the terminal type (either 24x80 or 27x132) before starting the `tn5250` session.
- **Schema Enforcement:** Any new automation action MUST start with an update to `src/robot/schema.ts` using Zod. The TypeScript engine must remain generic and driven by the YAML schema.
- **Tmux Interactions:** Only use `send-keys` and `capture-pane`. Avoid complex tmux scripting that makes debugging difficult.
- **Tmux Session Safety:** Always check if the tmux session defined in the YAML exists before attempting to send keys or capture content.
- **Error Handling:** When a terminal error occurs (e.g., timeout, missing session), include the current tmux pane content in the error message or log.
- **Environment Isolation:** Screens vary by LPAR. Use `TN5250_HOST` to segment configuration.
- **Capture Pathing:** Stick to the standard `/captures/{host}/{filename}_{timestamp}.txt` format.

## Vision and Capture Analysis
- If using multimodal models to analyse screen captures, ensure the model understands the fixed-width nature of 5250 terminals (typically 24x80 or 27x132).
- Remind the model that "Sign On" screens often have hidden input fields for passwords.