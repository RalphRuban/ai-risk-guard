"""
AST-based vulnerability detection engine.
"""

import ast

from utils.logger import logger

from core.metadata.vuln_metadata import (
    VULN_METADATA,
)


class ASTScanner(ast.NodeVisitor):

    def __init__(self):

        self.vulnerabilities = []

        self.source_lines = []

        self.changed_lines = None

        self.file_path = None

    def scan(
        self,
        file_path,
        changed_lines=None
    ):

        self.vulnerabilities = []

        self.changed_lines = changed_lines

        self.file_path = file_path

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                code = file.read()

            self.source_lines = code.splitlines()

            tree = ast.parse(code)

            self.visit(tree)

            return self.vulnerabilities

        except Exception as e:

            logger.error(
                f"AST scanning failed: {e}",
                "SCANNER"
            )

            return []

    def should_scan(self, node):

        if not self.changed_lines:
            return True

        return getattr(
            node,
            "lineno",
            -1
        ) in self.changed_lines

    def get_code(self, node):

        try:

            return self.source_lines[
                node.lineno - 1
            ].strip()

        except Exception:

            return ""

    def add_vulnerability(
        self,
        vulnerability_type,
        node,
        message
    ):

        metadata = VULN_METADATA.get(
            vulnerability_type,
            {}
        )

        self.vulnerabilities.append({

            "type":
                vulnerability_type,

            "line":
                node.lineno,

            "file":
                self.file_path,

            "code":
                self.get_code(node),

            "severity":
                metadata.get(
                    "severity",
                    "HIGH"
                ),

            "message":
                message,

            "description":
                metadata.get(
                    "description",
                    ""
                ),

            "cwe":
                metadata.get(
                    "cwe",
                    ""
                ),

            "owasp":
                metadata.get(
                    "owasp",
                    ""
                ),
        })

    def visit_Call(self, node):

        try:

            if not self.should_scan(node):
                return

            func = node.func

            if (
                isinstance(func, ast.Attribute)
                and
                isinstance(func.value, ast.Name)
                and
                func.value.id == "os"
                and
                func.attr == "system"
            ):

                self.add_vulnerability(
                    "COMMAND_INJECTION",
                    node,
                    "Unsafe shell execution detected"
                )

            elif (
                isinstance(func, ast.Name)
                and
                func.id in ("eval", "exec")
            ):

                self.add_vulnerability(
                    "CODE_INJECTION",
                    node,
                    "Unsafe dynamic execution detected"
                )

            elif (
                isinstance(func, ast.Attribute)
                and
                isinstance(func.value, ast.Name)
                and
                func.value.id == "pickle"
                and
                func.attr == "loads"
            ):

                self.add_vulnerability(
                    "INSECURE_DESERIALIZATION",
                    node,
                    "Unsafe deserialization detected"
                )

        except Exception as e:

            logger.error(
                f"visit_Call failed: {e}",
                "SCANNER"
            )

        self.generic_visit(node)

    def visit_Assign(self, node):

        try:

            if not self.should_scan(node):
                return

            if not isinstance(
                node.targets[0],
                ast.Name
            ):
                return

            variable_name = (
                node.targets[0]
                .id
                .lower()
            )

            keywords = {

                "password",
                "secret",
                "token",
                "key",
                "api_key",
            }

            if any(
                keyword in variable_name
                for keyword in keywords
            ):

                if (
                    isinstance(
                        node.value,
                        ast.Constant
                    )
                    and
                    isinstance(
                        node.value.value,
                        str
                    )
                ):

                    self.add_vulnerability(
                        "HARDCODED_SECRET",
                        node,
                        "Hardcoded secret detected"
                    )

        except Exception as e:

            logger.error(
                f"visit_Assign failed: {e}",
                "SCANNER"
            )

        self.generic_visit(node)