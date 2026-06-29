"""
utils/logger.py
Structured logger using Python's built-in logging module.
- Writes JSON lines to data/logs.json with rotation (5 MB × 3 backups)
- Also streams to stdout so Docker / cloud log collectors pick it up
- Drop-in replacement: logger.info(...) / logger.error(...) API unchanged
"""

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE    = Path("data/logs.json")
MAX_BYTES   = 5 * 1024 * 1024   # 5 MB per file
BACKUP_COUNT = 3                  # keep 3 rotated backups


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        module  = getattr(record, "app_module", "GENERAL")
        return json.dumps({
            "time":    datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "module":  module,
            "message": record.getMessage(),
        })


def _build_logger() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("ai_risk_guard")
    log.setLevel(logging.DEBUG)

    if log.handlers:          # avoid duplicate handlers on reload
        return log

    formatter = _JsonFormatter()

    # Rotating file handler
    fh = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    log.addHandler(fh)

    # Stdout handler (for Docker / cloud)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    log.addHandler(sh)

    return log


_log = _build_logger()


class Logger:
    """
    Thin wrapper that preserves the original logger.info(msg, module) API.
    """

    def _emit(self, level: int, message: str, module: str):
        extra = {"app_module": module}
        _log.log(level, message, extra=extra)

    def info(self, message: str, module: str = "GENERAL"):
        self._emit(logging.INFO, message, module)

    def error(self, message: str, module: str = "GENERAL"):
        self._emit(logging.ERROR, message, module)

    def warning(self, message: str, module: str = "GENERAL"):
        self._emit(logging.WARNING, message, module)

    def debug(self, message: str, module: str = "GENERAL"):
        self._emit(logging.DEBUG, message, module)


logger = Logger()