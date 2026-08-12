"""
Best-effort rebinding of test-file imports to the module under validation.

When a fetched test file imports from a repo module that is not staged in
the sandbox (e.g. ``from tests.demo import fetch_url`` while the patched
module is ``demo1.py``), the test cannot run and the sandbox would otherwise
try to pip-install the top-level root (``tests``). This module rewrites such
imports to the scanned source module so regression tests can actually run,
or signals that the stage should be skipped with a clear reason.
"""

import ast
import os
import re


def _module_names(source_code: str) -> set:
    """Return top-level names defined or imported by *source_code*.

    Covers function/class definitions, top-level assignments (constants such
    as ``API_TOKEN``), annotated/compound assignments, and import aliases.
    """
    names: set[str] = set()
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, TypeError):
        return names
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _source_module_path(source_filename: str) -> str:
    """Derive the importable module path of *source_filename* (no ``.py``)."""
    normalized = source_filename.replace(os.sep, "/")
    normalized = normalized.removesuffix(".py")
    return normalized.replace("/", ".").strip(".")


def rebind_test_imports(
    test_content: str,
    source_code: str,
    source_filename: str,
    candidate_roots: set,
) -> tuple[str, dict]:
    """Best-effort rebind of unresolvable test imports to the patched module.

    Only ``from <root[.sub]> import (names)`` statements whose top-level root
    is in *candidate_roots* (the set the sandbox flagged as missing) are
    considered. For each:

    - **all** requested names exist in the source module -> rewrite the
      import to the source module path (e.g. ``tests.demo`` -> ``demo1``);
    - **some** names missing -> mark the stage skipped (the test targets a
      module that does not match the patched code);
    - **none** present -> treated as a genuine third-party dependency and
      left untouched for the pip-install path.

    Plain/dotted ``import`` statements are never rewritten.

    Returns ``(content, info)`` where ``info`` contains ``rebound``,
    ``skip``, ``reason`` and ``rebound_map`` keys.
    """
    info: dict = {"rebound": False, "skip": False, "reason": None, "rebound_map": {}}
    if not test_content or not source_code or not source_filename or not candidate_roots:
        return test_content, info

    try:
        tree = ast.parse(test_content)
    except (SyntaxError, TypeError):
        return test_content, info

    try:
        ast.parse(source_code)
    except (SyntaxError, TypeError) as e:
        info.update({
            "skip": True,
            "reason": f"source module could not be parsed: {e}",
        })
        return test_content, info

    source_names = _module_names(source_code)
    if not source_names:
        return test_content, info

    to_module = _source_module_path(source_filename)
    rebind_plan = []
    missing_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root not in candidate_roots:
                continue
            imported = [alias.name for alias in node.names]
            present = [name for name in imported if name in source_names]
            if not present:
                continue
            if len(present) == len(imported):
                rebind_plan.append((node.module, to_module))
            else:
                absent = [name for name in imported if name not in source_names]
                missing_imports.append((node.module, absent))

    if missing_imports:
        details = "; ".join(
            f"'{name}' not defined in {to_module}" for _, names in missing_imports for name in names
        )
        info.update({
            "skip": True,
            "reason": (
                f"test imports from {', '.join(module for module, _ in missing_imports)} "
                f"which does not match the patched module ({details})"
            ),
            "missing_modules": sorted({module for module, _ in missing_imports}),
        })
        return test_content, info

    if rebind_plan:
        content = test_content
        for from_module, _ in rebind_plan:
            content = re.sub(
                r"(?<!\w)from\s+" + re.escape(from_module) + r"\s+import",
                f"from {to_module} import",
                content,
                flags=re.MULTILINE,
            )
        info.update({
            "rebound": True,
            "rebound_map": dict(rebind_plan),
        })
        return content, info

    return test_content, info
