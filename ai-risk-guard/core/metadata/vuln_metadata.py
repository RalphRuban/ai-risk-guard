"""
data/vuln_metadata.py
Single source of truth for vulnerability type metadata.
Keys are SCREAMING_SNAKE_CASE to match vuln["type"] throughout the codebase.
"""

# Stable machine-readable rule IDs per vulnerability type. These are exposed in
# both the PR comment and SARIF properties; they are decoupled from the ruleId
# GitHub sees (the vuln type string) so renaming a display rule never breaks
# alert deduplication.
RULE_IDS: dict[str, str] = {
    "COMMAND_INJECTION": "CMD001",
    "CODE_INJECTION": "EXEC001",
    "HARDCODED_SECRET": "SECRET001",
    "INSECURE_DESERIALIZATION": "DESER001",
    "SQL_INJECTION": "SQL001",
    "PATH_TRAVERSAL": "PATH001",
    "SSRF": "SSRF001",
    "WEAK_CRYPTOGRAPHY": "CRYPTO001",
    "DEBUG_CODE": "DEBUG001",
    "TLS_VERIFICATION_DISABLED": "TLS001",
}

# Vulnerability types that are detected and reported but never gate the PR
# decision. They are treated as informational alerts: shown in the PR comment
# and SARIF, persisted to the dashboard, but excluded from the max-risk
# computation that decides REQUEST_CHANGES.
SILENT_TYPES: frozenset[str] = frozenset({
    "DEBUG_CODE",
    "TLS_VERIFICATION_DISABLED",
})

# CVSS-like security severity scores per vulnerability type. These drive the
# severity classification GitHub Code Scanning displays (Critical >= 9.0,
# High >= 7.0, Medium >= 4.0, else Low) and the PR comment dashboard KPI counts.
SECURITY_SEVERITY: dict[str, float] = {
    "COMMAND_INJECTION": 9.5,
    "CODE_INJECTION": 9.5,
    "SQL_INJECTION": 9.0,
    "HARDCODED_SECRET": 8.0,
    "INSECURE_DESERIALIZATION": 8.0,
    "PATH_TRAVERSAL": 7.0,
    "SSRF": 7.0,
    "WEAK_CRYPTOGRAPHY": 5.0,
    "TLS_VERIFICATION_DISABLED": 6.0,
    "DEBUG_CODE": 2.0,
}

# Human-readable display names per vulnerability type. Used in the PR comment
# finding cards so readers see e.g. "Command Injection" instead of the
# SCREAMING_SNAKE_CASE rule key.
VULN_NAMES: dict[str, str] = {
    "COMMAND_INJECTION": "Command Injection",
    "CODE_INJECTION": "Code Injection",
    "SQL_INJECTION": "SQL Injection",
    "PATH_TRAVERSAL": "Path Traversal",
    "SSRF": "Server-Side Request Forgery",
    "HARDCODED_SECRET": "Hardcoded Secret",
    "INSECURE_DESERIALIZATION": "Insecure Deserialization",
    "WEAK_CRYPTOGRAPHY": "Weak Cryptography",
    "TLS_VERIFICATION_DISABLED": "TLS Verification Disabled",
    "DEBUG_CODE": "Debug Code",
}


def vuln_name(vuln_type: str) -> str:
    """Return the human-readable display name for a vulnerability type.

    Falls back to a title-cased rendering of the type key for unknown types.
    """
    name = VULN_NAMES.get(vuln_type)
    if name:
        return name
    return vuln_type.replace("_", " ").title()


def severity_level_for(vuln_type: str) -> str | None:
    """Return the display severity level for a vulnerability type.

    Uses GitHub Code Scanning thresholds on the per-type security severity
    score. Returns None for unknown types so callers can fall back.
    """
    score = SECURITY_SEVERITY.get(vuln_type)
    if score is None:
        return None
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


