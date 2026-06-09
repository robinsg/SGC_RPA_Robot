# Security Policy

This document outlines the security requirements and expectations for the 5250 RPA Robot project.

## Security Requirements

To ensure the security and integrity of this automation framework, the following requirements must be adhered to:

### 1. Transport Security
- **SSL/TLS Enforced**: All connections to IBM i systems and HMC Proxies should utilise SSL/TLS encryption. Avoid disabling SSL in production environments to prevent interception of credentials and business data.
- **Certificate Validation**: Ensure that the machine running the robot trusts the certificates presented by the target systems.

### 2. Secret Management
- **No Hardcoded Secrets**: Credentials, passwords, and private keys must never be hardcoded in YAML scripts or source code.
- **Environment Isolation**: Use `.env.<lpar>` files for local configuration. Ensure these files are never committed to version control.
- **Masking**: The framework implements automatic masking of known sensitive environment variables in log outputs.

### 3. Least Privilege
- **Service Accounts**: Run the robot using dedicated IBM i user profiles with the minimum necessary permissions for the tasks being automated.
- **Restricted Capabilities**: It is recommended to use user profiles with `LMTCPB(*YES)` and no special authorities (like `*ALLOBJ`) where possible.
- **File System Permissions**: The project directory and configuration files should have restricted permissions on the host operating system.

### 4. Input Validation
- **YAML Schema**: All automation logic must conform to the defined YAML schema to ensure predictable execution.
- **Environment Loading**: The system utilizes a secure parser for environment files to prevent shell injection vulnerabilities.

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please report it via the appropriate internal security channels. Do not open public issues for security vulnerabilities.

Include a detailed description of the issue, steps to reproduce, and any potential impact in your report. We aim to acknowledge all reports promptly and work towards a resolution.
