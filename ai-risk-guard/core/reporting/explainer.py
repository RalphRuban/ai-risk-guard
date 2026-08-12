EVIDENCE_RULES = {
    "COMMAND_INJECTION": "Rule: os.system() / subprocess with shell=True — Executes OS commands from untrusted input",
    "CODE_INJECTION": "Rule: eval() / exec() — Dynamically executes arbitrary Python code",
    "HARDCODED_SECRET": "Rule: Secret-named variable assigned a string literal — Hardcoded credential pattern",
    "INSECURE_DESERIALIZATION": "Rule: pickle.loads() — Deserializes untrusted data allowing arbitrary code execution",
    "SQL_INJECTION": "Rule: Dynamic string formatting in SQL execute() — SQL injection vector",
    "PATH_TRAVERSAL": "Rule: File path constructed from dynamic input without basename sanitization — Path traversal",
    "SSRF": "Rule: Dynamic URL in HTTP request — Server-side request forgery vector",
    "WEAK_CRYPTOGRAPHY": "Rule: Use of weak cryptographic hash (MD5/SHA1) — Broken or legacy algorithm",
}


def generate_evidence(vulnerability):
    vuln_type = vulnerability.get("type", "")
    code = vulnerability.get("code", "")
    line = vulnerability.get("line", 0)
    rule = EVIDENCE_RULES.get(vuln_type, "Unknown rule matched")
    return {"rule": rule, "code": code, "line": line}
