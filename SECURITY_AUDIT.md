# Security Audit and Threat Model Report - 5250 RPA Robot

## 1. Executive Summary
The 5250 RPA Robot is a YAML-driven automation framework. While the core engine follows several security best practices (such as using `SafeLoader` for YAML and passing arguments as lists to `subprocess`), there are areas where security can be hardened, particularly regarding secret management, logging, and transport security.

## 2. Threat Model

### Assets
- **IBM i Credentials**: Usernames and passwords used to authenticate to the host.
- **HMC Credentials**: Credentials for managing LPARs via the HMC Proxy.
- **Business Data**: Sensitive information displayed on the terminal screens and captured in logs or screen captures.
- **Execution Environment**: The machine running the robot, which holds `.env` files and logs.

### Threats
- **Credential Leakage**: Secrets stored in `.env` files or leaked into log files through debug outputs.
- **Man-in-the-Middle (MITM)**: If SSL is disabled, terminal traffic (including credentials) is transmitted in cleartext.
- **Unauthorized Access to Captures**: Screen captures saved to the `captures/` directory may contain sensitive business data.
- **Command Injection**: Maliciously crafted YAML or environment variables could potentially lead to command execution, though the current implementation mitigates this by avoiding shell execution in subprocesses.

## 3. Vulnerability Assessment

### Identified Issues
1. **[REMEDIATED] Log Masking**: Previously, sensitive environment variables like `TN5250_PASSWORD` were not masked in logs if they appeared in debug output.
2. **Cleartext Communication**: The system allows `TN5250_SSL="off"`, which is a high risk in production environments.
3. **Broad Environment Sourcing**: `run-robot.sh` uses `source` to load environment variables, which could execute arbitrary code if the `.env` file is compromised.
4. **Capture Security**: Screen captures are stored as plain text files without encryption or access control within the application.

## 4. Authentication and Authorisation Review

### Authentication
- **Mechanism**: Credentials are injected from `.env` files into the shell environment and then passed to the 5250 emulator or used by the Python engine to navigate the login screen.
- **Risk**: Environment variables can sometimes be visible to other users on the same system (e.g., via `ps`).

### Authorisation
- **Mechanism**: The robot operates with the permissions of the IBM i user profile it logs in with.
- **Risk**: If the user profile has excessive permissions (e.g., `*ALLOBJ`), a compromised robot script could cause significant damage.

## 5. Recommendations and Remediation Tasks

### Immediate Remediation (Completed)
- [x] **Implemented Sensitive Data Masking**: Updated `robot_py/logger.py` to automatically mask `TN5250_PASSWORD` and `HMC_PWD` in all log output.
- [x] **Harden Environment Loading**: Modified `run-robot.sh` to parse `.env` files manually instead of using `source` to prevent code injection.

### Planned Remediation
- [ ] **Enforce SSL by Default**: Update documentation and default settings to discourage unencrypted connections.

### Operational Recommendations
1. **Minimum Set of Permissions**:
   - The IBM i user profile should have `*USER` class.
   - Limit `LMTCPB(*YES)` (Limit capabilities) if the robot only needs to run specific commands.
   - Use specific `GRTOBJAUT` to give the profile access only to the libraries, files, and programs it needs to automate.
   - Avoid `*ALLOBJ` or `*SECADM` special authorities unless strictly necessary.
2. **Environment Security**:
   - Run the robot under a dedicated service account.
   - Set strict file permissions on the project directory (`chmod 700`).
   - Ensure `.env` files are `chmod 600`.
3. **Transport Security**:
   - Always set `TN5250_SSL="on"`.
   - Use valid certificates on the IBM i and HMC.
