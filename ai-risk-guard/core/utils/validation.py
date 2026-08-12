"""
core/utils/validation.py
Input validation and sanitization utilities.
"""

import os
import re

from core.exceptions import InputValidationError

# Path traversal patterns
_PATH_TRAVERSAL_PATTERNS = re.compile(r"(\.\./|\.\.\\)")
# Null byte injection
_NULL_BYTE = re.compile(r"\0")
# Only allow safe file extensions
_SAFE_EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".toml", ".env", ".md", ".txt", ".cfg", ".ini", ".conf"}


def validate_file_path(file_path: str, allow_absolute: bool = False) -> str:
    """Validate and sanitize a file path. Raises InputValidationError on invalid input."""
    if not isinstance(file_path, str) or not file_path.strip():
        raise InputValidationError("file_path must be a non-empty string")

    if _NULL_BYTE.search(file_path):
        raise InputValidationError("file_path contains null byte")

    if not allow_absolute and os.path.isabs(file_path):
        raise InputValidationError("absolute paths are not allowed")

    norm = os.path.normpath(file_path)

    if _PATH_TRAVERSAL_PATTERNS.search(norm):
        raise InputValidationError("path traversal detected in file_path")

    return norm


def validate_diff_data(diff_data: str | None) -> str | None:
    """Validate diff data input."""
    if diff_data is None:
        return None
    if not isinstance(diff_data, str):
        raise InputValidationError("diff_data must be a string or None")
    if len(diff_data) > 10 * 1024 * 1024:  # 10 MB limit
        raise InputValidationError("diff_data exceeds maximum size of 10 MB")
    return diff_data


def validate_code_input(code: str, max_size: int = 5 * 1024 * 1024) -> str:
    """Validate code input. Raises InputValidationError on invalid input."""
    if not isinstance(code, str):
        raise InputValidationError("code must be a string")
    if not code.strip():
        raise InputValidationError("code must not be empty")
    if len(code) > max_size:
        raise InputValidationError(f"code exceeds maximum size of {max_size} bytes")
    return code


def safe_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and injection."""
    sanitized = os.path.basename(filename)
    sanitized = _NULL_BYTE.sub("", sanitized)
    return sanitized
