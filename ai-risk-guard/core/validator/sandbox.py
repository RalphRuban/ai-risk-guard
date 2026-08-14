"""
Hardened Docker sandbox validator.
"""

import ast
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

from core.cache.sandbox_cache import SandboxCache
from core.config import config
from core.exceptions import InputValidationError
from core.utils.tempdir import TempDir
from core.utils.validation import (
    safe_filename,
    safe_repo_path,
    validate_code_input,
    validate_file_path,
)
from core.validator.test_rebind import rebind_test_imports
from utils.logger import logger

log = logging.getLogger("ai_risk_guard.sandbox")

BLOCKED_PATTERNS = [
    r"os\.system\s*\(",
    r"os\.popen\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"pickle\.loads\s*\(",
    r"subprocess\.run\s*\(.*shell\s*=\s*True",
    r"subprocess\.Popen\s*\(",
    r"__import__\s*\(",
    r"compile\s*\(.*exec",
    r"shutil\.rmtree\s*\(",
    r"os\.remove\s*\(",
    r"os\.rename\s*\(",
    r"webbrowser\.open\s*\(",
]

ARGPARSE_REQUIRED_ARGS_RE = re.compile(
    r"error: the following arguments are required:"
)


def _build_parent_map(tree):
    """Build a child-to-parent mapping for an AST tree."""
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    return parents


def _is_in_pytest_raises(node, parents):
    """Check if a node is inside a ``with pytest.raises(...):`` block."""
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, ast.With):
            expr = current.context_expr
            if (isinstance(expr, ast.Call)
                    and isinstance(expr.func, ast.Attribute)
                    and isinstance(expr.func.value, ast.Name)
                    and expr.func.value.id == "pytest"
                    and expr.func.attr == "raises"):
                return True
        current = parents.get(id(current))
    return False


