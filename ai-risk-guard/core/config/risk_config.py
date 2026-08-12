"""
core/config/risk_config.py
Pydantic v2 model for risk scoring configuration.
"""


from pydantic import BaseModel, Field


class GatingConfig(BaseModel):
    max_allowed_risk: float = Field(8.5, description="Risk threshold for blocking (0-10)", ge=0.0, le=10.0)
    auto_request_changes_above: float = Field(4.0, description="Risk threshold above which the PR is automatically blocked (0-10)", ge=0.0, le=10.0)


class RiskConfig(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "severity": 0.22,
            "type": 0.14,
            "validation": 0.16,
            "confidence": 0.12,
            "complexity": 0.0,
            "sensitivity": 0.12,
            "exposure": 0.12,
            "quality": 0.12
        },
        description="Weighted scoring factors for risk calculation"
    )
    severity_normalization: dict[str, float] = Field(
        default_factory=lambda: {"CRITICAL": 1.0, "HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3},
        description="Mapping of severity labels to numeric values"
    )
    type_normalization: dict[str, float] = Field(
        default_factory=lambda: {
            "COMMAND_INJECTION": 1.0,
            "CODE_INJECTION": 0.95,
            "SQL_INJECTION": 1.0,
            "SSRF": 0.9,
            "INSECURE_DESERIALIZATION": 0.9,
            "PATH_TRAVERSAL": 0.8,
            "HARDCODED_SECRET": 0.7,
            "WEAK_CRYPTOGRAPHY": 0.5,
            "TLS_VERIFICATION_DISABLED": 0.5,
            "DEBUG_CODE": 0.2,
        },
        description="Mapping of vulnerability types to risk normalization values"
    )
    gating: GatingConfig = Field(default_factory=GatingConfig)  # type: ignore[arg-type]
