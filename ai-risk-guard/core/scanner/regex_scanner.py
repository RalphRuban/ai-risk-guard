"""
Regex + entropy-based secret scanner.
"""

import re

from core.metadata.vuln_metadata import (
    VULN_METADATA,
)

from core.scanner.entropy_detector import (
    EntropyDetector,
)

from core.scanner.context_validator import (
    ContextValidator,
)


SECRET_PATTERNS = [

    (
        r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{6,})',
        "HARDCODED_SECRET"
    ),

    (
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{12,})',
        "HARDCODED_SECRET"
    ),
]


class RegexScanner:

    def __init__(self):

        self.entropy_detector = EntropyDetector()

    def scan(
        self,
        file_path
    ):

        findings = []

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                for line_number, line in enumerate(
                    file,
                    start=1
                ):

                    findings.extend(
                        self.scan_patterns(
                            line,
                            line_number,
                            file_path
                        )
                    )

                    findings.extend(
                        self.scan_entropy(
                            line,
                            line_number,
                            file_path
                        )
                    )

            return findings

        except Exception:

            return []

    def scan_patterns(
        self,
        line,
        line_number,
        file_path
    ):

        results = []

        for pattern, vulnerability_type in SECRET_PATTERNS:

            match = re.search(
                pattern,
                line
            )

            if not match:
                continue

            secret_value = match.group(2)

            if not ContextValidator.looks_like_real_secret(
                secret_value
            ):
                continue

            metadata = VULN_METADATA.get(
                vulnerability_type,
                {}
            )

            results.append({

                "type":
                    vulnerability_type,

                "line":
                    line_number,

                "file":
                    file_path,

                "code":
                    line.strip(),

                "severity":
                    metadata.get(
                        "severity",
                        "HIGH"
                    ),

                "message":
                    "Potential secret detected",

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

        return results

    def scan_entropy(
        self,
        line,
        line_number,
        file_path
    ):

        results = []

        entropy_findings = (
            self.entropy_detector.detect(line)
        )

        for finding in entropy_findings:

            results.append({

                "type":
                    "HARDCODED_SECRET",

                "line":
                    line_number,

                "file":
                    file_path,

                "code":
                    line.strip(),

                "severity":
                    "HIGH",

                "message":
                    f"High entropy secret detected "
                    f"(entropy={finding['entropy']})",

                "description":
                    "Potential credential leakage",

                "cwe":
                    "CWE-798",

                "owasp":
                    "A07:2021",
            })

        return results