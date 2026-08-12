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
from core.utils.validation import safe_filename, validate_code_input, validate_file_path
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
                if isinstance(node.func, ast.Name) and node.func.id == "compile":
                    # compile(source, ...) with mode='exec' or mode='eval'
                    raw_modes = [getattr(kw.value, "value", None) for kw in node.keywords if kw.arg == "mode"]
                    if raw_modes and any(m in ("exec", "eval") for m in raw_modes if m) and not _is_in_pytest_raises(node, parents):
                        return True
            elif isinstance(node, ast.Import):
                if any(_resolve_name(aliases, alias.name) == "ctypes" for alias in node.names):
                    return True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "ctypes":
                    return True
        return False
    except SyntaxError:
        stripped = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        return any(re.search(pattern, stripped) for pattern in BLOCKED_PATTERNS)
    except Exception:
        stripped = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        return any(re.search(pattern, stripped) for pattern in BLOCKED_PATTERNS)


def _win32_capped_run(cmd, env, timeout, mem_bytes, cwd=None):
    """Run a command on Windows under a Job Object that caps committed memory.

    Returns a ``subprocess.CompletedProcess`` on success, or ``None`` if the job
    cannot be created/assigned so callers can transparently fall back to a plain
    subprocess.run with the existing wall-clock timeout. ``resource.setrlimit``
    is a no-op on Windows, so this is the only way to enforce a memory ceiling.
    """
    if mem_bytes <= 0 or sys.platform != "win32":
        return None
    proc = None
    job = None
    kernel32 = None
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100

        class _IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32),
                ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = mem_bytes
        if not kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(info), ctypes.sizeof(info)
        ):
            return None

        proc = subprocess.Popen(
            cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if not kernel32.AssignProcessToJobObject(job, int(proc._handle)):
            return None
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
            raise
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)
    except Exception:
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        return None
    finally:
        if job and kernel32 is not None:
            try:
                kernel32.CloseHandle(job)
            except Exception:
                pass


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

    @staticmethod
    def _build_clean_env() -> dict:
        """Build a minimal environment for local subprocess, stripping secrets."""
        clean = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
            "TMPDIR": os.environ.get("TMPDIR", os.environ.get("TEMP", os.environ.get("TMP", ""))),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if sys.platform == "win32":
            clean["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
            clean["ComSpec"] = os.environ.get("ComSpec", r"C:\Windows\system32\cmd.exe")
        if config.sandbox.local.strip_secrets:
            for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
                clean.pop(k, None)
        return clean

    @staticmethod
    def _set_resource_limits():
        """Apply resource limits to the current process (Linux only, call via preexec_fn)."""
        if sys.platform == "win32":
            return
        lc = config.sandbox.local
        try:
            import resource
            if lc.memory_limit_mb > 0:
                resource.setrlimit(resource.RLIMIT_AS, (lc.memory_limit_mb * 1024 * 1024) * 2)
            if lc.cpu_time_seconds > 0:
                resource.setrlimit(resource.RLIMIT_CPU, (lc.cpu_time_seconds, lc.cpu_time_seconds))
            if lc.max_processes > 0:
                resource.setrlimit(resource.RLIMIT_NPROC, (lc.max_processes, lc.max_processes))
            if lc.max_file_bytes > 0:
                resource.setrlimit(resource.RLIMIT_FSIZE, (lc.max_file_bytes, lc.max_file_bytes))
        except (ImportError, ValueError, OSError):
            pass

    def _preexec_fn(self):
        """Callable for subprocess preexec_fn — applies resource limits if possible."""
        self._set_resource_limits()

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

    def _truncate_output(self, result: dict, max_bytes: int | None = None) -> dict:
        """Truncate stdout/stderr in a result dict to prevent memory exhaustion."""
        if max_bytes is None:
            max_bytes = config.sandbox.docker.max_output_bytes
        for key in ("output", "error"):
            if isinstance(result.get(key), str) and len(result[key]) > max_bytes:
                result[key] = result[key][:max_bytes] + f"\n... (truncated at {max_bytes} bytes)"
        return result

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
                    "falling back to local execution",
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
        dockerfile = config.sandbox.docker.dockerfile
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
            ["docker", "build", "-f", dockerfile, "-t", image, "."],
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

    def _do_docker_run(self, cmd: list, container_name: str, mode: str = "secure_validation", track_exit_code: bool = False, timeout: int | None = None, max_output_bytes: int | None = None) -> dict:
        """Execute a Docker command and handle common timeout/cleanup/truncation."""
        import time as _time
        start = _time.time()
        mode_label = "docker_test" if mode == "docker" else "docker_run"
        dc = config.sandbox.docker
        run_timeout = timeout or dc.timeout_seconds
        # Report the network mode actually baked into the docker command (may
        # differ from the config default when a per-scan/network override or a
        # forced bridge for dependency installs is in effect).
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
            result = subprocess.run(
                cmd, capture_output=True, timeout=run_timeout, text=True,
            )
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
            if max_output_bytes is not None:
                return self._truncate_output(response, max_bytes=max_output_bytes)
            return self._truncate_output(response)
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
        return test_file_path.replace(os.sep, "/")
    
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

    def _run_local_command(self, cmd, env, timeout, cwd=None):
        """Run ``cmd`` under the configured resource limits.

        Linux uses ``preexec_fn`` + ``resource.setrlimit``; Windows enforces a
        committed-memory ceiling via a Job Object (resource limits are a no-op
        there). Either path preserves a hard wall-clock ``timeout``.
        """
        if sys.platform != "win32":
            return subprocess.run(
                cmd, capture_output=True, timeout=timeout, text=True,
                env=env, preexec_fn=self._preexec_fn, cwd=cwd,
            )
        mem_bytes = config.sandbox.local.memory_limit_mb * 1024 * 1024
        capped = _win32_capped_run(cmd, env, timeout, mem_bytes, cwd=cwd)
        if capped is not None:
            return capped
        return subprocess.run(
            cmd, capture_output=True, timeout=timeout, text=True, env=env, cwd=cwd
        )

    def _run_local(self, code: str, mode: str = "secure_validation", test_file_path: str | None = None, source_filename: str | None = None):
        """Run code directly via local Python as fallback when Docker is unavailable."""
        import time as _time
        start = _time.time()
        try:
            validate_code_input(code)

            if contains_unsafe_pattern(code):
                self._track_sandbox_metrics("local_run", False, _time.time() - start)
                return {"success": False, "error": "Unsafe pattern detected"}

            script_name = source_filename or "script.py"
            with TempDir(prefix="airisk_sandbox_") as temp_dir:
                file_path = os.path.join(temp_dir, script_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    self._write_mock_header(f, source_filename=script_name)
                    f.write(code)

                if test_file_path:
                    validate_file_path(test_file_path, allow_absolute=True)
                    if os.path.exists(test_file_path):
                        safe_name = self._safe_test_path(test_file_path)
                        target_path = os.path.join(temp_dir, safe_name)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(test_file_path, "r", encoding="utf-8", errors="ignore") as tf:
                            test_content = tf.read()
                        with open(target_path, "w", encoding="utf-8") as tf:
                            tf.write(test_content)

                cmd = [sys.executable, file_path]

                try:
                    result = self._run_local_command(
                        cmd, env=self._build_clean_env(),
                        timeout=config.sandbox.local.timeout_seconds,
                    )
                    success = result.returncode == 0 and "Traceback" not in result.stderr
                    note = None
                    if not success and self._cli_arguments_only(result):
                        success = True
                        note = "cli_arguments_required"
                    resp = self._truncate_output({
                        "success": success,
                        "output": result.stdout,
                        "error": result.stderr,
                        "mode": f"{mode}_local",
                        **({"note": note} if note else {}),
                    }, max_bytes=config.sandbox.local.max_output_bytes)
                    self._track_sandbox_metrics("local_run", success, _time.time() - start)
                    return resp
                except subprocess.TimeoutExpired:
                    self._track_sandbox_metrics("local_run", False, _time.time() - start)
                    return {"success": False, "error": "Sandbox timeout (local)"}

        except InputValidationError as e:
            self._track_sandbox_metrics("local_run", False, _time.time() - start)
            return {"success": False, "error": f"Input validation error: {e}"}
        except Exception as e:
            logger.error(f"Local sandbox error: {e}", "SANDBOX")
            self._track_sandbox_metrics("local_run", False, _time.time() - start)
            return {"success": False, "error": f"Local sandbox error: {e}"}

    def _is_pytest_available(self) -> bool:
        """Check if pytest is available in the current Python environment."""
        try:
            import importlib.util
            return importlib.util.find_spec("pytest") is not None
        except ImportError:
            return False

    @staticmethod
    def _count_test_functions(test_content: str) -> int:
        """Count the number of test_* functions in a test file via AST."""
        try:
            tree = ast.parse(test_content)
            return sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
        except SyntaxError:
            return 0

    def _run_local_tests(self, test_file_path: str, source_code: str | None = None, source_filename: str | None = None, extra_files: list | None = None) -> dict:
        """Run pytest locally as fallback when Docker is unavailable."""
        import time as _time
        start = _time.time()
        lc = config.sandbox.local
        try:
            validate_file_path(test_file_path, allow_absolute=True)
            if not os.path.exists(test_file_path):
                self._track_sandbox_metrics("local_test", False, _time.time() - start)
                return {"success": False, "error": "Test file not found"}

            with open(test_file_path, "r", encoding="utf-8", errors="ignore") as f:
                test_content = f.read()

            validate_code_input(test_content)

            if contains_unsafe_pattern(test_content):
                self._track_sandbox_metrics("local_test", False, _time.time() - start)
                return {"success": False, "error": "Unsafe pattern detected in test"}

            if not self._is_pytest_available():
                logger.warning("pytest is not available in local environment — tests will be skipped", "SANDBOX")
                self._track_sandbox_metrics("local_test", False, _time.time() - start)
                return {"success": False, "skipped": True, "error": "pytest not available (local fallback)", "mode": "local"}

            safe_name = self._safe_test_path(test_file_path)

            with TempDir(prefix="airisk_tests_") as temp_dir:
                if source_code and source_filename:
                    src_path = os.path.join(temp_dir, source_filename)
                    with open(src_path, "w", encoding="utf-8") as f:
                        self._write_mock_header(f, source_filename=source_filename)
                        f.write(source_code)

                target_path = os.path.join(temp_dir, safe_name)
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

                resolution = self._resolve_test_dependencies(temp_dir, test_content, source_code, source_filename)
                test_content = resolution["test_content"]
                rebind_info = resolution["rebind_info"]
                missing = resolution["missing"]
                if rebind_info.get("skip"):
                    self._track_sandbox_metrics("local_test", False, _time.time() - start)
                    return {
                        "success": False,
                        "skipped": True,
                        "mode": "local",
                        "error": rebind_info.get("reason") or "unresolvable test imports",
                        "rebind": rebind_info,
                    }
                if not rebind_info.get("skip"):
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(test_content)

                if missing:
                    preexec = self._preexec_fn if sys.platform != "win32" else None
                    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "--user"] + list(missing)
                    try:
                        pip_result = subprocess.run(
                            pip_cmd, capture_output=True, timeout=30, text=True,
                            env=self._build_clean_env(), preexec_fn=preexec,
                        )
                        if pip_result.returncode != 0:
                            logger.warning(
                                f"Dependency install failed for {', '.join(sorted(missing))} — continuing to pytest: {pip_result.stderr[:500]}",
                                "SANDBOX"
                            )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            f"Dependency install timed out for {', '.join(sorted(missing))} — continuing to pytest",
                            "SANDBOX"
                        )

                cmd = [sys.executable, "-m", "pytest", target_path, "-v"]
                try:
                    result = self._run_local_command(
                        cmd, env=self._build_clean_env(),
                        timeout=lc.test_timeout_seconds,
                        cwd=temp_dir,
                    )
                    success = result.returncode == 0

                    test_count = self._count_test_functions(test_content)
                    if test_count > 0 and success:
                        combined_output = (result.stdout + result.stderr).lower()
                        has_output = any(
                            indicator in combined_output
                            for indicator in ["passed", "failed", "error", "test_"]
                        )
                        if not has_output:
                            logger.warning(
                                f"pytest returned exit code 0 but no test output detected "
                                f"({test_count} test functions found in file) — tests may not have actually executed",
                                "SANDBOX"
                            )

                    resp = self._truncate_output({
                        "success": success,
                        "output": result.stdout,
                        "error": result.stderr,
                        "exit_code": result.returncode,
                        "mode": "local",
                    }, max_bytes=lc.test_max_output_bytes)
                    if rebind_info.get("rebound"):
                        resp["rebind"] = rebind_info
                    from sandbox.mock_header import MOCKED_ENV_VARS
                    resp["mocked_env_vars"] = list(MOCKED_ENV_VARS)
                    self._track_sandbox_metrics("local_test", success, _time.time() - start)
                    return resp
                except subprocess.TimeoutExpired:
                    self._track_sandbox_metrics("local_test", False, _time.time() - start)
                    return {"success": False, "error": "Test timeout (local)"}

        except InputValidationError as e:
            self._track_sandbox_metrics("local_test", False, _time.time() - start)
            return {"success": False, "error": f"Input validation error: {e}"}
        except Exception as e:
            logger.error(f"Local run_tests error: {e}", "SANDBOX")
            self._track_sandbox_metrics("local_test", False, _time.time() - start)
            return {"success": False, "error": f"Local run_tests error: {e}"}

    def _write_mock_header(self, file, source_filename: str = "script.py"):
        from sandbox.mock_header import build_mock_header
        file.write(build_mock_header(source_filename))

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

        # Fall back to local execution if Docker is not available
        if not self._is_docker_available():
            logger.info("Sandbox: Docker unavailable, falling back to local execution", "SANDBOX")
            return self._run_local(code, mode, test_file_path, source_filename)

        # Fall back to local execution if the sandbox image cannot be provisioned
        if not self._docker_image_ready():
            logger.warning("Sandbox: image unavailable, falling back to local execution", "SANDBOX")
            result = self._run_local(code, mode, test_file_path, source_filename)
            result["image_unavailable"] = True
            return result

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
                file_path = os.path.join(temp_dir, script_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    self._write_mock_header(f, source_filename=script_name)
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

        if not self._is_docker_available():
            logger.info("Sandbox: Docker unavailable for tests, falling back to local", "SANDBOX")
            return self._run_local_tests(test_file_path, source_code, source_filename, extra_files)

        if not self._docker_image_ready():
            logger.warning("Sandbox: image unavailable for tests, falling back to local", "SANDBOX")
            result = self._run_local_tests(test_file_path, source_code, source_filename, extra_files)
            result["image_unavailable"] = True
            return result

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
                    src_path = os.path.join(temp_dir, source_filename)
                    with open(src_path, "w", encoding="utf-8") as f:
                        self._write_mock_header(f, source_filename=source_filename)
                        f.write(source_code)

                target_path = os.path.join(temp_dir, safe_name)
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
                    pip_and_test = (
                        "import subprocess, sys; "
                        "r = subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '--user'] + sys.argv[1:], capture_output=True, text=True); "
                        "print(r.stderr, flush=True) if r.returncode != 0 else None; "
                        f"sys.exit(subprocess.call([sys.executable, '-m', 'pytest', '/app/{safe_name}', '-v']))"
                    )
                    entry_point = ["python", "-c", pip_and_test] + sorted(missing)
                    # Dependency installs need outbound access, so they always
                    # force bridge regardless of the user's network setting.
                    cmd = self._build_docker_cmd(container_name, mount_path, entry_point, network="bridge", read_only=False)
                    logger.warning(
                        f"Test deps {', '.join(sorted(missing))} are not staged in the image and network is "
                        f"disabled — pre-bake these into the Docker image instead of pip-installing at runtime",
                        "SANDBOX"
                    )
                else:
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