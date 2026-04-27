# Operational Guidelines for 5250 RPA Robot

## Core Principles
- **Terminal Reliability**: Always prioritize robust screen state detection. Never assume a screen has loaded without a matching `wait_for_text` or similar guard.
- **YAML First**: All automation logic must reside in YAML configuration. The TypeScript engine should remain generic and driven by the schema.
- **Environment Isolation**: Screens vary by LPAR. Use `TN5250_HOST` to segment configuration and output (like captures).

## Technical Implementation Rules
- **Schema Enforcement**: Any new automation action MUST start with an update to `src/robot/schema.ts` using Zod.
- **Error Handling**: When a terminal error occurs (timeout, missing session), include the current tmux pane content in the error message or log.
- **Capture Pathing**: Stick to the standard `/captures/{host}/{filename}_{timestamp}.txt` format.
- **Tmux Interaction**: Only use `send-keys` and `capture-pane`. Avoid complex tmux scripting that makes debugging difficult.

## Design Patterns
- **Page Object Model (Mental)**: Treat different screens as objects. Though logic is in YAML, the YAML steps should be structured to represent a clear transition from one screen to the next.
- **Conditional Handling**: Use `press_key_if_text_present` for optional screens (Sign On Info, Password Expiry warnings) rather than hard branching.
