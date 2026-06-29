"""
Manager Agent.
The primary orchestrator that delegates tasks to specialized agents.
"""

from typing import List, Dict, Any, Optional
from core.agents.scanner_agent import ScannerAgent
from core.agents.patch_agent import PatchAgent
from core.agents.validator_agent import ValidatorAgent
from core.agents.risk_agent import RiskAgent
from core.agents.orchestrator_agent import OrchestrationAgent
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
        pr_context: Optional[Dict[str, Any]] = None,
        diff_data: Optional[str] = None,
        repo_root: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Orchestrate the end-to-end security analysis via fresh, isolated agents.
        """
        # Instantiate fresh agents per request (Fix B: Concurrency Safety)
        scanner = ScannerAgent()
        patcher = PatchAgent()
        validator = ValidatorAgent()
        risk_analyzer = RiskAgent()
        orchestrator = OrchestrationAgent()

        # Initialize Shared Context (Agent Memory)
        context = {
            "file_path": file_path,
            "pr_context": pr_context or {},
            "diff_data": diff_data,
            "repo_root": repo_root,
        }
        
        try:
            # 1. Read original code
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                context["original_code"] = f.read()
            
            # 2. Sequential Execution
            context = scanner.execute(context)
            
            if not context.get("vulnerabilities"):
                return []
                
            context = patcher.execute(context)
            context = validator.execute(context)
            context = risk_analyzer.execute(context)
            context = orchestrator.execute(context)
            
            return context.get("results", [])
            
        except Exception as e:
            logger.error(f"Manager execution failed: {e}", "MANAGER")
            return []