def _build_import_aliases(tree):
    """Map local names to their fully-qualified module/attribute targets.

    Handles ``import os as o`` -> ``o`` => ``os`` and
    ``from subprocess import run as r`` -> ``r`` => ``subprocess.run`` so that
    alias-based access like ``o.system()`` is caught by the safety screen.
    """
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                asname = alias.asname or alias.name
                aliases[asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                asname = alias.asname or alias.name
                aliases[asname] = f"{module}.{alias.name}" if module else alias.name
    return aliases


def _resolve_name(aliases, name):
    return aliases.get(name, name)


def contains_unsafe_pattern(code: str):
    """AST-aware safety pre-screening to avoid false positives on strings/comments.

    Safe patterns like ``with pytest.raises(TypeError): subprocess.run(..., shell=True)``
    are excluded because the dangerous call is the *test target*, not production code.
    """
    try:
        tree = ast.parse(code)
        parents = _build_parent_map(tree)
        aliases = _build_import_aliases(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    fn = node.func
                    val = fn.value
                    if isinstance(val, ast.Name):
                        resolved = _resolve_name(aliases, val.id)
                        # os.system(), os.popen(), os.remove(), os.rename()
                        if resolved == "os" and fn.attr in ("system", "popen", "remove", "rename") and not _is_in_pytest_raises(node, parents):
                            return True
                        # pickle.loads()
                        if resolved == "pickle" and fn.attr == "loads" and not _is_in_pytest_raises(node, parents):
                            return True
                        # subprocess.run, .Popen, .call (blocked unless shell=False is explicit)
                        if resolved == "subprocess" and fn.attr in ("run", "Popen", "call") and not _is_in_pytest_raises(node, parents):
                            shell_kw = next((kw for kw in node.keywords if kw.arg == "shell"), None)
                            if shell_kw is None:
                                return True
                            if not isinstance(shell_kw.value, ast.Constant) or shell_kw.value.value is not False:
                                return True
                        # ctypes.* — allows arbitrary memory/OS access; any usage is blocked
                        if resolved == "ctypes" and not _is_in_pytest_raises(node, parents):
                            return True
                        # shutil.rmtree()
                        if resolved == "shutil" and fn.attr == "rmtree" and not _is_in_pytest_raises(node, parents):
                            return True
                        # webbrowser.open()
                        if resolved == "webbrowser" and fn.attr == "open" and not _is_in_pytest_raises(node, parents):
                            return True
                if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "__import__") and not _is_in_pytest_raises(node, parents):
                    return True
                # builtins.eval / builtins.exec / builtins.__import__ and the
                # __builtins__ alias — must be blocked (no pytest.raises escape).
                if isinstance(node.func, ast.Attribute):
                    _bv = node.func.value
                    if isinstance(_bv, ast.Name) and _bv.id in ("builtins", "__builtins__") and node.func.attr in ("eval", "exec", "__import__"):
                        return True
                if isinstance(node.func, ast.Name) and node.func.id == "getattr" and not _is_in_pytest_raises(node, parents) and len(node.args) >= 2:
                    target = node.args[0]
                    attr = node.args[1]
                    if isinstance(target, ast.Name):
                        resolved = _resolve_name(aliases, target.id)
                        if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                            if resolved == "os" and attr.value in ("system", "popen", "remove", "rename"):
                                return True
                            if resolved == "subprocess" and attr.value in ("run", "Popen", "call"):
                                return True
                            if resolved == "pickle" and attr.value == "loads":
                                return True
                            if resolved in ("builtins", "__builtins__") and attr.value in ("eval", "exec", "__import__"):
                                return True
                if isinstance(node.func, ast.Name) and node.func.id == "compile":
                    # compile(source, ...) with mode='exec' or mode='eval'
                    raw_modes = [getattr(kw.value, "value", None) for kw in node.keywords if kw.arg == "mode"]
                    if raw_modes and any(m in ("exec", "eval") for m in raw_modes if m) and not _is_in_pytest_raises(node, parents):
                        return True
            elif isinstance(node, ast.Import):
                if any(_resolve_name(aliases, alias.name) == "ctypes" for alias in node.names):
                    return True
            elif isinstance(node, ast.ImportFrom):
                if node.module in ("builtins", "__builtins__") and any(
                    alias.name in ("eval", "exec", "__import__", "*") for alias in node.names
                ):
                    return True
                if node.module == "ctypes":
                    return True
        return False
    except SyntaxError:
        stripped = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        return any(re.search(pattern, stripped) for pattern in BLOCKED_PATTERNS)
    except Exception:
        stripped = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        return any(re.search(pattern, stripped) for pattern in BLOCKED_PATTERNS)


class Sandbox:

    _KNOWN_DOCKER_PACKAGES = frozenset({
        "pytest", "hypothesis", "requests", "asteval",
        "flask", "sqlalchemy", "bcrypt", "cryptography",
        "pydantic", "urllib3", "certifi", "jinja2",
        "markupsafe", "werkzeug", "six",
    })

    def __init__(self):
        self._docker_available = None
        self._image_verified = False
        self.image_unavailable = False
        self._orphans_cleaned = False
        self._sandbox_cache = SandboxCache()

    def _is_docker_available(self) -> bool:
        """Check if Docker is available on this system (cached)."""
        if self._docker_available is not None:
            return self._docker_available
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            self._docker_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._docker_available = False
        except Exception:
            self._docker_available = False
        return self._docker_available

    def _ready_for_execution(self, purpose: str) -> tuple[bool, str | None]:
        """Check Docker + image readiness with bounded retries.

        Returns ``(ready, reason)`` where ``reason`` is ``None`` when ready,
        otherwise ``"daemon"`` or ``"image"``. Retries cover transient daemon
        restarts (and a daemon that comes up mid-provisioning) so a brief Docker
        outage does not immediately fail a scan closed. Still fails closed when
        Docker or the image cannot be made available.
        """
        attempts = config.sandbox.docker.retry_attempts
        backoff = config.sandbox.docker.retry_backoff_seconds
        for attempt in range(attempts + 1):
            if self._is_docker_available() and self._docker_image_ready():
                self._record_sandbox_availability(True)
                return True, None
            if attempt < attempts:
                # Clear cached state so the next attempt re-probes the daemon
                # and re-attempts image provisioning.
                self._docker_available = None
                self._image_verified = False
                self.image_unavailable = False
                delay = backoff * (2 ** attempt)
                logger.warning(
                    f"Sandbox {purpose}: not ready (attempt {attempt + 1}/{attempts + 1}) — retrying in {delay}s",
                    "SANDBOX",
                )
                time.sleep(delay)
        if self._is_docker_available():
            self._record_sandbox_availability(False, "image")
            return False, "image"
        self._record_sandbox_availability(False, "daemon")
        return False, "daemon"

    def _force_kill_container(self, container_name: str):
        """Attempt to force-remove a Docker container with retry + kill escalation."""
        for attempt in range(3):
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    capture_output=True,
                    timeout=10,
                )
                return
            except subprocess.TimeoutExpired:
                logger.warning(f"Container {container_name} rm -f timeout (attempt {attempt+1}/3)")
                try:
                    subprocess.run(
                        ["docker", "kill", container_name],
                        capture_output=True,
                        timeout=5,
                    )
                except subprocess.TimeoutExpired:
                    logger.warning(f"Container {container_name} kill timeout (attempt {attempt+1}/3)")
            except FileNotFoundError:
                logger.warning("Docker binary not found for container cleanup")
                return
            except Exception as e:
                logger.warning(f"Container {container_name} cleanup error (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    def _cleanup_orphaned_containers(self):
        """Remove any orphaned sandbox containers from previous runs on startup."""
        if not self._is_docker_available():
            return
        try:
            result = subprocess.run(
                ["docker", "ps", "-aq", "--filter", "name=sandbox_", "--filter", "status=exited"],
                capture_output=True, timeout=10, text=True,
            )
            container_ids = result.stdout.strip().split()
            if not container_ids or (len(container_ids) == 1 and not container_ids[0]):
                return
            subprocess.run(
                ["docker", "rm", "-f"] + container_ids,
                capture_output=True, timeout=30,
            )
            logger.info(f"Cleaned up {len(container_ids)} orphaned sandbox container(s)", "SANDBOX")
        except Exception:
            pass

    def _ensure_image_available(self):
        """Verify the Docker image exists locally; pull or build it if missing (lazy, cached)."""
        if self._image_verified:
            return
        image = config.sandbox.docker.image
        self.image_unavailable = False
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True, timeout=10,
            )
            if result.returncode == 0:
                self._image_verified = True
                return
            logger.info(f"Docker image '{image}' not found locally, provisioning...", "SANDBOX")
            if not self._provision_image(image):
                self.image_unavailable = True
                logger.warning(
                    f"Docker image '{image}' could not be provisioned — "
                    "sandbox scans will fail closed until it is available",
                    "SANDBOX"
                )
        except Exception as e:
            self.image_unavailable = True
            logger.warning(f"Error checking Docker image '{image}': {e}", "SANDBOX")

    def _provision_image(self, image: str) -> bool:
        """Try to pull the image; for local (non-registry) images, build it if pull fails."""
        pull = subprocess.run(
            ["docker", "pull", image],
            capture_output=True, timeout=120,
        )
        if pull.returncode == 0:
            self._image_verified = True
            logger.info(f"Docker image '{image}' pulled successfully", "SANDBOX")
            return True

        if self._is_local_image_name(image):
            return self._build_image(image)
        logger.warning(
            f"Failed to pull Docker image '{image}': {pull.stderr.decode()[:500]}",
            "SANDBOX"
        )
        return False

    def _build_image(self, image: str) -> bool:
        """Build the sandbox image from its Dockerfile (repo-root context)."""
        if not config.sandbox.docker.build_local_image:
            logger.warning(
                f"Cannot provision local image '{image}': auto-build is disabled in config",
                "SANDBOX"
            )
            return False
        # Resolve the Dockerfile (and the build context) against the repo root so
        # the build works no matter which working directory the app runs from.
        repo_root = Path(__file__).resolve().parents[2]
        dockerfile = config.sandbox.docker.dockerfile
        if dockerfile and not os.path.isabs(dockerfile):
            dockerfile = str(repo_root / dockerfile)
        if not dockerfile or not os.path.exists(dockerfile):
            logger.warning(
                f"Cannot build local image '{image}': dockerfile '{dockerfile}' not found",
                "SANDBOX"
            )
            return False
        logger.info(
            f"Pull failed; building local image '{image}' from {dockerfile}...",
            "SANDBOX"
        )
        build = subprocess.run(
            ["docker", "build", "-f", dockerfile, "-t", image, str(repo_root)],
            capture_output=True, timeout=600,
        )
        if build.returncode == 0:
            self._image_verified = True
            logger.info(f"Docker image '{image}' built successfully", "SANDBOX")
            return True
        logger.warning(
            f"Failed to build Docker image '{image}': {build.stderr.decode()[:500]}",
            "SANDBOX"
        )
        return False

    @staticmethod
    def _is_local_image_name(image: str) -> bool:
        """A registry-qualified name contains '/'; bare names like 'repo:tag' are local builds."""
        return "/" not in image

    def docker_image_available(self) -> bool:
        """Return whether the sandbox image exists locally (no pull/build attempt).

        Lightweight check used by the health endpoint so it never triggers a
        potentially slow provisioning step.
        """
        if not self._is_docker_available():
            return False
        image = config.sandbox.docker.image
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _docker_image_ready(self) -> bool:
        """Ensure the image can be provisioned; returns True if it is ready to run."""
        self._ensure_image_available()
        return not self.image_unavailable

    @staticmethod
    def _cli_arguments_only(result) -> bool:
        """Return True when a failed run merely lacks required CLI arguments."""
        stderr = getattr(result, "stderr", None) or ""
        return "Traceback" not in stderr and bool(ARGPARSE_REQUIRED_ARGS_RE.search(stderr))

    @staticmethod
    def _track_sandbox_metrics(mode_label: str, success: bool, duration: float):
        try:
            from app.metrics import (
                sandbox_duration,
                sandbox_runs_total,
                sandbox_timeouts_total,
            )
            sandbox_runs_total.labels(mode=mode_label, success=str(success).lower()).inc()
            sandbox_duration.labels(mode=mode_label).observe(duration)
            if not success:
                base = mode_label.split("_")[0]
                sandbox_timeouts_total.labels(mode=base).inc()
        except Exception:
            pass

    @staticmethod
    def _record_sandbox_availability(available: bool, reason: str = ""):
        """Record sandbox availability + fail-closed events (best-effort)."""
        try:
            from app.metrics import sandbox_available, sandbox_fail_closed_total
            sandbox_available.set(1 if available else 0)
            if not available:
                sandbox_fail_closed_total.labels(reason=reason or "unknown").inc()
        except Exception:
            pass

    def _run_captured(self, cmd: list, timeout: int, max_bytes: int) -> subprocess.CompletedProcess:
        """Run a command, streaming stdout/stderr with a hard per-stream cap.

        Unlike ``subprocess.run(capture_output=True)`` this never buffers the
        full output in host memory, so a chatty container cannot exhaust the
        webhook process. The wall-clock timeout is still enforced.
        """
        import threading as _threading

        def _read_capped(stream, sink, marker_ref):
            n = 0
            truncated = False
            try:
                for line in iter(stream.readline, ""):
                    if n < max_bytes:
                        take = min(len(line), max_bytes - n)
                        sink.append(line[:take])
                        n += take
                    else:
                        truncated = True
            except Exception:
                pass
            finally:
                marker_ref["truncated"] = truncated
                try:
                    stream.close()
                except Exception:
                    pass

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        out_buf: list = []
        err_buf: list = []
        out_marker: dict = {"truncated": False}
        err_marker: dict = {"truncated": False}
        t_out = _threading.Thread(target=_read_capped, args=(proc.stdout, out_buf, out_marker), daemon=True)
        t_err = _threading.Thread(target=_read_capped, args=(proc.stderr, err_buf, err_marker), daemon=True)
        t_out.start()
        t_err.start()
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            t_out.join(timeout=5)
            t_err.join(timeout=5)
            raise
        finally:
            t_out.join(timeout=5)
            t_err.join(timeout=5)

        stdout = "".join(out_buf)
        stderr = "".join(err_buf)
        if out_marker["truncated"]:
            stdout += f"\n... (truncated at {max_bytes} bytes)"
        if err_marker["truncated"]:
            stderr += f"\n... (truncated at {max_bytes} bytes)"
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    def _do_docker_run(self, cmd: list, container_name: str, mode: str = "secure_validation", track_exit_code: bool = False, timeout: int | None = None, max_output_bytes: int | None = None) -> dict:
        """Execute a Docker command and handle common timeout/cleanup/truncation."""
        import time as _time
        start = _time.time()
        mode_label = "docker_test" if mode == "docker" else "docker_run"
        dc = config.sandbox.docker
        run_timeout = timeout or dc.timeout_seconds
        cap_bytes = max_output_bytes or dc.max_output_bytes
        # Report the network mode actually baked into the docker command (may
        # differ from the config default when a per-scan/network override is in
        # effect).
        effective_network = next(
            (arg.partition("=")[2] for arg in cmd if arg.startswith("--network=")),
            dc.network,
        )
        logger.info(
            f"Sandbox: running container={container_name} image={dc.image} "
            f"mode={mode_label} memory={dc.memory} cpu={dc.cpu} "
            f"timeout={run_timeout}s network={effective_network}",
            "SANDBOX"
        )
        if not self._orphans_cleaned:
            self._cleanup_orphaned_containers()
            self._orphans_cleaned = True
        self._ensure_image_available()
        try:
            result = self._run_captured(cmd, run_timeout, cap_bytes)
            success = result.returncode == 0
            response = {"success": success, "output": result.stdout, "error": result.stderr, "mode": mode}
            if track_exit_code:
                response["exit_code"] = result.returncode
            if mode != "docker" and result.stderr:
                response["success"] = response["success"] and "Traceback" not in result.stderr
            if not response["success"] and self._cli_arguments_only(result):
                response["success"] = True
                response["note"] = "cli_arguments_required"
            self._track_sandbox_metrics(mode_label, bool(response["success"]), _time.time() - start)
            return response
        except subprocess.TimeoutExpired:
            self._force_kill_container(container_name)
            self._track_sandbox_metrics(mode_label, False, _time.time() - start)
            return {"success": False, "error": "Sandbox timeout", "mode": mode}
        except FileNotFoundError:
            self._track_sandbox_metrics(mode_label, False, _time.time() - start)
            return {"success": False, "error": "Docker binary not found", "mode": mode}

    @staticmethod
    def _safe_test_path(test_file_path: str) -> str:
        """Return a safe path for test files preserving subdirectory structure."""
        if os.path.isabs(test_file_path):
            return safe_filename(test_file_path)
        return validate_file_path(test_file_path).replace(os.sep, "/")
    
    def _build_docker_cmd(self, container_name: str, mount_path: str, entry_point: list, network: str | None = None, read_only: bool | None = None) -> list:
        dc = config.sandbox.docker
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            f"--memory={dc.memory}",
            f"--cpus={dc.cpu}",
            f"--pids-limit={dc.pids_limit}",
            f"--network={network or dc.network}",
        ]
        if read_only is None:
            read_only = dc.read_only
        if read_only:
            cmd.append("--read-only")
        cmd.extend(["--tmpfs", dc.tmpfs])
        for cap in dc.cap_drop:
            cmd.extend(["--cap-drop", cap])
        for opt in dc.security_opts:
            cmd.extend(["--security-opt", opt])
        cmd.extend(["-v", f"{mount_path}:/app:ro", dc.image])
        cmd.extend(entry_point)
        return cmd

    @staticmethod
    def _detect_third_party_imports(*codes: str, workspace: str = "", source_filename: str = "") -> set:
        """Detect third-party imports in code that are NOT in the Docker image.

        Imports whose root resolves to a local module or package inside
        *workspace* (or matches the scanned source module stem) are treated
        as locally resolvable and excluded from the returned set.
        """
        imported = set()
        for code in codes:
            if not code:
                continue
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        imported.add(root)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    imported.add(root)
        stdlib = getattr(sys, "stdlib_module_names", None)
        if stdlib is None:
            try:
                stdlib = frozenset(sys.builtin_module_names)
            except AttributeError:
                stdlib = frozenset()
        missing = imported - stdlib - Sandbox._KNOWN_DOCKER_PACKAGES

        if workspace:
            local_names = set()
            if source_filename:
                local_names.add(os.path.splitext(os.path.basename(source_filename))[0])
            for root in missing:
                if os.path.isfile(os.path.join(workspace, root + ".py")) or os.path.isdir(os.path.join(workspace, root)):
                    local_names.add(root)
            excluded = missing & local_names
            missing = missing - excluded
            if excluded:
                logger.debug(
                    f"Skipping pip install for locally-resolvable imports: {', '.join(sorted(excluded))}",
                    "SANDBOX"
                )

        return missing

    @staticmethod
    def _stage_extra_files(temp_dir: str, extra_files) -> list:
        """Write extra files (conftest.py, repo-relative helpers) into the workspace.

        Returns the staged absolute paths so the caller can extend the
        ``__init__.py`` creation loop. Files escaping the workspace are ignored.
        """
        staged = []
        root = os.path.normpath(temp_dir)
        for entry in extra_files or []:
            if not isinstance(entry, dict):
                continue
            rel = entry.get("path") or entry.get("filename")
            content = entry.get("content")
            if not rel or not content:
                continue
            abs_path = os.path.normpath(os.path.join(temp_dir, rel.replace("/", os.sep)))
            try:
                if os.path.commonpath([root, abs_path]) != root:
                    logger.warning(f"Ignoring test dependency outside workspace: {rel}", "SANDBOX")
                    continue
            except ValueError:
                continue
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            staged.append(abs_path)
        return staged

    def _resolve_test_dependencies(self, temp_dir: str, test_content: str, source_code: str | None, source_filename: str | None) -> dict:
        """Resolve test imports: rebind to the patched module, or skip.

        ``missing`` is first computed without the workspace so module-under-test
        roots still participate in rebinding even when a repo mirror is staged
        (running against a mirror would silently exercise unpatched code).
        Staged files (conftest.py, genuine helpers) resolve their roots during
        the workspace-aware re-computation.

        Returns a dict with ``test_content``, ``rebind_info`` and ``missing``.
        """
        source_code = source_code or ""
        source_filename = source_filename or ""
        missing = self._detect_third_party_imports(
            source_code, test_content, source_filename=source_filename
        )
        rebind_info: dict = {}
        if missing:
            rebound_content, rebind_info = rebind_test_imports(
                test_content, source_code, source_filename, candidate_roots=missing
            )
            if rebind_info.get("rebound"):
                test_content = rebound_content
            missing = self._detect_third_party_imports(
                source_code, test_content, workspace=temp_dir, source_filename=source_filename
            )
        return {
            "test_content": test_content,
            "rebind_info": rebind_info,
            "missing": missing,
        }

    def _write_mock_header(self, file):
        from sandbox.mock_header import build_mock_header
        file.write(build_mock_header())

    def run(
        self,
        code: str,
        mode: str = "secure_validation",
        test_file_path: str | None = None,
        source_filename: str | None = None,
        scan_mode: str | None = None,
        network: str | None = None,
    ):
        container_name = f"sandbox_{uuid.uuid4().hex[:8]}"
        cache_variant = f"{network or ''}|{scan_mode or ''}"

        # Fail closed when Docker or the image is unavailable — never execute
        # untrusted PR code on the host. Retries cover transient daemon restarts.
        ready, reason = self._ready_for_execution("run")
        if not ready:
            if reason == "image":
                logger.warning("Sandbox: image unavailable — refusing to run untrusted code on host", "SANDBOX")
                return {"success": False, "error": "Sandbox unavailable (image not provisioned)", "image_unavailable": True, "mode": "unavailable"}
            logger.error("Sandbox: Docker unavailable — refusing to run untrusted code on host", "SANDBOX")
            return {"success": False, "error": "Sandbox unavailable (Docker required)", "image_unavailable": True, "mode": "unavailable"}

        try:
            validate_code_input(code)

            if contains_unsafe_pattern(code):
                return {"success": False, "error": "Unsafe pattern detected"}

            script_name = source_filename or "script.py"

            test_content = ""
            if test_file_path:
                validate_file_path(test_file_path, allow_absolute=True)
                if os.path.exists(test_file_path):
                    with open(test_file_path, "r", encoding="utf-8", errors="ignore") as tf:
                        test_content = tf.read()

            cached = self._sandbox_cache.get(code, test_content, mode, cache_variant)
            if cached is not None:
                return cached

            with TempDir(prefix="airisk_sandbox_") as temp_dir:
                file_path = safe_repo_path(temp_dir, script_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    self._write_mock_header(f)
                    f.write(code)

                if test_content and test_file_path:
                    safe_name = self._safe_test_path(test_file_path)
                    target_test_path = os.path.join(temp_dir, safe_name)
                    with open(target_test_path, "w", encoding="utf-8") as tf:
                        tf.write(test_content)

                mount_path = temp_dir.replace(os.sep, "/")

                entry_point = ["python", f"/app/{script_name}"]
                cmd = self._build_docker_cmd(container_name, mount_path, entry_point, network=network)
                result = self._do_docker_run(cmd, container_name, mode=mode)
                self._sandbox_cache.set(code, test_content, mode, result, cache_variant)
                return result

        except InputValidationError as e:
            return {"success": False, "error": f"Input validation error: {e}"}
        except Exception as e:
            self._force_kill_container(container_name)
            logger.error(f"Sandbox error: {e}", "SANDBOX")
            log.exception("Unhandled sandbox error")
            return {"success": False, "error": f"Sandbox error: {e}"}

    def run_tests(self, test_file_path: str, source_code: str | None = None, source_filename: str | None = None, extra_files: list | None = None, scan_mode: str | None = None, network: str | None = None) -> dict:
        validate_file_path(test_file_path, allow_absolute=True)
        container_name = f"test_{uuid.uuid4().hex[:8]}"
        cache_variant = f"{network or ''}|{scan_mode or ''}"

        ready, reason = self._ready_for_execution("tests")
        if not ready:
            if reason == "image":
                logger.warning("Sandbox: image unavailable for tests — refusing to run untrusted tests on host", "SANDBOX")
                return {"success": False, "error": "Sandbox unavailable (image not provisioned)", "image_unavailable": True, "mode": "unavailable"}
            logger.error("Sandbox: Docker unavailable for tests — refusing to run untrusted tests on host", "SANDBOX")
            return {"success": False, "error": "Sandbox unavailable (Docker required)", "image_unavailable": True, "mode": "unavailable"}

        try:
            if not os.path.exists(test_file_path):
                return {"success": False, "error": "Test file not found"}

            with open(test_file_path, "r", encoding="utf-8", errors="ignore") as f:
                test_content = f.read()

            validate_code_input(test_content)

            if contains_unsafe_pattern(test_content):
                return {"success": False, "error": "Unsafe pattern detected in test"}

            if not extra_files:
                cached = self._sandbox_cache.get(source_code or "", test_content, "test", cache_variant)
                if cached is not None:
                    return cached

            safe_name = self._safe_test_path(test_file_path)

            with TempDir(prefix="airisk_tests_") as temp_dir:
                if source_code and source_filename:
                    src_path = safe_repo_path(temp_dir, source_filename)
                    with open(src_path, "w", encoding="utf-8") as f:
                        self._write_mock_header(f)
                        f.write(source_code)

                target_path = safe_repo_path(temp_dir, safe_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(test_content)

                init_paths = [target_path]
                if source_code and source_filename:
                    init_paths.append(src_path)
                init_paths.extend(self._stage_extra_files(temp_dir, extra_files))
                for fpath in init_paths:
                    d = os.path.dirname(fpath)
                    while d and d != temp_dir:
                        init = os.path.join(d, "__init__.py")
                        if not os.path.exists(init):
                            Path(init).touch()
                        d = os.path.dirname(d)

                mount_path = temp_dir.replace(os.sep, "/")

                resolution = self._resolve_test_dependencies(temp_dir, test_content, source_code, source_filename)
                test_content = resolution["test_content"]
                rebind_info = resolution["rebind_info"]
                missing = resolution["missing"]
                if rebind_info.get("skip"):
                    return {
                        "success": False,
                        "skipped": True,
                        "mode": "docker",
                        "error": rebind_info.get("reason") or "unresolvable test imports",
                        "rebind": rebind_info,
                    }
                if not rebind_info.get("skip"):
                    with open(target_path, "w", encoding="utf-8") as tf:
                        tf.write(test_content)

                if missing:
                    # Never pip-install attacker-controlled package names at
                    # runtime (this previously forced --network=bridge + a
                    # writable rootfs). Missing deps are reported so pytest
                    # fails on the unresolved import instead.
                    logger.warning(
                        f"Test deps {', '.join(sorted(missing))} are not staged in the image — "
                        f"not installing at runtime; pre-bake these into the Docker image",
                        "SANDBOX"
                    )

                entry_point = ["python", "-m", "pytest", f"/app/{safe_name}", "-v"]
                cmd = self._build_docker_cmd(container_name, mount_path, entry_point, network=network)

                result = self._do_docker_run(cmd, container_name, mode="docker", track_exit_code=True, timeout=config.sandbox.docker.test_timeout_seconds, max_output_bytes=config.sandbox.docker.test_max_output_bytes)
                if rebind_info.get("rebound"):
                    result["rebind"] = rebind_info
                from sandbox.mock_header import MOCKED_ENV_VARS
                result["mocked_env_vars"] = list(MOCKED_ENV_VARS)
                if not extra_files:
                    self._sandbox_cache.set(source_code or "", test_content, "test", result, cache_variant)
                return result

        except InputValidationError as e:
            return {"success": False, "error": f"Input validation error: {e}"}
        except Exception as e:
            self._force_kill_container(container_name)
            logger.error(f"run_tests error: {e}", "SANDBOX")
            log.exception("Unhandled run_tests error")
            return {"success": False, "error": f"run_tests error: {e}"}