"""
Entropy-based secret detection engine.
Research-oriented secret scanner.
"""

import math
import re


SECRET_KEYWORDS = {
    "token",
    "secret",
    "password",
    "apikey",
    "api_key",
    "access_key",
}


class EntropyDetector:

    def shannon_entropy(self, data: str):

        if not data:
            return 0.0

        entropy = 0.0

        for char in set(data):

            probability = data.count(char) / len(data)

            entropy -= probability * math.log2(probability)

        return round(entropy, 3)

    def looks_sensitive(self, variable_name: str):

        variable_name = variable_name.lower()

        return any(
            keyword in variable_name
            for keyword in SECRET_KEYWORDS
        )

    def detect(self, line: str):

        matches = re.findall(
            r'([A-Za-z0-9_\-]{16,})',
            line
        )

        findings = []

        for token in matches:

            entropy = self.shannon_entropy(token)

            if entropy >= 3.5:

                findings.append({
                    "token": token,
                    "entropy": entropy,
                })

        return findings