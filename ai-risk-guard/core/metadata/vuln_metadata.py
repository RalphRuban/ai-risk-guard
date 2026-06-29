"""
data/vuln_metadata.py
Single source of truth for vulnerability type metadata.
Keys are SCREAMING_SNAKE_CASE to match vuln["type"] throughout the codebase.
"""

VULN_METADATA: dict[str, dict] = {
    "COMMAND_INJECTION": {
        "cwe":         "CWE-78",
        "owasp":       "A03:2021 – Injection",
        "severity":    "HIGH",
        "description": "Execution of OS commands constructed from untrusted input.",
    },
    "CODE_INJECTION": {
        "cwe":         "CWE-94",
        "owasp":       "A03:2021 – Injection",
        "severity":    "HIGH",
        "description": "Execution of untrusted code via eval() or exec().",
    },
    "HARDCODED_SECRET": {
        "cwe":         "CWE-798",
        "owasp":       "A07:2021 – Identification and Authentication Failures",
        "severity":    "HIGH",
        "description": "Sensitive credentials or secrets stored in source code.",
    },
    "INSECURE_DESERIALIZATION": {
        "cwe":         "CWE-502",
        "owasp":       "A08:2021 – Software and Data Integrity Failures",
        "severity":    "HIGH",
        "description": "Deserialisation of untrusted data via pickle.loads().",
    },
}