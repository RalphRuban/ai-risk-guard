"""
Patch Agent.
Responsible for generating and applying secure code patches.
"""

from typing import Any

from core.agents.base_agent import BaseAgent
from core.patch.fixers import apply_patch_to_content
from core.patch.llm_patcher import LLMPatcher
from core.patch.patch_orchestrator import apply_patches_safely


class PatchAgent(BaseAgent):
    """
    Agent specialized in code transformation and patching.
    Now supports both deterministic AST patching and LLM-driven multi-candidate generation.
    """
    
    def __init__(self):
        super().__init__("Patch")
        self.llm_patcher = LLMPatcher()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        vulnerabilities = context.get("vulnerabilities", [])
        original_code = context.get("original_code")
        
        if not vulnerabilities:
            self.log("No vulnerabilities to patch")
            return context

        if original_code is None:
            self.log("No original code to patch")
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
            llm_result = self.llm_patcher.generate_candidates(original_code, vulnerabilities)
            llm_variants, llm_prompt, llm_raw = llm_result

            # `llm_prompt` is None whenever generation fell back to the original
            # code (e.g. Gemini 503/rate-limits). Those fallback copies are NOT
            # real patches and must never be validated or selected as the winner —
            # otherwise an unpatched byte-for-byte original could be posted as the fix.
            llm_failure = llm_prompt is None
            if llm_failure:
                self.log(
                    "LLM patch generation unavailable/skipped — omitting LLM candidates "
                    "since fallback only returned the unpatched original",
                    "warning",
                )

            llm_source = self.llm_patcher.model_id if self.llm_patcher.model_id else "gemini_unknown"

            for i, variant_code in enumerate(llm_variants):
                if llm_failure or variant_code.strip() == (original_code or "").strip():
                    self.log(f"Skipping LLM candidate {i+1}: no distinct patch produced", "warning")
                    continue
                candidates.append({
                    "id": f"llm_variant_{i+1}",
                    "code": variant_code,
                    "source": llm_source
                })

            if not llm_failure and llm_prompt is not None and llm_raw is not None:
                context["llm_prompt"] = llm_prompt
                context["llm_raw_response"] = llm_raw

        context["patch_candidates"] = candidates
        self.log(f"Prepared {len(candidates)} patch candidates for validation")
        
        return context
