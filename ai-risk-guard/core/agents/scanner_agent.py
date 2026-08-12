"""
Scanner Agent.
Responsible for discovering vulnerabilities in source code.
Supports incremental PR analysis: only scans modified functions.
"""

import ast
import hashlib
import logging
import os
from typing import Any

from core.agents.base_agent import BaseAgent
from core.cache.scan_cache import ScanCache
from core.exceptions import InputValidationError, ScanError
from core.scanner.diff_engine import DiffAwareScanner
from core.scanner.vulnerability_scanner import VulnerabilityScanner
from core.utils.validation import validate_diff_data, validate_file_path

log = logging.getLogger("ai_risk_guard.scanner_agent")

class ScannerAgent(BaseAgent):
    """
    Agent specialized in code analysis and vulnerability detection.
    Now discovers associated unit tests for functional verification.
    Supports incremental per-function scanning for PR diffs.
    """
    
    def __init__(self):
        super().__init__("Scanner")
        self.scanner = VulnerabilityScanner()
        self.scan_cache = ScanCache()
        self.diff_engine = DiffAwareScanner()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        file_path = context.get("file_path")
        repo_root = context.get("repo_root")
        diff_data = context.get("diff_data")
        
        if not file_path:
            self.log("No file_path provided, skipping scan", "warning")
            return context
        
        try:
            file_path = validate_file_path(file_path, allow_absolute=True)
            diff_data = validate_diff_data(diff_data)
        except InputValidationError as e:
            self.log(f"Input validation failed: {e}", "error")
            return context
        
        self.log(f"Scanning file for vulnerabilities: {file_path}")
        
        try:
            commit_hash = ""
            if diff_data:
                commit_hash = hashlib.sha256(
                    str(diff_data).encode()
                ).hexdigest()[:12]
            
            # Parse diff to get changed lines map
            diff_map = None
            if isinstance(diff_data, str):
                default_file = os.path.basename(file_path)
                if repo_root:
                    try:
                        rel = os.path.relpath(file_path, repo_root).replace("\\", "/")
                        if not rel.startswith("..") and not os.path.isabs(rel):
                            default_file = rel
                    except ValueError:
                        pass
                diff_map = self.diff_engine.parse_diff(
                    diff_data, default_file=default_file
                )
            elif diff_data is not None:
                diff_map = diff_data
            
            # Compute modified functions for incremental scanning
            modified_functions = None
            if diff_map:
                original_code = context.get("original_code", "")
                if original_code:
                    modified_functions = self.diff_engine.get_modified_functions(
                        file_path, original_code, diff_map
                    )
            
            if modified_functions:
                self.log(f"Incremental scan: {len(modified_functions)} modified functions")
                cached_vulns = self.scan_cache.get_functions(
                    file_path, modified_functions, commit_hash
                )
                
                if cached_vulns:
                    self.log(f"Using cached results for unmodified functions: {len(cached_vulns)} findings")
                    context["vulnerabilities"] = cached_vulns
                    return context
                
                vulnerabilities = self.scanner.scan_file(
                    file_path=file_path,
                    diff_data=diff_map,
                    scope_filter=modified_functions
                )
                
                for func_name in modified_functions:
                    func_vulns = [
                        v for v in vulnerabilities
                        if self._vuln_in_function(v, func_name, original_code)
                    ]
                    self.scan_cache.set_function(file_path, func_name, commit_hash, func_vulns)
            else:
                cached = self.scan_cache.get(file_path, commit_hash)
                if cached is not None:
                    self.log(f"Scan cache hit for {file_path}")
                    context["vulnerabilities"] = cached
                    return context
                
                vulnerabilities = self.scanner.scan_file(
                    file_path=file_path,
                    diff_data=diff_map
                )
                
                self.scan_cache.set(file_path, commit_hash, vulnerabilities)
            
            # Test Discovery
            test_file = self._discover_test_file(file_path, repo_root or "")
            if test_file:
                self.log(f"Discovered associated test file: {os.path.basename(test_file)}")
                context["associated_test_file"] = test_file
            
            # Update context with findings
            context["vulnerabilities"] = vulnerabilities
            self.log(f"Found {len(vulnerabilities)} potential vulnerabilities")

        except ScanError as e:
            self.log(f"Scan error: {e}", "error")
            context["scan_error"] = f"Scan error: {e}"
        except Exception as e:
            self.log(f"Unexpected scanner error: {e}", "error")
            log.exception("Unexpected error in scanner_agent.execute")
            context["scan_error"] = f"Unexpected scanner error: {e}"

        return context

    def _vuln_in_function(self, vulnerability: dict, function_name: str, code: str) -> bool:
        """Check if a vulnerability line falls within a given function's line range."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                    end_line = getattr(node, "end_lineno", node.lineno)
                    vuln_line = vulnerability.get("line", 0)
                    return node.lineno <= vuln_line <= end_line
        except SyntaxError:
            pass
        return False

    def _discover_test_file(self, target_file: str, repo_root: str) -> str | None:
        """
        Search for a related test file (e.g., test_[name].py or [name]_test.py).
        Searches same directory, tests/ subdirectory, and mirrored structure.
        Uses the same candidate logic as test_file_fetcher for consistency.
        """
        if not repo_root:
            return None

        from core.scanner.test_file_fetcher import predict_test_candidates

        rel_path = os.path.relpath(target_file, repo_root).replace("\\", "/") if os.path.isabs(target_file) else target_file.replace("\\", "/")
        candidates = predict_test_candidates(rel_path)

        for candidate in candidates:
            candidate_path = os.path.join(repo_root, candidate.replace("/", os.sep))
            if os.path.isfile(candidate_path):
                return candidate_path
        return None
