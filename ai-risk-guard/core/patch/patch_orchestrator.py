"""
Transactional patch orchestration engine.
Applies patches safely with conflict detection.
"""

import difflib
from collections.abc import Callable
from typing import Any

from core.patch.fixers import SUPPORTED_FIXER_TYPES
from utils.logger import logger


def apply_patches_safely(
    code: str,
    vulnerabilities: list[dict],
    patch_function: Callable,
) -> dict[str, Any]:
    """
    Apply patches safely, tracking conflicts and errors.
    """

    used_lines: set[int] = set()
    applied: list[dict] = []
    conflicts: list[dict] = []
    errors: list[str] = []
    current_code: str = code

    logger.info(f"Orchestrating patches for {len(vulnerabilities)} findings", "PATCH")

    ordered_vulnerabilities = sorted(
        vulnerabilities,
        key=lambda v: int(v.get("line", 0)),
        reverse=True,
    )

    for vuln in ordered_vulnerabilities:
        vuln_type = vuln.get('type')
        line = int(vuln.get("line", 0))

        if line in used_lines:
            logger.warning(f"Conflict detected for {vuln_type} at line {line}, skipping", "PATCH")
            conflicts.append(vuln)
            continue

        result = patch_function(current_code, vuln)

        if not result.get("ast_success"):
            if result.get("error"):
                logger.error(f"Failed to patch {vuln_type} at line {line}: {result['error']}", "PATCH")
                errors.append(result["error"])
            elif vuln_type not in SUPPORTED_FIXER_TYPES:
                logger.info(f"No automated fixer for {vuln_type} at line {line} — informational", "PATCH")
            else:
                logger.warning(f"Fixer could not transform {vuln_type} at line {line}", "PATCH")
            conflicts.append(vuln)
            continue

        current_code = result["patched_code"]
        applied.append(vuln)
        used_lines.add(line)
        logger.info(f"Successfully applied patch for {vuln_type} at line {line}", "PATCH")

    combined_diff = "".join(
        difflib.unified_diff(
            code.splitlines(keepends=True),
            current_code.splitlines(keepends=True),
        )
    )

    logger.info(f"Patch orchestration complete: {len(applied)} applied, {len(conflicts)} skipped", "PATCH")

    return {
        "final_code": current_code,
        "applied": applied,
        "conflicts": conflicts,
        "errors": errors,
        "combined_diff": combined_diff,
    }