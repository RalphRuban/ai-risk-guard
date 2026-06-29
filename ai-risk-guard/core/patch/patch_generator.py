"""
core/patch/patch_generator.py
Generates human-readable safe patch snippets shown in the PR report.
These are illustrative code examples, not applied to the file directly
(that is handled by ast_patch_engine.py).
"""

from core.validator.sandbox import Sandbox

_sandbox = Sandbox()


def generate_patch(vuln: dict) -> dict:
    """
    Return a safe, compilable snippet for the given vulnerability type.
    Also validates the snippet compiles successfully via the sandbox.
    """
    vuln_type = vuln.get("type", "")

    if vuln_type == "COMMAND_INJECTION":
        patch = (
            "import subprocess\n"
            "import shlex\n\n"
            "# Safe command execution — no shell interpolation\n"
            "subprocess.run(shlex.split(command), shell=False, check=True)"
        )

    elif vuln_type == "CODE_INJECTION":
        patch = (
            "import ast\n\n"
            "# Safe evaluation — only handles literals (str, int, list, dict…)\n"
            "result = ast.literal_eval(data)"
        )

    elif vuln_type == "HARDCODED_SECRET":
        patch = (
            "import os\n\n"
            "# Load from environment — never hard-code credentials\n"
            "SECRET = os.getenv('SECRET_KEY')"
        )

    elif vuln_type == "INSECURE_DESERIALIZATION":
        patch = (
            "import json\n\n"
            "# Use JSON instead of pickle for untrusted data\n"
            "result = json.loads(data)"
        )

    else:
        patch = "# No automated patch available — manual review required."

    validation = _sandbox.run(patch, mode="compile")

    return {
        "patch":      patch,
        "validation": validation,
    }