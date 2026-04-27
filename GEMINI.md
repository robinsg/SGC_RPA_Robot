# AI Development Guidelines

## Project Context
This project is an RPA (Robotic Process Automation) engine for IBM i (AS/400) systems. It bridges modern AI capabilities with legacy green-screen terminals via `tmux` and `tn5250`.

## Prompting Guidelines
- When generating automation scripts, use the back-reference syntax `${VAR_NAME}` for sensitive credentials.
- Always include a `description` for each YAML step to explain the "why" to the user.
- Prefer rectangular block searches (`row`, `col`, `end_row`, `end_col`) over global searches when targeting specific fields to reduce false positives.

## Vision and Capture Analysis
- If using multimodal models to analyze screen captures, ensure the model understands the fixed-width nature of 5250 terminals (typically 24x80 or 27x132).
- Remind the model that "Sign On" screens often have hidden input fields for passwords.