VULN_METADATA: dict[str, dict] = {
    "COMMAND_INJECTION": {
        "cwe":         "CWE-78",
        "owasp":       "A03:2021 – Injection",
        "soc2":        "CC6.8 (Software Disruption Control)",
        "iso27001":    "A.14.2.5 (Secure Engineering Principles)",
        "pci_dss":     "Req 6.5.1 (Injection Flaws)",
        "severity":    "HIGH",
        "description": "Execution of OS commands constructed from untrusted input.",
        "risk_rationale": "User input flows directly to shell execution without sanitization, allowing an attacker to execute arbitrary system commands.",
        "remediation": "Replace `os.system()` with `subprocess.run()` using a command list and `shell=False`. Validate and sanitize all user input before passing to shell execution.",
    },
    "CODE_INJECTION": {
        "cwe":         "CWE-94",
        "owasp":       "A03:2021 – Injection",
        "soc2":        "CC6.8 (Software Disruption Control)",
        "iso27001":    "A.14.2.5 (Secure Engineering Principles)",
        "pci_dss":     "Req 6.5.1 (Injection Flaws)",
        "severity":    "HIGH",
        "description": "Execution of untrusted code via eval() or exec().",
        "risk_rationale": "Dynamically executing user-controlled strings via `eval()` or `exec()` allows arbitrary code execution, leading to full system compromise.",
        "remediation": "Replace `eval()`/`exec()` with `ast.literal_eval()` for safe parsing. If dynamic execution is unavoidable, use a sandboxed environment with strict allowlists.",
    },
    "HARDCODED_SECRET": {
        "cwe":         "CWE-798",
        "owasp":       "A07:2021 – Identification and Authentication Failures",
        "soc2":        "CC6.1 (Logical Access Security & Secret Management)",
        "iso27001":    "A.9.4.3 (Password Management Systems)",
        "pci_dss":     "Req 8.2.1 (Strong Secrets & Credentials)",
        "severity":    "HIGH",
        "description": "Sensitive credentials or secrets stored in source code.",
        "risk_rationale": "Hardcoded credentials in source code are exposed to anyone with repository access and are a leading cause of credential-based breaches.",
        "remediation": "Move secrets to environment variables or a secure vault (e.g., HashiCorp Vault, AWS Secrets Manager). Use a secrets management library to load credentials at runtime.",
    },
    "INSECURE_DESERIALIZATION": {
        "cwe":         "CWE-502",
        "owasp":       "A08:2021 – Software and Data Integrity Failures",
        "soc2":        "CC7.1 (Vulnerability & Software Integrity)",
        "iso27001":    "A.12.6.1 (Technical Vulnerability Management)",
        "pci_dss":     "Req 6.5.8 (Improper Data Handling)",
        "severity":    "HIGH",
        "description": "Deserialisation of untrusted data via pickle.loads().",
        "risk_rationale": "Deserializing untrusted data with `pickle.loads()` can execute arbitrary Python code, leading to remote code execution.",
        "remediation": "Replace `pickle.loads()` with `json.loads()` for trusted data formats. If pickle is required, sign and verify payloads with HMAC before deserialization.",
    },
    "SQL_INJECTION": {
        "cwe":         "CWE-89",
        "owasp":       "A03:2021 – Injection",
        "soc2":        "CC6.8 (Database Integrity & Injection Prevention)",
        "iso27001":    "A.14.2.5 (Secure Engineering Principles)",
        "pci_dss":     "Req 6.5.1 (Injection Flaws)",
        "severity":    "HIGH",
        "description": "SQL query dynamically constructed using string formatting or concatenation.",
        "risk_rationale": "Dynamic string formatting or concatenation in SQL queries allows an attacker to inject malicious SQL statements, leading to data exfiltration or destruction.",
        "remediation": "Use parameterized queries with placeholders (`%s` or `?`) instead of f-strings or string concatenation. Always pass user input as query parameters, never interpolated into SQL strings.",
    },
    "PATH_TRAVERSAL": {
        "cwe":         "CWE-22",
        "owasp":       "A01:2021 – Broken Access Control",
        "soc2":        "CC6.1 (Logical Access Security)",
        "iso27001":    "A.9.4.1 (Information Access Restriction)",
        "pci_dss":     "Req 6.5.8 (Improper Access Control)",
        "severity":    "HIGH",
        "description": "File access path constructed from untrusted user input without sanitization.",
        "risk_rationale": "User-controlled file paths without sanitization allow an attacker to read or write files outside the intended directory via `../` traversal sequences.",
        "remediation": "Sanitize file paths by applying `os.path.basename()` to extract only the filename and joining it with a fixed safe directory. Use an allowlist of permitted filenames where possible.",
    },
    "SSRF": {
        "cwe":         "CWE-918",
        "owasp":       "A10:2021 – Server-Side Request Forgery",
        "soc2":        "CC6.6 (Boundary Protection & Network Controls)",
        "iso27001":    "A.13.1.1 (Network Controls)",
        "pci_dss":     "Req 1.3.5 (Restricting Outbound Traffic)",
        "severity":    "HIGH",
        "description": "HTTP request issued to a user-supplied URL without scheme or domain validation.",
        "risk_rationale": "Issuing HTTP requests to user-supplied URLs allows an attacker to probe internal network services, access cloud metadata endpoints, or bypass firewall restrictions.",
        "remediation": "Validate and restrict URLs to an allowlist of trusted domains and schemes. Use a dedicated URL validation function that blocks private IP ranges and metadata endpoints.",
    },
    "WEAK_CRYPTOGRAPHY": {
        "cwe":         "CWE-327",
        "owasp":       "A02:2021 – Cryptographic Failures",
        "soc2":        "CC6.7 (Data Transmission Encryption)",
        "iso27001":    "A.10.1.1 (Cryptographic Controls)",
        "pci_dss":     "Req 4.1 (Strong Cryptography)",
        "severity":    "MEDIUM",
        "description": "Use of broken or legacy cryptographic hashing algorithms (e.g. MD5, SHA1).",
        "risk_rationale": "MD5 and SHA1 are cryptographically broken and vulnerable to collision attacks. They should not be used for security-sensitive operations like digital signatures or password hashing.",
        "remediation": "Replace MD5/SHA1 with SHA-256 or SHA-3. For password hashing specifically, use bcrypt, argon2, or PBKDF2 instead of raw hash functions.",
    },
    "TLS_VERIFICATION_DISABLED": {
        "cwe":         "CWE-295",
        "owasp":       "A02:2021 – Cryptographic Failures",
        "soc2":        "CC6.7 (Data Transmission Encryption)",
        "iso27001":    "A.10.1.1 (Cryptographic Controls)",
        "pci_dss":     "Req 4.1 (Strong Cryptography)",
        "severity":    "MEDIUM",
        "description": "TLS certificate verification disabled on an HTTP request.",
        "risk_rationale": "Disabling certificate verification (verify=False) makes HTTPS requests vulnerable to man-in-the-middle attacks, allowing an attacker to intercept or modify sensitive data in transit.",
        "remediation": "Remove verify=False so requests validate the server certificate against trusted CAs. If a self-signed certificate must be used, pass the exact CA bundle via verify=/path/to/ca.pem instead of disabling verification.",
    },
    "DEBUG_CODE": {
        "cwe":         "CWE-489",
        "owasp":       "A05:2021 – Security Misconfiguration",
        "soc2":        "CC6.8 (Software Disruption Control)",
        "iso27001":    "A.14.2.5 (Secure Engineering Principles)",
        "pci_dss":     "Req 6.5.1 (Injection Flaws)",
        "severity":    "LOW",
        "description": "Debugger or breakpoint invocation left in source code.",
        "risk_rationale": "Leftover debugger calls (breakpoint(), pdb.set_trace()) can halt production processes, leak stack traces, and expose interactive shells to attackers who can trigger the code path.",
        "remediation": "Remove breakpoint() and pdb.set_trace() calls from production code. Use logging with appropriate log levels for runtime diagnostics instead of interactive debuggers.",
    },
}