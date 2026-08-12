"""
core/models/risk.py
Strict Pydantic v2 data models for risk assessment and scoring.
"""


from pydantic import BaseModel, ConfigDict, Field

from core.models.vulnerability import Vulnerability


class RiskFactor(BaseModel):
    value: float = Field(
        ...,
        description="The normalized value for this factor (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    weight: float = Field(
        ...,
        description="The weight assigned to this factor in the composite score",
        ge=0.0,
        le=1.0
    )
    contribution: float = Field(
        ...,
        description="The weighted contribution (value * weight) to the total score",
        ge=0.0,
        le=1.0
    )

class CodeMetrics(BaseModel):
    functions: int = Field(
        0,
        description="Number of functions in the scanned file"
    )
    complexity: int = Field(
        1,
        description="Cyclomatic complexity of the scanned code (baseline=1)",
        ge=1
    )
    max_depth: int = Field(
        0,
        description="Maximum nesting depth in the scanned code"
    )

class RiskAssessment(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True
    )

    vulnerability: Vulnerability = Field(
        ...,
        description="The vulnerability being assessed"
    )
    risk_score: float = Field(
        ...,
        description="Overall calculated risk score (0.0-10.0)",
        ge=0.0,
        le=10.0
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the patch (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    risk_breakdown: dict[str, RiskFactor] = Field(
        default_factory=dict,
        description="Per-factor breakdown of the risk calculation for explainability"
    )
    is_sensitive: bool = Field(
        False,
        description="Whether the file is in a sensitive area (e.g. auth, payment)"
    )
    policy_violations: list[str] = Field(
        default_factory=list,
        description="List of policy violations detected during validation"
    )
    priority: str | None = Field(
        None,
        description="Remediation priority (P1/P2/P3) derived from the risk score"
    )
    rule_id: str | None = Field(
        None,
        description="Stable machine-readable rule ID (e.g. CMD001)"
    )
    detection_confidence: float | None = Field(
        None,
        description="Confidence in the rule match itself (0.0-1.0)"
    )
    secret_entropy: float | None = Field(
        None,
        description="Shannon entropy of a hardcoded secret value (bits/char)"
    )
    remediation: str | None = Field(
        None,
        description="Recommended remediation steps for this finding"
    )
