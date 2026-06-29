"""
Patch Agent.
Responsible for generating and applying secure code patches.
"""

from typing import Dict, Any, List
from core.agents.base_agent import BaseAgent
from core.patch.patch_orchestrator import apply_patches_safely
from core.patch.fixers import apply_patch_to_content
from core.patch.llm_patcher import LLMPatcher

class PatchAgent(BaseAgent):
    """
    Agent specialized in code transformation and patching.
    Now supports both deterministic AST patching and LLM-driven multi-candidate generation.
    """
    
    def __init__(self):
        super().__init__("Patch")
        self.llm_patcher = LLMPatcher()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        vulnerabilities = context.get("vulnerabilities", [])
        original_code = context.get("original_code")
        
        if not vulnerabilities:
            self.log("No vulnerabilities to patch")
            return context

        self.log(f"Attempting remediation for {len(vulnerabilities)} vulnerabilities")

        # 1. Deterministic AST Patch (Baseline)
        ast_patch_result = apply_patches_safely(
            code=original_code,
            vulnerabilities=vulnerabilities,
            patch_function=apply_patch_to_content
        )
        
        # 2. LLM Multi-Candidate Generation (Advanced)
        # We store these as a list of "Patch Candidate" dictionaries
        candidates = []
        
        # Add the AST baseline as the first candidate
        candidates.append({
            "id": "baseline_ast",
            "code": ast_patch_result["final_code"],
            "diff": ast_patch_result["combined_diff"],
            "source": "deterministic_ast"
        })

        if self.llm_patcher.enabled:
            self.log("Generating additional candidates via LLM...")
            llm_variants = self.llm_patcher.generate_candidates(original_code, vulnerabilities)
            
            for i, variant_code in enumerate(llm_variants):
                candidates.append({
                    "id": f"llm_variant_{i+1}",
                    "code": variant_code,
                    "source": "gemini_1.5_flash"
                })

        context["patch_candidates"] = candidates
        self.log(f"Prepared {len(candidates)} patch candidates for validation")
        
        return context
