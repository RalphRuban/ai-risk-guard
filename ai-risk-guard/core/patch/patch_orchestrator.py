"""
Transactional patch orchestration engine.
Applies patches safely with conflict detection.
"""

import difflib
from typing import List, Dict, Callable, Any

from core.patch.conflict_analyzer import ConflictAnalyzer
from core.patch.dependency_graph import DependencyGraph
from utils.logger import logger


def apply_patches_safely(
    code: str,
    vulnerabilities: List[Dict],
    patch_function: Callable,
) -> Dict[str, Any]:
    """
    Apply patches safely, tracking conflicts and errors.
    
    Args:
        code: Original source code
        vulnerabilities: List of vulnerability dictionaries
        patch_function: Function to apply individual patches
    
    Returns:
        Dictionary with final_code, applied, conflicts, errors, combined_diff
    """

    analyzer = ConflictAnalyzer()
    graph = DependencyGraph()

    applied: List[Dict] = []
    conflicts: List[Dict] = []
    errors: List[str] = []

    current_code: str = code

    logger.info(f"Orchestrating patches for {len(vulnerabilities)} findings", "PATCH")

    # Use DependencyGraph for topological sorting of vulnerabilities
    sorted_lines = graph.build_from_vulnerabilities(vulnerabilities)
    
    # Sort vulnerabilities based on topological order (reverse for line safety)
    line_to_vuln = {v.get("line"): v for v in vulnerabilities}
    ordered_vulnerabilities = [line_to_vuln[line] for line in sorted_lines if line in line_to_vuln]
    ordered_vulnerabilities.reverse()

    for vuln in ordered_vulnerabilities:
        vuln_type = vuln.get('type')
        line = vuln.get('line')

        if analyzer.has_conflict(vuln):
            logger.warning(f"Conflict detected for {vuln_type} at line {line}, skipping", "PATCH")
            conflicts.append(vuln)
            continue

        result = patch_function(
            current_code,
            vuln
        )

        if not result.get("ast_success"):
            logger.error(f"Failed to patch {vuln_type} at line {line}", "PATCH")
            conflicts.append(vuln)

            if result.get("error"):
                errors.append(result["error"])

            continue

        current_code = result["patched_code"]
        applied.append(vuln)
        analyzer.register(vuln)
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