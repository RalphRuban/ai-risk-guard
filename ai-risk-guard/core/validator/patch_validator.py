"""
Deterministic patch validation engine.
"""

import ast
import re


DANGEROUS_IMPORTS = {
    "socket",
    "ctypes",
    "multiprocessing",
}


DANGEROUS_PATTERNS = [
    r"\beval\s*\(",      # Match eval( but not literal_eval(
    r"\bexec\s*\(",
    r"os\.system\s*\(",
    r"pickle\.loads\s*\(",
]


class PatchValidator:

    def validate_ast(self, code: str):

        try:
            ast.parse(code)
            return {
                "success": True,
                "message": "AST validation passed",
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }

    def validate_imports(self, code: str):

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):

                    for imported in node.names:

                        if imported.name in DANGEROUS_IMPORTS:
                            return {
                                "success": False,
                                "message": f"Dangerous import detected: {imported.name}",
                            }

            return {
                "success": True,
                "message": "Import validation passed",
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }

    def validate_patterns(self, code: str):

        for pattern in DANGEROUS_PATTERNS:

            if re.search(pattern, code):

                return {
                    "success": False,
                    "message": f"Unsafe pattern detected: {pattern}",
                }

        return {
            "success": True,
            "message": "Pattern validation passed",
        }

    def validate_all(self, code: str):

        validators = [
            self.validate_ast,
            self.validate_imports,
            self.validate_patterns,
        ]

        results = []

        for validator in validators:

            result = validator(code)

            results.append(result)

            if not result["success"]:
                return {
                    "success": False,
                    "stage": validator.__name__,
                    "results": results,
                }

        return {
            "success": True,
            "results": results,
        }