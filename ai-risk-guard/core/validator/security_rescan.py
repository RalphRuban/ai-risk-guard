"""
Security re-scan engine.
Ensures vulnerability was removed after patching.
"""

import os
import tempfile

from core.scanner.vulnerability_scanner import VulnerabilityScanner


class SecurityRescanner:

    def rescan_code(self, code: str):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py",
                delete=False,
                mode="w",
                encoding="utf-8"
            ) as temp:
                temp.write(code)
                temp_path = temp.name

            # Perform the scan. A fresh scanner per call keeps this class free
            # of cross-call mutable state so concurrent rescan_code calls (the
            # validator validates candidates in a thread pool) cannot corrupt
            # one another's findings.
            scanner = VulnerabilityScanner()
            vulnerabilities = scanner.scan_file(temp_path)

            # If the scanner returns None or an empty list, 
            # we need to be careful. In Phase 2, an empty list 
            # means no vulnerabilities WERE FOUND.
            return {
                "success": vulnerabilities is not None and len(vulnerabilities) == 0,
                "remaining_vulnerabilities": vulnerabilities or [],
            }

        except Exception as e:
            from utils.logger import logger
            logger.error(f"SecurityRescanner failed: {e}", "VALIDATOR")
            return {
                "success": False,
                "remaining_vulnerabilities": [],
                "error": str(e)
            }

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass