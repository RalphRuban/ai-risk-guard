"""
core/sarif/__init__.py
SARIF output generation for GitHub Code Scanning integration.
"""

from core.sarif.converter import (
    build_analysis_result,
    build_analysis_summary,
    findings_to_risk_assessments,
)
from core.sarif.sarif_generator import SARIFGenerator

__all__ = [
    "SARIFGenerator",
    "build_analysis_result",
    "build_analysis_summary",
    "findings_to_risk_assessments",
]
