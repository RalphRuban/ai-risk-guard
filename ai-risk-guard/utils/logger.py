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
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE    = Path("data/logs.json")
MAX_BYTES   = 5 * 1024 * 1024   # 5 MB per file
BACKUP_COUNT = 3                  # keep 3 rotated backups


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        module  = getattr(record, "app_module", "GENERAL")
        trace_id = getattr(record, "trace_id", None)
        
        log_entry = {
            "time":    datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level":   record.levelname,
            "module":  module,
            "message": record.getMessage(),
        }
        
        if trace_id:
            log_entry["trace_id"] = trace_id

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


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

    def _emit(self, level: int, message: str, module: str, trace_id: str | None = None, exc_info: bool = False):
        extra = {"app_module": module}
        if trace_id:
            extra["trace_id"] = trace_id
        _log.log(level, message, extra=extra, exc_info=exc_info)

    def info(self, message: str, module: str = "GENERAL", trace_id: str | None = None, exc_info: bool = False):
        self._emit(logging.INFO, message, module, trace_id, exc_info=exc_info)

    def error(self, message: str, module: str = "GENERAL", trace_id: str | None = None, exc_info: bool = False):
        self._emit(logging.ERROR, message, module, trace_id, exc_info=exc_info)

    def warning(self, message: str, module: str = "GENERAL", trace_id: str | None = None, exc_info: bool = False):
        self._emit(logging.WARNING, message, module, trace_id, exc_info=exc_info)

    def debug(self, message: str, module: str = "GENERAL", trace_id: str | None = None, exc_info: bool = False):
        self._emit(logging.DEBUG, message, module, trace_id, exc_info=exc_info)


logger = Logger()