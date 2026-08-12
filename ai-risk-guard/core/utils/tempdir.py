"""
core/utils/tempdir.py
TempDir context manager that guarantees cleanup even on exceptions.
"""

import logging
import os
import shutil
import tempfile

logger = logging.getLogger("ai_risk_guard.tempdir")


class TempDir:
    """Context manager for a temporary directory that is always cleaned up."""

    def __init__(self, prefix="airisk_"):
        self._prefix = prefix
        self._path = None

    def __enter__(self) -> str:
        self._path = tempfile.mkdtemp(prefix=self._prefix)
        return self._path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._path is not None and os.path.isdir(self._path):
            for attempt in range(3):
                try:
                    shutil.rmtree(self._path, ignore_errors=False)
                    return False
                except (OSError, PermissionError) as e:
                    if attempt < 2:
                        import time
                        time.sleep(1)
                    else:
                        logger.error("Failed to clean up temp dir %s: %s", self._path, e)
        return False
