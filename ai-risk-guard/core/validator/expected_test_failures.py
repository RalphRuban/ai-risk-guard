"""
Expected test-failure attribution.

When a security patch removes a vulnerability, regression tests written against
the pre-patch code may pin the vulnerable behavior (e.g. asserting the hardcoded
API token, the MD5 digest, or ``shell=True``). Such tests are EXPECTED to fail
after a correct fix and must not be reported as regressions.

Attribution is diff-based: a failing test is "expected" when it references a
symbol (function, module-level variable, class) whose code the patch changed.
No extra test execution is required.
"""

from __future__ import annotations

import ast
import re
from typing import Any

_TEST_OUTCOME_RE = re.compile(
    r"::([A-Za-z_]\w*)(?:\[[^\]]*\])?\s+(PASSED|FAILED|ERROR|SKIPPED)"
)


def _module_symbols(source: str) -> dict[str, str]:
    """Map top-level symbol names to their normalized AST dump."""
    symbols: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return symbols

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            symbols[node.name] = ast.dump(node, include_attributes=False)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols[f"{node.name}.{item.name}"] = ast.dump(
                        item, include_attributes=False
                    )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in _assign_targets(node):
                if isinstance(target, ast.Name):
                    symbols[target.id] = ast.dump(node, include_attributes=False)
    return symbols


def _assign_targets(node: ast.Assign | ast.AnnAssign) -> list[ast.AST]:
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    targets: list[ast.AST] = []
    for target in node.targets:
        if isinstance(target, ast.Name):
            targets.append(target)
        elif isinstance(target, (ast.Tuple, ast.List)):
            targets.extend(_flatten_tuple(target))
    return targets


def _flatten_tuple(node: ast.Tuple | ast.List) -> list[ast.AST]:
    out: list[ast.AST] = []
    for el in node.elts:
        if isinstance(el, ast.Name):
            out.append(el)
        elif isinstance(el, (ast.Tuple, ast.List)):
            out.extend(_flatten_tuple(el))
    return out


def _referenced_names(node: ast.AST) -> set[str]:
    """Collect every identifier referenced inside an AST subtree."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.ImportFrom):
            if child.module:
                names.add(child.module.split(".")[0])
            for alias in child.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(child, ast.Import):
            for alias in child.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names


def changed_symbols(original: str, patched: str) -> set[str]:
    """Return top-level symbol names whose definition differs between versions."""
    orig = _module_symbols(original or "")
    patched_map = _module_symbols(patched or "")
    changed: set[str] = set()
    for name in set(orig) | set(patched_map):
        if orig.get(name) != patched_map.get(name):
            changed.add(name)
    return changed


def parse_test_outcomes(output: str) -> dict[str, str]:
    """Parse pytest verbose output into {test_name: status}."""
    outcomes: dict[str, str] = {}
    if not output:
        return outcomes
    for line in output.splitlines():
        m = _TEST_OUTCOME_RE.search(line)
        if m:
            outcomes[m.group(1)] = m.group(2)
    return outcomes


def classify(
    original: str,
    patched: str,
    test_source: str,
    failing_names: list[str],
) -> dict[str, list[str]]:
    """Split failing test names into expected (pin removed behavior) vs regressions."""
    expected: list[str] = []
    regressions: list[str] = []
    changed = changed_symbols(original, patched)

    funcs: dict[str, Any] = {}
    try:
        tree = ast.parse(test_source or "")
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.setdefault(node.name, node)

    for name in failing_names:
        base = re.sub(r"\[[^\]]*\]$", "", name)
        fn = funcs.get(base)
        if fn is None:
            regressions.append(name)
            continue
        if _referenced_names(fn) & changed:
            expected.append(name)
        else:
            regressions.append(name)

    return {"expected": expected, "regressions": regressions}


def analyze_test_results(
    original: str,
    patched: str,
    test_source: str,
    output: str,
) -> dict[str, Any]:
    """Full analysis of a pytest run against an original/patched source pair."""
    outcomes = parse_test_outcomes(output)
    failing = [name for name, status in outcomes.items() if status in ("FAILED", "ERROR")]
    passing = [name for name, status in outcomes.items() if status == "PASSED"]
    result = classify(original, patched, test_source, failing)
    return {
        "passing_tests": passing,
        "failing_tests": failing,
        "expected_failures": result["expected"],
        "regression_failures": result["regressions"],
        "expected": len(result["expected"]),
        "regressions": len(result["regressions"]),
    }
