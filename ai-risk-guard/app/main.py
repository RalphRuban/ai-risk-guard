"""
main.py

AI Risk Guard
Phase 2 Main Orchestrator
"""

import argparse
from typing import Any

from core.agents.manager_agent import ManagerAgent
from core.agents.orchestrator_agent import OrchestrationAgent
from core.sarif.converter import build_analysis_result
from core.sarif.sarif_generator import SARIFGenerator
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
        pr_context: dict[str, Any] | None = None,
        diff_data: str | None = None,
        repo_root: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze a file for vulnerabilities using the agentic pipeline.
        """
        return self.manager.process_file(
            file_path=file_path,
            pr_context=pr_context,
            diff_data=diff_data,
            repo_root=repo_root,
        )

    def run_orchestrator(
        self,
        results: list[dict[str, Any]],
        pr_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run the orchestration agent once with all accumulated findings.

        Posts a single GitHub review and uploads a single aggregated SARIF
        for the entire PR, avoiding per-file duplicate actions.

        Args:
            results: All findings across all files.
            pr_context: PR metadata (repo_name, pr_number, access_token, commit_sha).

        Returns:
            The orchestrator's context dict (including executive_decision).
        """
        orchestrator = OrchestrationAgent()
        file_path = "unknown"
        if results:
            file_path = (
                results[0].get("vulnerability", {}).get("file_rel")
                or results[0].get("vulnerability", {}).get("file", "unknown")
            )
        context = {
            "results": results,
            "pr_context": pr_context,
            "file_path": file_path,
        }
        return orchestrator.execute(context)


# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Risk Guard - Security analysis tool"
    )
    parser.add_argument(
        "target",
        help="Target file to analyze"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "sarif"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: stdout)"
    )
    args = parser.parse_args()
    
    engine = AIRiskGuard()
    findings = engine.analyze_file(
        file_path=args.target
    )
    
    if args.format == "sarif":
        # Generate SARIF output using shared converter
        analysis_result = build_analysis_result(findings, args.target)
        generator = SARIFGenerator()
        output = generator.generate_json(analysis_result)
    else:
        # Default markdown output
        output = format_report(findings)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)