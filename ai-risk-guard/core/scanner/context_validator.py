"""
core/scanner/context_validator.py

False-positive reduction engine.
Filters placeholder/demo/example/test content.
"""

import re

from utils.logger import logger

PLACEHOLDER_PATTERNS = [
    r"\bchangeme\b",
    r"\bexample\b",
    r"your[_\-]?key",
    r"your[_\-]?token",
    r"your[_\-]?password",
    r"\bplaceholder\b",
    r"\bdummy\b",
    r"\bsample\b",
    r"<secret>",
    r"<token>",
    r"<password>",
]


class ContextValidator:

    def is_test_file(
        self,
        file_path
    ):

        normalized = file_path.lower()

        return any(

            keyword in normalized

            for keyword in [
                "/tests/",
                "\\tests\\",
                "test_",
                "_test.py",
            ]
        )

    def is_comment(
        self,
        line
    ):

        stripped = line.strip()

        return (
            stripped.startswith(("#", "//"))
        )

    def is_placeholder(self, value):
        lowered = value.lower().strip()
    
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, lowered):
                return True
    
        # extra heuristic layer (REFINED)
        heuristic_patterns = [
            r"^your_.*_here$",
            r"^example_.*",
            r"^test_.*",
            r"^<.*>$", # Strictly placeholders like <API_KEY>
        ]
    
        for pattern in heuristic_patterns:
            if re.search(pattern, lowered):
                return True
    
        return False

    def is_env_var_source(self, line):
        return any(
            pattern in line
            for pattern in [
                "os.getenv(",
                "os.environ.get(",
                "os.environ[",
            ]
        )

    def should_ignore_secret(
        self,
        file_path,
        line
    ):

        try:

            if self.is_test_file(file_path):
                logger.debug(f"Ignoring test file: {file_path}", "CONTEXT")
                return True

            if self.is_comment(line):
                logger.debug(f"Ignoring comment: {line.strip()}", "CONTEXT")
                return True

            if self.is_placeholder(line):
                logger.debug(f"Ignoring placeholder: {line.strip()}", "CONTEXT")
                return True

            if self.is_env_var_source(line):
                logger.debug(f"Ignoring env var assignment: {line.strip()}", "CONTEXT")
                return True

            return False

        except Exception as error:

            logger.error(
                f"Context validation failed: {error}",
                "CONTEXT"
            )

            return False