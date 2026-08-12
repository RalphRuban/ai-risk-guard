"""
Security Policy Engine.
Enforces organizational security standards by validating code against the central config.
"""

import ast
import fnmatch
from typing import Any

from core.config import config
from utils.logger import logger


class PolicyEngine:
    """
    Engine responsible for checking code against organizational security policies.
    Loads rules from config/policy/default.yaml via the central config registry.
    """

    def __init__(self):
        self.policy = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        """Load policy rules from the central config registry."""
        try:
            pc = config.policy
            return {
                "forbidden_modules": pc.forbidden_modules,
                "forbidden_functions": pc.forbidden_functions,
                "mandatory_sanitizers": pc.mandatory_sanitizers,
                "sensitive_paths": pc.sensitive_paths,
                "restricted_function_args": [
                    {"function": r.function, "arg_index": r.arg_index, "forbidden_values": r.forbidden_values, "violation_msg": r.violation_msg}
                    for r in pc.restricted_function_args
                ],
                "mandatory_call_wrappers": [
                    {"target": r.target, "wrappers": r.wrappers, "arg_index": r.arg_index, "violation_msg": r.violation_msg}
                    for r in pc.mandatory_call_wrappers
                ],
                "forbidden_assignments": [
                    {"pattern": r.pattern, "violation_msg": r.violation_msg}
                    for r in pc.forbidden_assignments
                ],
                "mandatory_query_params": [
                    {"function": r.function, "param_arg_index": r.param_arg_index, "violation_msg": r.violation_msg}
                    for r in pc.mandatory_query_params
                ],
                "policy_name": pc.policy_name,
                "version": pc.version,
                "description": pc.description,
            }
        except Exception as e:
            logger.error(f"Failed to load policy from config: {e}", "POLICY")
            return {}

    def check_compliance(self, code: str) -> dict[str, Any]:
        """
        Check if the provided code complies with the loaded policy.

        Returns a dictionary with:
            success: bool (True if compliant)
            violations: List[str]
        """
        violations = set()

        try:
            tree = ast.parse(code)

            # 1. Check Forbidden Modules
            forbidden_modules = self.policy.get("forbidden_modules", [])
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name in forbidden_modules:
                            violations.add(f"Forbidden module import: {name.name}")
                elif isinstance(node, ast.ImportFrom) and node.module in forbidden_modules:
                    violations.add(f"Forbidden module import: {node.module}")

            # 2. Check Forbidden Functions
            forbidden_funcs = self.policy.get("forbidden_functions", [])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    if func_name in forbidden_funcs:
                        violations.add(f"Forbidden function call: {func_name}")

            # 3. Check Mandatory Sanitizers (e.g., shell=False)
            sanitizers = self.policy.get("mandatory_sanitizers", {})
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    if func_name in sanitizers:
                        required_args = sanitizers[func_name]
                        for req in required_args:
                            if not self._check_keyword_arg(node, req):
                                violations.add(f"Missing mandatory sanitizer '{req}' for {func_name}")

            # 4. Check Restricted Function Arguments (e.g., hashlib.new("md5"))
            restricted_args = self.policy.get("restricted_function_args", [])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    for rule in restricted_args:
                        if func_name == rule["function"] and len(node.args) > rule["arg_index"]:
                            arg = node.args[rule["arg_index"]]
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in rule["forbidden_values"]:
                                msg = rule["violation_msg"] or f"Forbidden argument value for {rule['function']}"
                                violations.add(msg.format(value=arg.value))

            # 5. Check Mandatory Call Wrappers (e.g., requests.get wrapped with validate_url_ssrf)
            call_wrappers = self.policy.get("mandatory_call_wrappers", [])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    for rule in call_wrappers:
                        if func_name == rule["target"] and len(node.args) > rule["arg_index"]:
                            arg = node.args[rule["arg_index"]]
                            if not (isinstance(arg, ast.Call) and self._get_func_name(arg.func) in rule["wrappers"]):
                                msg = rule["violation_msg"] or f"Argument must be wrapped with one of {rule['wrappers']}"
                                violations.add(msg)

            # 6. Check Forbidden Assignments (e.g., password = "hardcoded")
            forbidden_assigns = self.policy.get("forbidden_assignments", [])
            if forbidden_assigns:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                for rule in forbidden_assigns:
                                    if fnmatch.fnmatch(target.id.lower(), rule["pattern"].lower()) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                        msg = rule["violation_msg"] or f"Hardcoded value assigned to '{target.id}'"
                                        violations.add(msg)

            # 7. Check Mandatory Query Params (e.g., cursor.execute with f-string)
            query_params = self.policy.get("mandatory_query_params", [])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    for rule in query_params:
                        if (func_name == rule["function"] or func_name.endswith(f".{rule['function']}")) and len(node.args) > rule["param_arg_index"]:
                            param = node.args[rule["param_arg_index"]]
                            if isinstance(param, ast.JoinedStr):
                                msg = rule["violation_msg"] or f"f-string detected in {rule['function']}"
                                violations.add(msg)
                            elif isinstance(param, ast.BinOp) and isinstance(param.op, ast.Mod):
                                msg = rule["violation_msg"] or f"% formatting detected in {rule['function']}"
                                violations.add(msg)
                            elif isinstance(param, ast.Call):
                                param_func = self._get_func_name(param.func)
                                if param_func.endswith(".format") or param_func == "format":
                                    msg = rule["violation_msg"] or f".format() detected in {rule['function']}"
                                    violations.add(msg)

            return {
                "success": len(violations) == 0,
                "violations": sorted(violations)
            }

        except Exception as e:
            logger.error(f"Policy check failed: {e}", "POLICY")
            return {"success": False, "violations": ["Policy check failed — internal error"]}

    def _get_func_name(self, node: ast.AST) -> str:
        """Helper to extract function name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return ""

    def _check_keyword_arg(self, node: ast.Call, requirement: str) -> bool:
        """Helper to check if a keyword argument exists (e.g., shell=False)."""
        # Split 'shell=False' into key and value
        try:
            target_key, target_val = requirement.split('=')
            for keyword in node.keywords:
                if keyword.arg == target_key:
                    # Very simple value check (can be improved)
                    val_str = ast.unparse(keyword.value).strip()
                    if val_str == target_val:
                        return True
            return False
        except Exception:
            return False

    def is_path_sensitive(self, file_path: str) -> bool:
        """Check if a file path is marked as sensitive in the policy."""
        sensitive_paths = self.policy.get("sensitive_paths", [])
        return any(path in file_path for path in sensitive_paths)

    def enforce_sanitizers(self, code: str) -> str:
        """
        Enforce mandatory sanitizers by injecting missing keyword arguments.

        Walks the AST, finds all calls listed in mandatory_sanitizers, and
        injects any required keyword arguments that are missing.  For example,
        ``subprocess.run(...)`` without ``shell=False`` will get
        ``shell=False`` added to its keyword list.

        A keyword that is already present with a *conflicting* value (e.g.
        ``shell=True``) is left untouched — silently flipping it to
        ``shell=False`` without splitting the command would mask the original
        vulnerability from the security re-scan.

        Args:
            code: Source code string to fix up.

        Returns:
            Modified source code with missing sanitizers injected, or the
            original *code* unchanged if nothing needed fixing or an error
            occurred during parsing.
        """
        try:
            tree = ast.parse(code)
            modified = False
            sanitizers = self.policy.get("mandatory_sanitizers", {})

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_func_name(node.func)
                    if func_name in sanitizers:
                        required_args = sanitizers[func_name]
                        for req in required_args:
                            target_key, target_val = req.split("=", 1)
                            existing = next((kw for kw in node.keywords if kw.arg == target_key), None)
                            if existing is None:
                                val_node = ast.parse(target_val).body[0].value
                                node.keywords.append(
                                    ast.keyword(arg=target_key, value=val_node)
                                )
                                modified = True
                            # else: keyword present — do not overwrite conflicting values

            if modified:
                ast.fix_missing_locations(tree)
                return ast.unparse(tree)
            return code
        except Exception:
            return code
