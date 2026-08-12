"""
core/sarif/converter.py
Shared utility for converting dict-based findings to SARIF-compatible Pydantic models.
"""

from typing import Any

from utils.logger import logger


def findings_to_risk_assessments(findings: list[dict[str, Any]], default_file: str = "unknown") -> list[Any]:
    """
    Convert a list of dict-based findings to RiskAssessment objects.
    
    Args:
        findings: List of vulnerability findings (dicts from agent pipeline)
        default_file: Default file path if not present in finding
        
    Returns:
        List of RiskAssessment objects
    """
    from core.models.risk import RiskAssessment
    from core.models.vulnerability import Vulnerability
    
    risk_assessments = []
    
    for finding in findings:
        vuln_data = finding.get("vulnerability", {})
        try:
            # Use file_rel (repo-relative) if available, fall back to file (absolute temp path)
            file_path = vuln_data.get("file_rel") or vuln_data.get("file", default_file)
            vuln = Vulnerability.model_validate({
                "type": vuln_data.get("type", "COMMAND_INJECTION"),
                "file": file_path,
                "line": vuln_data.get("line", 0),
                "code": vuln_data.get("code", ""),
                "severity": vuln_data.get("severity", "MEDIUM"),
                "message": vuln_data.get("message", ""),
                "cwe": vuln_data.get("cwe"),
                "owasp": vuln_data.get("owasp"),
                "is_new": vuln_data.get("is_new", False),
                "function": vuln_data.get("function"),
                "context_lines": vuln_data.get("context_lines"),
            })
            
            # Convert risk_breakdown dict to proper RiskFactor objects
            risk_breakdown = {}
            raw_breakdown = finding.get("risk_breakdown", {})
            if raw_breakdown:
                from core.models.risk import RiskFactor
                for key, value in raw_breakdown.items():
                    if isinstance(value, dict):
                        risk_breakdown[key] = RiskFactor(
                            value=value.get("value", 0.0),
                            weight=value.get("weight", 0.0),
                            contribution=value.get("contribution", 0.0)
                        )
            
            assessment = RiskAssessment.model_validate({
                "vulnerability": vuln,
                "risk_score": finding.get("risk", 0.0),
                "confidence": finding.get("confidence", 0.0),
                "risk_breakdown": risk_breakdown,
                "policy_violations": finding.get("validation", {}).get("policy_violations", []),
                "priority": finding.get("priority"),
                "rule_id": finding.get("rule_id"),
                "detection_confidence": finding.get("detection_confidence"),
                "secret_entropy": finding.get("secret_entropy"),
                "remediation": finding.get("remediation"),
            })
            risk_assessments.append(assessment)
        except Exception as e:
            logger.warning(f"Failed to convert finding to RiskAssessment: {e}")
            continue
    
    return risk_assessments


def build_analysis_summary(findings: list[dict[str, Any]], passed_all_stages: bool = True) -> Any:
    """
    Build an AnalysisSummary from a list of findings.
    
    Args:
        findings: List of vulnerability findings (dicts)
        passed_all_stages: Whether all analysis stages completed successfully
        
    Returns:
        AnalysisSummary object
    """
    from core.models.analysis import AnalysisSummary
    
    if not findings:
        return AnalysisSummary.model_validate({"passed_all_stages": passed_all_stages})

    return AnalysisSummary.model_validate({
        "total_vulnerabilities": len(findings),
        "critical_count": sum(1 for f in findings if f.get("risk", 0) >= 8.0),
        "moderate_count": sum(1 for f in findings if 4.0 <= f.get("risk", 0) < 8.0),
        "low_count": sum(1 for f in findings if f.get("risk", 0) < 4.0),
        "max_risk_score": max((f.get("risk", 0) for f in findings), default=0.0),
        "patches_applied": sum(1 for f in findings if f.get("patch_applied")),
        "passed_all_stages": passed_all_stages
    })


def build_analysis_result(
    findings: list[dict[str, Any]], 
    file_path: str = "unknown",
    scan_duration_seconds: float = 0.0,
    passed_all_stages: bool = True,
) -> Any:
    """
    Build a complete AnalysisResult from findings.
    
    Args:
        findings: List of vulnerability findings (dicts)
        file_path: Path to the analyzed file
        scan_duration_seconds: Duration of the scan in seconds
        passed_all_stages: Whether all analysis stages completed successfully
        
    Returns:
        AnalysisResult object ready for SARIF generation
    """
    from core.models.analysis import AnalysisResult
    from core.models.scan import ScanResult
    
    risk_assessments = findings_to_risk_assessments(findings, file_path)
    summary = build_analysis_summary(findings, passed_all_stages=passed_all_stages)
    
    # Get the actual file path from findings if available (prefer file_rel)
    actual_file = file_path
    if findings:
        vuln = findings[0].get("vulnerability", {})
        actual_file = vuln.get("file_rel") or vuln.get("file", file_path)
    
    return AnalysisResult.model_validate({
        "file_path": actual_file,
        "scan": ScanResult(
            success=True,
            file_path=actual_file,
            vulnerabilities=[],
            scan_duration_seconds=scan_duration_seconds
        ),
        "risk_assessments": risk_assessments,
        "summary": summary,
        "scan_duration_seconds": scan_duration_seconds,
    })
