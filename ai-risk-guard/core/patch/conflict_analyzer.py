"""
Structural patch conflict analyzer.
Tracks which vulnerabilities have been patched to avoid duplicate patches.
"""

from typing import Dict, Set


class ConflictAnalyzer:
    """Tracks patch conflicts during multi-vulnerability fixing."""

    def __init__(self):
        self.used_lines: Set[int] = set()

    def has_conflict(self, vuln: Dict) -> bool:
        """Check if vulnerability line already patched."""
        line = vuln.get("line")

        if line in self.used_lines:
            return True

        return False

    def register(self, vuln: Dict) -> None:
        """Mark vulnerability as patched."""
        line = vuln.get("line")

        self.used_lines.add(line)