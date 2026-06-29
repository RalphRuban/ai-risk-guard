"""
Security Policy Engine.
Enforces organizational security standards by validating code against a policy.json file.
"""

import json
import os
import ast
import re
from typing import Dict, Any, List, Optional
from utils.logger import logger

class PolicyEngine:
    """
    Engine responsible for checking code against organizational security policies.
    """

    def __init__(self, policy_path: str = "core/policy/policy.json"):
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        """Load and parse the policy.json file."""
        try:
            if not os.path.exists(self.policy_path):
                logger.warning(f"Policy file not found at {self.policy_path}. Using empty policy.", "POLICY")
                return {}
            
            with open(self.policy_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load policy: {e}", "POLICY")
            return {}

    def check_compliance(self, code: str) -> Dict[str, Any]:
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
                elif isinstance(node, ast.ImportFrom):
                    if node.module in forbidden_modules:
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

            return {
                "success": len(violations) == 0,
                "violations": sorted(list(violations))
            }

        except Exception as e:
            logger.error(f"Policy check failed: {e}", "POLICY")
            return {"success": False, "violations": [f"Static analysis error during policy check: {str(e)}"]}

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
