"""
core/models/validation.py
Strict Pydantic v2 data models for patch validation and sandbox execution.
"""


from pydantic import BaseModel, Field


class SyntaxValidationResult(BaseModel):
    success: bool = Field(
        ...,
        description="Whether the validation stage passed"
    )
    message: str = Field(
        default="",
        description="Human-readable message describing the validation outcome"
    )
    stage: str | None = Field(
        None,
        description="Name of the validation stage that failed (only set on failure)"
    )

class SandboxResult(BaseModel):
    success: bool = Field(
        ...,
        description="Whether the sandbox execution completed without errors or policy violations"
    )
    output: str | None = Field(
        None,
        description="Captured stdout from the sandbox execution"
    )
    error: str | None = Field(
        None,
        description="Captured stderr or error message from the sandbox"
    )
    mode: str | None = Field(
        None,
        description="The sandbox execution mode (e.g. secure_validation, compile)"
    )

class RescanResult(BaseModel):
    success: bool = Field(
        ...,
        description="Whether no remaining vulnerabilities were found (true = clean)"
    )
    remaining_vulnerabilities: list[dict] = Field(
        default_factory=list,
        description="List of vulnerabilities still present after patching"
    )
    error: str | None = Field(
        None,
        description="Error message if the rescanner failed"
    )

class ValidationResult(BaseModel):
    syntax: SyntaxValidationResult = Field(
        ...,
        description="Result of AST syntax and pattern validation"
    )
    sandbox: SandboxResult = Field(
        ...,
        description="Result of Docker sandbox execution validation"
    )
    rescan: RescanResult = Field(
        ...,
        description="Result of security re-scan after patching"
    )
    policy: dict = Field(
        default_factory=dict,
        description="Result of policy compliance check (success, violations, etc.)"
    )
    validation_score: float = Field(
        0.0,
        description="Composite validation score (0.0-1.0) across all stages",
        ge=0.0,
        le=1.0
    )
