"""
core/scanner/test_file_fetcher.py
Predicts and fetches test files from GitHub for a given source file.
Used to enable Stage 5 (regression tests) in patch validation.
"""

import ast
import base64
import logging
import os
import sys

import requests

log = logging.getLogger("ai_risk_guard.test_file_fetcher")

_STDLIB: frozenset = frozenset(getattr(sys, "stdlib_module_names", ()))


def _case_variant(stem: str) -> str:
    """Toggle the case of the first letter of *stem*.

    Returns the original *stem* unchanged if it has no alphabetic first
    character.
    """
    if stem and stem[0].islower():
        return stem[0].upper() + stem[1:]
    if stem and stem[0].isupper():
        return stem[0].lower() + stem[1:]
    return stem


def predict_test_candidates(source_file: str) -> list[str]:
    """Generate candidate test file paths for a source file.

    Given a source file like ``src/auth/login.py``, generates candidates
    matching common test naming conventions:
    - ``test_login.py`` (flat in same dir)
    - ``login_test.py``
    - ``tests/test_login.py``
    - ``tests/login_test.py``
    - ``tests/src/auth/test_login.py`` (mirrored structure)
    - etc.

    Returns candidates in priority order (most likely first).
    """
    source_file = source_file.replace("\\", "/")
    parts = source_file.split("/")
    basename = parts[-1]
    name_no_ext = os.path.splitext(basename)[0]
    dirname = os.path.dirname(source_file)
    parent_dir = parts[-2] if len(parts) > 1 else ""

    candidates = []

    # 1. Flat naming in same directory
    candidates.append(f"test_{basename}")
    candidates.append(f"{name_no_ext}_test.py")

    # 2. Flat naming with parent directory prefix
    if parent_dir:
        candidates.append(f"test_{parent_dir}_{name_no_ext}.py")
        candidates.append(f"{parent_dir}_{name_no_ext}_test.py")
        candidates.append(f"test_{parent_dir}_{basename}")

    # 3. Subdirectory of source's directory
    if dirname:
        candidates.append(os.path.join(dirname, f"test_{basename}").replace("\\", "/"))
        candidates.append(os.path.join(dirname, f"{name_no_ext}_test.py").replace("\\", "/"))

    # 4. Flat tests/ directory
    candidates.append(f"tests/test_{basename}")
    candidates.append(f"tests/{name_no_ext}_test.py")
    if parent_dir:
        candidates.append(f"tests/test_{parent_dir}_{name_no_ext}.py")
        candidates.append(f"tests/{parent_dir}_{name_no_ext}_test.py")

    # 5. Mirrored structure in tests/
    if dirname:
        candidates.append(f"tests/{dirname}/test_{basename}".replace("\\", "/"))
        candidates.append(f"tests/{dirname}/{name_no_ext}_test.py".replace("\\", "/"))

    # 6. Tests mirror with parent prefix (e.g. test_auth_login.py in tests/)
    if parent_dir:
        candidates.append(f"tests/test_{parent_dir}_{name_no_ext}.py")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    # Add case variants (e.g. Demo1_test.py for source demo1.py)
    case_var = _case_variant(name_no_ext)
    if case_var != name_no_ext:
        for c in list(unique):
            var = c.replace(name_no_ext, case_var, 1)
            if var not in seen:
                seen.add(var)
                unique.append(var)

    return unique


def fetch_test_file_content(
    repo_name: str,
    branch: str,
    test_file_path: str,
    access_token: str,
    ref: str = "",
    timeout: int = 10,
) -> str | None:
    """Fetch a single test file from GitHub via the Contents API.

    When *ref* is given (e.g. a commit SHA) the file is fetched at that exact
    ref instead of the moving *branch* head. Returns the file content as a
    string, or ``None`` if the file does not exist or cannot be fetched.
    """
    url = f"https://api.github.com/repos/{repo_name}/contents/{test_file_path}?ref={ref or branch}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            log.info(f"Fetched test file: {test_file_path} ({len(content)} bytes)")
            return content
        elif response.status_code == 404:
            log.debug(f"Test file not found: {test_file_path}")
            return None
        else:
            log.warning(
                f"Failed to fetch test file {test_file_path}: "
                f"{response.status_code} {response.text[:200]}"
            )
            return None
    except requests.Timeout:
        log.warning(f"Timeout fetching test file: {test_file_path}")
        return None
    except requests.RequestException as e:
        log.error(f"Error fetching test file {test_file_path}: {e}")
        return None
    except (ValueError, KeyError, UnicodeDecodeError) as e:
        log.error(f"Error decoding test file {test_file_path}: {e}")
        return None


def _import_modules(test_content: str) -> list[str]:
    """Return the fully-qualified modules imported by *test_content*."""
    modules: list[str] = []
    try:
        tree = ast.parse(test_content)
    except (SyntaxError, TypeError):
        return modules
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def is_relevant_test(test_content: str, source_file: str) -> bool:
    """Return True when *test_content* plausibly tests *source_file*.

    Relevance is judged by module-name overlap: the test imports a module
    whose basename matches the source file stem (e.g. source ``demo1.py``
    and the test importing ``demo1``, ``src.demo1`` or ``tests.demo1``).
    """
    source_stem = os.path.splitext(os.path.basename(source_file))[0].lower()
    if not source_stem:
        return False
    return any(
        module.rsplit(".", 1)[-1].lower() == source_stem
        for module in _import_modules(test_content)
    )


