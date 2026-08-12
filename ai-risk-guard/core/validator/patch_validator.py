"""
Deterministic patch validation engine.
"""

import ast
import re

DANGEROUS_IMPORTS = {
    "socket",
    "ctypes",
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

        except Exception:
            return {
                "success": False,
                "message": "AST validation failed",
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

                elif isinstance(node, ast.ImportFrom) and node.module and node.module in DANGEROUS_IMPORTS:

                    return {
                        "success": False,
                        "message": f"Dangerous import detected: {node.module}",
                    }

            return {
                "success": True,
                "message": "Import validation passed",
            }

        except Exception:
            return {
                "success": False,
                "message": "Import validation failed",
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

    def validate_names(self, code: str):
        """Static NameError check.

        Catches patches that reference a name that is never imported, defined,
        assigned, or built-in (e.g. calling ``shlex.split`` without ``import
        shlex``). Syntax-valid code still fails at runtime with a NameError, so
        this is a cheap static guard against broken patches.
        """

        try:
            tree = ast.parse(code)
        except Exception:
            return {
                "success": True,
                "skipped": True,
                "message": "Name validation skipped (unparseable code)",
            }

        defined: set[str] = set()
        starred_import = False

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        defined.add(alias.asname)
                    else:
                        defined.add(alias.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    # `from x import *` makes the whole namespace opaque.
                    starred_import = True
                for alias in node.names:
                    if alias.name != "*":
                        defined.add(alias.asname or alias.name)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)

            elif isinstance(node, ast.arg):
                defined.add(node.arg)

            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)

            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                defined.update(node.names)

            elif isinstance(node, ast.ExceptHandler) and node.name:
                defined.add(node.name)

        try:
            import builtins
            defined.update(dir(builtins))
        except Exception:
            pass
        defined.update({"True", "False", "None", "__class__", "__debug__"})

        if starred_import:
            return {
                "success": True,
                "skipped": True,
                "message": "Name validation skipped (star import present)",
            }

        undefined = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id not in defined
            ):
                undefined.append((node.id, getattr(node, "lineno", 0)))

        if undefined:
            seen = sorted({f"{name} (line {line})" for name, line in undefined})
            return {
                "success": False,
                "message": "Possible NameError: undefined name(s): " + ", ".join(seen),
                "undefined_names": [name for name, _ in undefined],
            }

        return {
            "success": True,
            "message": "Name validation passed",
        }

    def validate_all(self, code: str):

        validators = [
            self.validate_ast,
            self.validate_imports,
            self.validate_names,
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