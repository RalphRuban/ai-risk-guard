"""
Manager Agent.
The primary orchestrator that delegates tasks to specialized agents.
"""

import os
from typing import Any

from core.agents.patch_agent import PatchAgent
from core.agents.risk_agent import RiskAgent
from core.agents.scanner_agent import ScannerAgent
from core.agents.validator_agent import ValidatorAgent
from core.cache.gemini_cache import GeminiCache
from core.triage.llm_triage import LLMTriage
from utils.logger import logger


class ManagerAgent:
    """
    Orchestrator for the Multi-Agent security pipeline.
    """
    
    def __init__(self):
        # We moved agent instantiation into process_file to ensure thread-safety.
        # This prevents findings from one PR scan leaking into another.
        logger.info("AI Risk Guard Manager operational.", "MANAGER")

    def process_file(
        self,
        file_path: str,
        pr_context: dict[str, Any] | None = None,
        diff_data: str | None = None,
        repo_root: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Orchestrate the end-to-end security analysis via fresh, isolated agents.
        """
        # Validate inputs
        if not file_path or not os.path.isfile(file_path):
            logger.error(f"Invalid file_path: {file_path}", "MANAGER")
            return []

        # Instantiate fresh agents per request (Fix B: Concurrency Safety)
        scanner = ScannerAgent()
        patcher = PatchAgent()
        validator = ValidatorAgent()
        risk_analyzer = RiskAgent()

        # Initialize Shared Context (Agent Memory)
        pr_context = pr_context or {}
        context: dict[str, Any] = {
            "file_path": file_path,
            "pr_context": pr_context,
            "diff_data": diff_data,
            "repo_root": repo_root,
        }

        # Extract test_file_path from pr_context so validator_agent can find it
        test_file_path = pr_context.get("test_file_path")
        if test_file_path:
            context["test_file_path"] = test_file_path
        test_deps = pr_context.get("test_deps")
        if test_deps:
            context["test_deps"] = test_deps
        
        # 1. Read original code
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                context["original_code"] = f.read()
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to read file {file_path}: {e}", "MANAGER")
            return []
        
        # 2. Sequential Execution with per-agent error isolation
        # Using execute_with_metrics() for timing instrumentation
        try:
            context = scanner.execute_with_metrics(context)
        except Exception as e:
            logger.error(f"Scanner agent failed: {e}", "MANAGER")
            return []
        
        if not context.get("vulnerabilities"):
            logger.info("No vulnerabilities found, skipping remaining agents", "MANAGER")
            return []

        # LLM triage: confirm/refute low-confidence detections before patching.
        # Rejected findings become non-gating; a failure fails open (unchanged).
        llm_triage = LLMTriage()
        context["llm_triage"] = llm_triage
        try:
            context["vulnerabilities"] = llm_triage.triage_vulnerabilities(
                context.get("vulnerabilities", [])
            )
        except Exception as e:
            logger.warning(f"LLM triage failed — continuing with deterministic findings: {e}", "MANAGER")

        try:
            context = patcher.execute_with_metrics(context)
            # Record patch generation metric
            try:
                from app.metrics import patches_total
                num_candidates = len(context.get("patch_candidates") or [])
                if num_candidates > 0:
                    patches_total.labels(status="success").inc()
            except ImportError:
                pass
        except Exception as e:
            logger.error(f"Patcher agent failed: {e}", "MANAGER")
            try:
                from app.metrics import patches_total
                patches_total.labels(status="failure").inc()
            except ImportError:
                pass
            raw_vulns = context.get("vulnerabilities", [])
            wrapped = [
                {"vulnerability": v, "risk": 0.0, "confidence": 0.0}
                for v in raw_vulns
            ]
            return wrapped
        
        try:
            context = validator.execute_with_metrics(context)
        except Exception as e:
            logger.error(f"Validator agent failed: {e}", "MANAGER")
            return []

        # Cache LLM response only after validation — never cache unvalidated patches
        llm_prompt = context.get("llm_prompt")
        llm_raw_response = context.get("llm_raw_response")
        if llm_prompt is not None and llm_raw_response is not None:
            gemini_cache = GeminiCache()
            candidates = context.get("patch_candidates", [])
            # Cache only if at least one LLM candidate passed all critical stages
            # syntax 0.20 + sandbox 0.25 + rescan 0.15 + policy 0.15 = 0.75
            # Tests (0.25) are optional — they depend on having a test file.
            llm_passed = any(
                c.get("source", "") != "deterministic_ast"
                and c.get("validation_score", 0) >= 0.75
                for c in candidates
            )
            if llm_passed:
                gemini_cache.set(llm_prompt, llm_raw_response)
                logger.info("Cached LLM patch candidates after successful validation", "MANAGER")
            else:
                gemini_cache.invalidate_key(llm_prompt)
                logger.info("Invalidated LLM cache entry — all candidates failed validation", "MANAGER")

        try:
            context = risk_analyzer.execute_with_metrics(context)
        except Exception as e:
            logger.error(f"Risk agent failed: {e}", "MANAGER")

        return context.get("results", [])
