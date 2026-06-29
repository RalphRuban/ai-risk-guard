"""
Context-aware risk enhancement engine.
"""


SENSITIVE_KEYWORDS = {
    "auth",
    "payment",
    "token",
    "secret",
    "admin",
    "credential",
}


PUBLIC_ROUTE_PATTERNS = {
    "@app.route",
    "@app.get",
    "@app.post",
    "@router.get",
    "@router.post",
}


class ContextRiskEngine:

    @staticmethod
    def file_sensitivity(filename: str):

        filename = filename.lower()

        if any(
            keyword in filename
            for keyword in SENSITIVE_KEYWORDS
        ):
            return 1.0

        return 0.5

    @staticmethod
    def public_exposure(code: str):

        if any(
            pattern in code
            for pattern in PUBLIC_ROUTE_PATTERNS
        ):
            return 1.0

        return 0.4

    @staticmethod
    def privileged_operation(code: str):

        dangerous_calls = [
            "os.system",
            "subprocess",
            "eval",
            "exec",
        ]

        if any(
            call in code
            for call in dangerous_calls
        ):
            return 1.0

        return 0.3