"""
core/scanner/diff_engine.py

Phase 2 diff-aware scanning engine.
Extracts modified files + changed line numbers.
"""

import re

from utils.logger import logger


class DiffAwareScanner:

    def parse_diff(
        self,
        diff_text
    ):

        try:

            changed_files = {}

            current_file = None
            current_line = 0

            lines = diff_text.splitlines()

            for line in lines:

                # -------------------------------------------------
                # FILE DETECTION
                # -------------------------------------------------

                if line.startswith("+++ b/"):

                    current_file = (
                        line.replace("+++ b/", "")
                        .strip()
                    )

                    changed_files.setdefault(
                        current_file,
                        set()
                    )

                # -------------------------------------------------
                # HUNK HEADER
                # @@ -10,5 +20,8 @@
                # -------------------------------------------------

                elif line.startswith("@@"):

                    match = re.search(
                        r"\+(\d+)",
                        line
                    )

                    if match:
                        current_line = int(
                            match.group(1)
                        )

                # -------------------------------------------------
                # ADDED LINE
                # -------------------------------------------------

                elif (
                    line.startswith("+")
                    and
                    not line.startswith("+++")
                ):

                    if current_file:

                        changed_files[
                            current_file
                        ].add(current_line)

                    current_line += 1

                # -------------------------------------------------
                # NORMAL CONTEXT
                # -------------------------------------------------

                elif not line.startswith("-"):

                    current_line += 1

            logger.info(
                f"Diff parsed: {len(changed_files)} files",
                "DIFF"
            )

            return changed_files

        except Exception as error:

            logger.error(
                f"Diff parser failed: {error}",
                "DIFF"
            )

            return {}

    def should_scan_line(
        self,
        file_path,
        line_number,
        diff_map
    ):

        if not diff_map:
            return True

        changed_lines = diff_map.get(
            file_path,
            set()
        )

        return line_number in changed_lines