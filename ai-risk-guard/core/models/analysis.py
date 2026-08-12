"""
core/models/analysis.py
Composite top-level Pydantic v2 model for the complete analysis pipeline output.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models.patch import PatchResult
from core.models.risk import RiskAssessment
from core.models.scan import ScanResult
from core.models.validation import ValidationResult


class AnalysisSummary(BaseModel):
    total_vulnerabilities: int = Field(
        0,
        description="Total number of vulnerabilities detected"
    )
    critical_count: int = Field(
        0,
        description="Number of vulnerabilities with risk score >= 8.0"
    )
    moderate_count: int = Field(
        0,
        description="Number of vulnerabilities with risk score >= 4.0 and < 8.0"
    )
    low_count: int = Field(
        0,
        description="Number of vulnerabilities with risk score < 4.0"
    )
    max_risk_score: float = Field(
        0.0,
        description="Highest risk score across all vulnerabilities",
        ge=0.0,
        le=10.0
    )
    patches_applied: int = Field(
        0,
        description="Number of successfully applied patches"
    )
    patches_failed: int = Field(
        0,
        description="Number of patches that failed or conflicted"
    )
    passed_all_stages: bool = Field(
        True,
        description="Whether all stages (scan, patch, validate, risk) completed successfully"
    )

class AnalysisResult(BaseModel):
    model_config = ConfigDict(
        ser_json_timedelta="iso8601"
    )

    file_path: str = Field(
        ...,
        description="The absolute path of the analyzed file"
    )
    scan: ScanResult = Field(
        ...,
        description="Results from the vulnerability scanning stage"
    )
    patch: PatchResult | None = Field(
        None,
        description="Results from the patch generation and application stage"
    )
    validation: ValidationResult | None = Field(
        None,
        description="Results from the validation stage (syntax, sandbox, rescan, policy)"
    )
    risk_assessments: list[RiskAssessment] = Field(
        default_factory=list,
        description="Risk assessment for each vulnerability found"
    )
    executive_decision: str | None = Field(
        None,
        description="The autonomous decision made by the orchestrator (COMMENT, REQUEST_CHANGES, APPROVE)"
    )
    summary: AnalysisSummary = Field(
        default_factory=AnalysisSummary,  # type: ignore[arg-type]
        description="Aggregated summary statistics for the analysis run"
    )
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when the analysis completed"
    )
    scan_duration_seconds: float = Field(
        0.0,
        description="Wall-clock duration of the scan in seconds"
    )
