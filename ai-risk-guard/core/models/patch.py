"""
core/models/patch.py
Strict Pydantic v2 data models for patch generation and application.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PatchSource(str, Enum):
    AST = "ast"
    LLM = "llm"

class PatchCandidate(BaseModel):
    source: PatchSource = Field(
        ...,
        description="Origin of the patch: deterministic AST transformer or LLM generation"
    )
    vulnerability_type: str = Field(
        ...,
        description="The type of vulnerability this patch targets (e.g. COMMAND_INJECTION)"
    )
    patched_code: str = Field(
        ...,
        description="The full source code after applying the patch"
    )
    diff: str = Field(
        default="",
        description="Unified diff string showing the changes made by this patch"
    )
    explanation: str | None = Field(
        None,
        description="Human-readable explanation of the remediation applied"
    )
    ast_success: bool = Field(
        False,
        description="Whether the AST-level transformation succeeded without errors"
    )
    error: str | None = Field(
        None,
        description="Error message if the patch application failed"
    )

    model_config = ConfigDict(
        use_enum_values=True
    )

class PatchResult(BaseModel):
    file_path: str = Field(
        ...,
        description="The absolute path of the file that was patched"
    )
    final_code: str = Field(
        ...,
        description="The final source code after all patches have been applied"
    )
    combined_diff: str = Field(
        default="",
        description="Unified diff of all changes applied to the file"
    )
    candidates: list[PatchCandidate] = Field(
        default_factory=list,
        description="All patch candidates generated and applied"
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Vulnerability types that could not be patched due to conflicts"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages from failed patch attempts"
    )

class PatchQuality(BaseModel):
    syntax_valid: bool = Field(
        False,
        description="Whether the patched code has valid syntax"
    )
    security_validated: bool = Field(
        False,
        description="Whether security rescan confirmed the vulnerability is removed"
    )
    tests_passed: bool | None = Field(
        None,
        description="Whether regression tests passed (requires test synthesis)"
    )
    complexity_increase: float = Field(
        0.0,
        description="Relative complexity increase (negative factor, lower is better)"
    )
    formatting_preserved: bool = Field(
        True,
        description="Whether the original code formatting was preserved"
    )
    confidence: float = Field(
        0.0,
        description="Confidence score from the adaptive learning engine (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    overall_score: float | None = Field(
        None,
        description="Weighted composite quality score (0.0-1.0)"
    )
