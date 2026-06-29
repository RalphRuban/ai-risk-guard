"""
Security explainability engine.
Generates human-readable remediation reasoning.
"""

EXPLANATIONS = {

    "COMMAND_INJECTION":
        "User-controlled input may execute arbitrary system commands.",

    "CODE_INJECTION":
        "Dynamic code execution may allow arbitrary Python execution.",

    "HARDCODED_SECRET":
        "Hardcoded credentials may expose sensitive infrastructure access.",

    "INSECURE_DESERIALIZATION":
        "Deserialization may execute attacker-controlled payloads.",
}


FIX_EXPLANATIONS = {

    "COMMAND_INJECTION":
        "Replaced unsafe shell execution with secure subprocess handling.",

    "CODE_INJECTION":
        "Replaced unsafe eval/exec usage with safe literal parsing.",

    "HARDCODED_SECRET":
        "Moved sensitive values into environment variables.",

    "INSECURE_DESERIALIZATION":
        "Removed unsafe deserialization pattern.",
}


class SecurityExplainer:

    def explain_vulnerability(
        self,
        vulnerability_type
    ):

        return EXPLANATIONS.get(
            vulnerability_type,
            "Potential security issue detected."
        )

    def explain_fix(
        self,
        vulnerability_type
    ):

        return FIX_EXPLANATIONS.get(
            vulnerability_type,
            "Applied security remediation."
        )

    def remediation_summary(
        self,
        vulnerability
    ):

        vulnerability_type = vulnerability.get("type")

        return {
            "issue":
                self.explain_vulnerability(
                    vulnerability_type
                ),

            "fix":
                self.explain_fix(
                    vulnerability_type
                ),
        }