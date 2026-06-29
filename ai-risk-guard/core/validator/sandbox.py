"""
Hardened Docker sandbox validator.
"""

import subprocess
import tempfile
import uuid
import os
import re

from utils.logger import logger


DOCKER_IMAGE = "ai-risk-guard"


BLOCKED_PATTERNS = [

    r"os\.system\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"pickle\.loads\s*\(",
    r"subprocess\.run\s*\(.*shell\s*=\s*True",
]


def contains_unsafe_pattern(code: str):

    return any(
        re.search(pattern, code)
        for pattern in BLOCKED_PATTERNS
    )


class Sandbox:

    def run(
        self,
        code,
        mode="secure_validation",
        test_file_path=None
    ):

        try:

            if contains_unsafe_pattern(code):

                return {
                    "success": False,
                    "error": "Unsafe pattern detected",
                }

            container_name = (
                f"sandbox_{uuid.uuid4().hex[:8]}"
            )

            with tempfile.TemporaryDirectory() as temp_dir:

                file_path = os.path.join(
                    temp_dir,
                    "script.py"
                )

                with open(
                    file_path,
                    "w",
                    encoding="utf-8"
                ) as file:
                    # Prepend stateful mock for interactive and slow functions
                    mock_header = (
                        "import builtins, sys, shlex, time\n"
                        "class MockInput:\n"
                        "    def __init__(self): self.count = 0\n"
                        "    def __call__(self, _=''):\n"
                        "        self.count += 1\n"
                        "        if self.count == 1: return 'echo hello' # For subprocess\n"
                        "        if self.count == 2: return '[1, 2, 3]'   # For literal_eval\n"
                        "        return '123'\n"
                        "builtins.input = MockInput()\n"
                        "def mock_sleep(seconds): pass # Speed up validation\n"
                        "time.sleep = mock_sleep\n"
                        "sys.argv = ['script.py']\n"
                    )
                    file.write(mock_header + code)

                # --- NEW: Test File Integration ---
                test_in_container = None
                if test_file_path and os.path.exists(test_file_path):
                    test_in_container = os.path.basename(test_file_path)
                    target_test_path = os.path.join(temp_dir, test_in_container)
                    with open(test_file_path, "r", encoding="utf-8", errors="ignore") as tf:
                        test_content = tf.read()
                    with open(target_test_path, "w", encoding="utf-8") as tf:
                        tf.write(test_content)

                mount_path = temp_dir.replace("\\", "/")

                # Base command
                cmd = [
                    "docker", "run", "--rm",
                    "--name", container_name,
                    "--memory=128m",
                    "--cpus=0.5",
                    "--pids-limit=32",
                    "--network=none",
                    "--read-only",
                    "--cap-drop=ALL",
                    "-v", f"{mount_path}:/app:ro",
                    DOCKER_IMAGE,
                ]

                # Decide what to run
                if test_in_container:
                    # Run the user's tests
                    cmd.extend(["python", "-m", "pytest", f"/app/{test_in_container}"])
                else:
                    # Just run the script to check for crashes
                    cmd.extend(["python", "/app/script.py"])

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=10, # Increased for pytest
                        text=True,
                    )

                    success = (
                        result.returncode == 0
                        and
                        "Traceback" not in result.stderr
                    )

                    return {
                        "success": success,
                        "output": result.stdout,
                        "error": result.stderr,
                        "mode": mode,
                    }
                
                except subprocess.TimeoutExpired:
                    # Explicit Cleanup (Fix B): Kill the container if it's still hanging
                    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
                    return {
                        "success": False,
                        "error": "Sandbox timeout",
                    }

        except Exception as e:

            logger.error(
                f"Sandbox error: {e}",
                "SANDBOX"
            )

            return {
                "success": False,
                "error": str(e),
            }