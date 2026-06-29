"""
Scanner Agent.
Responsible for discovering vulnerabilities in source code.
"""

import os
from typing import Dict, Any, List, Optional
from core.agents.base_agent import BaseAgent
from core.scanner.vulnerability_scanner import VulnerabilityScanner

class ScannerAgent(BaseAgent):
    """
    Agent specialized in code analysis and vulnerability detection.
    Now discovers associated unit tests for functional verification.
    """
    
    def __init__(self):
        super().__init__("Scanner")
        self.scanner = VulnerabilityScanner()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        file_path = context.get("file_path")
        repo_root = context.get("repo_root")
        diff_data = context.get("diff_data")
        
        self.log(f"Scanning file for vulnerabilities: {file_path}")
        
        vulnerabilities = self.scanner.scan_file(
            file_path=file_path,
            diff_data=diff_data
        )
        
        # --- NEW: Test Discovery (Week 6 Expansion) ---
        test_file = self._discover_test_file(file_path, repo_root)
        if test_file:
            self.log(f"Discovered associated test file: {os.path.basename(test_file)}")
            context["associated_test_file"] = test_file
        
        # Update context with findings
        context["vulnerabilities"] = vulnerabilities
        self.log(f"Found {len(vulnerabilities)} potential vulnerabilities")
        
        return context

    def _discover_test_file(self, target_file: str, repo_root: str) -> Optional[str]:
        """
        Search for a related test file (e.g., test_[name].py or [name]_test.py).
        """
        if not repo_root:
            return None
            
        base_name = os.path.basename(target_file)
        name_no_ext = os.path.splitext(base_name)[0]
        
        potential_names = [
            f"test_{base_name}",
            f"{name_no_ext}_test.py"
        ]
        
        for root, _, files in os.walk(repo_root):
            # Focus on 'tests' directories or root
            for p_name in potential_names:
                if p_name in files:
                    return os.path.join(root, p_name)
        return None
