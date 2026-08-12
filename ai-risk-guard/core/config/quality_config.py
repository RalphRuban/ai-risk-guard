"""
core/config/quality_config.py
Pydantic v2 model for patch quality scoring configuration.
"""


from pydantic import BaseModel, Field


class QualityConfig(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "syntax_validity": 0.20,
            "security_validation": 0.25,
            "tests_passed": 0.20,
            "complexity": -0.10,
            "formatting_preserved": 0.10,
            "confidence": 0.15,
        },
        description="Weighted scoring factors for patch quality calculation"
    )
