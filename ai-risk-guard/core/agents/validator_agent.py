"""
Validator Agent.
Responsible for verifying the integrity and security of applied patches.
"""

import os
from typing import Dict, Any
from core.agents.base_agent import BaseAgent
from core.validator.patch_validator import PatchValidator
from core.validator.security_rescan import SecurityRescanner
from core.validator.sandbox import Sandbox
from core.policy.policy_engine import PolicyEngine

class ValidatorAgent(BaseAgent):
    """
    Agent specialized in patch verification and security re-scanning.
    Now includes Policy Enforcement and Test-Aware validation.
    """
    
    def __init__(self):
        super().__init__("Validator")
        self.validator = PatchValidator()
        self.rescanner = SecurityRescanner()
        self.sandbox = Sandbox()
        self.policy_engine = PolicyEngine()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candidates = context.get("patch_candidates", [])
        test_file = context.get("associated_test_file")
        
        if not candidates:
            self.log("No patch candidates to validate")
            return context

        self.log(f"Starting multi-stage validation for {len(candidates)} candidates")
        if test_file:
            self.log(f"Running functional verification using: {os.path.basename(test_file)}")
        
        for candidate in candidates:
            patched_code = candidate.get("code")
            self.log(f"Validating candidate: {candidate['id']} ({candidate['source']})")
            
            # Stage 1: Syntax & Semantic Checks
            syntax_res = self.validator.validate_all(patched_code)
            
            # Stage 2: Sandbox Execution (Test-Aware)
            sandbox_res = self.sandbox.run(patched_code, test_file_path=test_file)
            
            # Stage 3: Security Re-scan
            rescan_res = self.rescanner.rescan_code(patched_code)
            
            # Stage 4: Policy Enforcement
            policy_res = self.policy_engine.check_compliance(patched_code)
            
            # Compute a validation score (0.0 to 1.0)
            score = 0.0
            if syntax_res.get("success") is True: 
                score += 0.25
            if sandbox_res.get("success") is True: 
                score += 0.35
            if rescan_res.get("success") is True: 
                score += 0.20
            if policy_res.get("success") is True: 
                score += 0.20
            
            # Round score to avoid float precision issues
            score = round(score, 2)
            
            # Attach validation data to the candidate
            candidate["validation_score"] = score
            candidate["validation_details"] = {
                "syntax": syntax_res,
                "sandbox": sandbox_res,
                "rescan": rescan_res,
                "policy": policy_res
            }
            
            if score >= 1.0:
                self.log(f"Candidate {candidate['id']} PASSED all validation stages")
            else:
                self.log(f"Candidate {candidate['id']} FAILED some validation (Score: {score})", "warning")
                # Add detailed failure logs
                if not syntax_res.get("success"):
                    results_list = syntax_res.get('results', [])
                    last_msg = results_list[-1].get('message') if results_list else "Unknown error"
                    self.log(f"  - Syntax/Pattern failure: {syntax_res.get('stage')} - {last_msg}", "debug")
                if not sandbox_res.get("success"):
                    self.log(f"  - Sandbox failure: {sandbox_res.get('error')}", "debug")
                if not rescan_res.get("success"):
                    self.log(f"  - Security Re-scan failure: {len(rescan_res.get('remaining_vulnerabilities', []))} vulns left", "debug")
                if not policy_res.get("success"):
                    self.log(f"  - Policy Violations: {policy_res.get('violations')}", "debug")
            
        return context
