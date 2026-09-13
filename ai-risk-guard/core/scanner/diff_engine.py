"""
core/scanner/diff_engine.py

Phase 2 diff-aware scanning engine.
Extracts modified files + changed line numbers + modified functions.
"""

import ast
import logging
import re

from utils.logger import logger

log = logging.getLogger("ai_risk_guard.diff_engine")

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _normalize_path(header_path: str) -> str:
    """Normalize a unified-diff file header path.

    Git's default ``a/``/``b/`` prefixes are stripped while paths without a
    prefix (``--no-prefix`` sources or third-party patches) pass through, so
    the file key matches the repository paths used by ``should_scan_line``.
    """
    path = header_path.strip()
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


class DiffAwareScanner:

    def parse_diff(
        self,
        diff_text,
        default_file=None
    ):
        if not isinstance(diff_text, str) or not diff_text.strip():
            logger.warning("Empty or invalid diff text provided", "DIFF")
            return {}

        try:
            changed_files = {}
            current_file = None
            current_line = 0

            lines = diff_text.splitlines()

            for line in lines:
                if line.startswith(("+++ ", "--- ")):
                    header_path = line[4:].strip()
                    # Deleted files are represented as +++ /dev/null; the real
                    # path arrives in the --- line, so /dev/null is ignored.
                    if header_path and header_path != "/dev/null":
                        current_file = _normalize_path(header_path)
                        changed_files.setdefault(current_file, set())

                elif line.startswith("@@"):
                    if current_file is None and default_file:
                        current_file = default_file
                        changed_files.setdefault(current_file, set())
                    match = _HUNK_RE.match(line)
                    if match:
                        current_line = int(match.group(2))

                elif line.startswith("\\"):
                    # Git "\\ No newline at end of file" continuation marker,
                    # not a source line — must not advance the new-line counter.
                    continue

                elif line.startswith("+") and not line.startswith("+++"):
                    if current_file:
                        changed_files[current_file].add(current_line)
                    current_line += 1

                elif not line.startswith("-"):
                    current_line += 1

            logger.info(
                f"Diff parsed: {len(changed_files)} files",
                "DIFF"
            )

            return changed_files

        except re.error as e:
            logger.error(f"Regex error in diff parser: {e}", "DIFF")
            return {}
        except Exception as e:
            logger.error(f"Diff parser failed: {e}", "DIFF")
            log.exception("Unhandled diff parser error")
            return {}

    def should_scan_line(
        self,
        file_path,
        line_number,
        diff_map
    ):

        if not diff_map:
            return True

        norm_file_path = file_path.replace("\\", "/")

        changed_lines = diff_map.get(file_path)
        if changed_lines is None:
            for diff_file, lines in diff_map.items():
                norm_diff_file = diff_file.replace("\\", "/")
                if norm_file_path.endswith(norm_diff_file) or norm_diff_file.endswith(norm_file_path):
                    changed_lines = lines
                    break

        if changed_lines is None:
            return False

        return line_number in changed_lines

    # =============================================================
    # FUNCTION-LEVEL DIFF PARSING
    # =============================================================

    def get_function_line_ranges(self, code_text: str) -> dict:
        """Parse AST to find all function definitions and their line ranges."""
        try:
            tree = ast.parse(code_text)
            ranges = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_line = getattr(node, "end_lineno", node.lineno)
                    ranges[node.name] = (node.lineno, end_line)
            return ranges
        except SyntaxError:
            return {}

    def get_modified_functions(self, file_path: str, code_text: str, diff_map: dict) -> list:
        """Map changed lines to function names. Returns list of modified function names."""
        ranges = self.get_function_line_ranges(code_text)
        if not ranges:
            return []

        norm_file_path = file_path.replace("\\", "/")
        changed_lines = diff_map.get(file_path)
        if changed_lines is None:
            for diff_file, lines in diff_map.items():
                norm_diff_file = diff_file.replace("\\", "/")
                if norm_file_path.endswith(norm_diff_file) or norm_diff_file.endswith(norm_file_path):
                    changed_lines = lines
                    break

        if not changed_lines:
            return []

        modified = set()
        for func_name, (start, end) in ranges.items():
            for line in changed_lines:
                if start <= line <= end:
                    modified.add(func_name)
                    break

        logger.info(f"Modified functions in {file_path}: {list(modified)}", "DIFF")
        return list(modified)
