# Security policy

This application is experimental and has no production support commitment. Do not submit real health information, conversation transcripts, credentials or identifying booking details in public issues.

For a security report, use the repository's private vulnerability reporting feature if it is enabled. If no private reporting channel is available, open a minimal issue asking for a private contact without describing an exploit or including sensitive data.

Reports should identify the affected revision, impact and a minimal reproduction using synthetic data. Known dependency limitations are recorded in [DEPENDENCY_SECURITY.md](docs/DEPENDENCY_SECURITY.md); an application-level mitigation is not an upstream patch.

Session ownership, bounded admission, request limits and memory expiry are defense-in-depth controls. They do not establish guaranteed availability, clinical safety or forensic erasure of process memory. A hosting provider has its own infrastructure and retention policies.