def discover_and_fetch_test_file(
    repo_name: str,
    branch: str,
    source_file: str,
    access_token: str,
    cache,
    commit_sha: str = "",
) -> tuple[str | None, str | None]:
    """Predict test file candidates for *source_file* and try each one.

    Uses the cache first. If a candidate is cached as ``None`` (previously
    not found), it is skipped. Otherwise, the cache is consulted for the
    test file content, and if not present, fetched from GitHub. The result
    is stored in the cache.

    Candidates that exist but do not reference *source_file* are passed over
    in favour of more relevant candidates. If none of the existing candidates
    are relevant, the first existing one is returned as a best-effort
    fallback (preserving prior behaviour for loosely-named test repos).

    Returns ``(content, matched_path)`` of the first successfully fetched
    test file, or ``(None, None)`` if no candidate exists.
    """
    candidates = predict_test_candidates(source_file)

    first_existing: tuple[str | None, str | None] = (None, None)
    resolved: set[str] = set()
    for candidate_path in candidates:
        if not cache.has_entry(repo_name, branch, candidate_path, commit_sha):
            continue
        resolved.add(candidate_path)
        cached = cache.get(repo_name, branch, candidate_path, commit_sha)
        if cached is None:
            continue
        if is_relevant_test(cached, source_file):
            log.info(f"Test file cache hit (relevant): {candidate_path}")
            return cached, candidate_path
        if first_existing[1] is None:
            first_existing = (cached, candidate_path)

    # Cache miss for the remaining candidates — try fetching from GitHub
    for candidate_path in candidates:
        if candidate_path in resolved:
            continue
        content = fetch_test_file_content(
            repo_name, branch, candidate_path, access_token, ref=commit_sha
        )
        cache.set(repo_name, branch, candidate_path, content, commit_sha)
        if content is not None:
            if is_relevant_test(content, source_file):
                log.info(f"Discovered relevant test file: {candidate_path} for source: {source_file}")
                return content, candidate_path
            if first_existing[1] is None:
                first_existing = (content, candidate_path)

    if first_existing[1] is not None:
        log.info(f"No relevant test file for {source_file}; using best-effort {first_existing[1]}")
        return first_existing

    log.info(f"No test file found for: {source_file}")
    return None, None


def _module_under_test(module: str, source_file: str) -> bool:
    """Return True when *module* names the file under test (e.g. ``demo1``)."""
    source_stem = os.path.splitext(os.path.basename(source_file))[0].lower()
    if not source_stem:
        return False
    return module.rsplit(".", 1)[-1].lower() == source_stem


def _module_file_candidates(module: str) -> list[str]:
    """Repo-relative file paths a module may map to (module or package)."""
    rel = module.replace(".", "/")
    return [rel + ".py", rel + "/__init__.py"]


def _known_third_party_packages() -> frozenset:
    try:
        from core.validator.sandbox import Sandbox
        return frozenset(Sandbox._KNOWN_DOCKER_PACKAGES)
    except ImportError:
        return frozenset()


def fetch_test_dependencies(
    repo_name: str,
    branch: str,
    source_file: str,
    test_content: str,
    access_token: str,
    cache,
    known_packages: frozenset | None = None,
    commit_sha: str = "",
    timeout: int = 10,
) -> list[dict]:
    """Fetch repo-relative modules a test file depends on, plus conftest.

    Imports that resolve to the module under test, the standard library, or
    known third-party packages are never fetched — the module under test is
    left to the runtime rebinding logic so regression tests exercise the
    patched code rather than a stale repo mirror.

    Returns a list of ``{"path": ..., "content": ...}`` dicts for files that
    actually exist in the repository.
    """
    excluded = set(known_packages or ()) | _known_third_party_packages() | set(_STDLIB)
    dep_paths = set()
    for module in _import_modules(test_content):
        root = module.split(".")[0]
        if root in excluded:
            continue
        if _module_under_test(module, source_file):
            continue
        for rel_path in _module_file_candidates(module):
            dep_paths.add(rel_path)
            parent = os.path.dirname(rel_path).replace(os.sep, "/")
            while parent:
                dep_paths.add(parent + "/__init__.py")
                parent = os.path.dirname(parent)

    dep_paths.add("conftest.py")
    dep_paths.add("tests/conftest.py")

    deps = []
    for rel_path in sorted(dep_paths):
        if cache.has_entry(repo_name, branch, rel_path, commit_sha):
            cached = cache.get(repo_name, branch, rel_path, commit_sha)
            if cached is not None:
                deps.append({"path": rel_path, "content": cached})
            continue
        content = fetch_test_file_content(
            repo_name, branch, rel_path, access_token, ref=commit_sha, timeout=timeout
        )
        cache.set(repo_name, branch, rel_path, content, commit_sha)
        if content is not None:
            deps.append({"path": rel_path, "content": content})
    return deps
