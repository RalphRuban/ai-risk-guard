"""
main.py

AI Risk Guard
Phase 2 Main Orchestrator
"""

from typing import List, Dict, Optional, Any

from utils.logger import logger
from core.agents.manager_agent import ManagerAgent
from services.github.reporter import format_report

# =========================================================
# MAIN ENGINE
# =========================================================
class AIRiskGuard:
    """
    Main entry point for AI Risk Guard.
    Now leverages a Multi-Agent architecture for orchestration.
    """

    def __init__(self):
        # Initialize the Manager Agent which coordinates specialized agents
        self.manager = ManagerAgent()

    # =====================================================
    # ANALYZE FILE
    # =====================================================

    def analyze_file(
        self,
        file_path: str,
        pr_context: Optional[Dict[str, Any]] = None,
        diff_data: Optional[str] = None,
        repo_root: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a file for vulnerabilities using the agentic pipeline.
        """
        return self.manager.process_file(
            file_path=file_path,
            pr_context=pr_context,
            diff_data=diff_data,
            repo_root=repo_root
        )


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(
            "Usage: python main.py <target_file>"
        )
        sys.exit(1)
    target = sys.argv[1]
    engine = AIRiskGuard()
    findings = engine.analyze_file(
        file_path=target
    )
    report = format_report(
        findings
    )
    print(report)