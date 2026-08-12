"""
core/exceptions/__init__.py
Granular custom exception classes for AI Risk Guard.
"""


class AIRiskGuardError(Exception):
    """Base exception for all AI Risk Guard errors."""


class ScanError(AIRiskGuardError):
    """Raised when vulnerability scanning fails."""


class PatchError(AIRiskGuardError):
    """Raised when patch generation or application fails."""


class ValidationError(AIRiskGuardError):
    """Raised when patch validation fails."""


class SandboxError(AIRiskGuardError):
    """Raised when sandbox execution fails."""


class RiskAnalysisError(AIRiskGuardError):
    """Raised when risk calculation fails."""


class CacheError(AIRiskGuardError):
    """Raised when cache operations fail."""


class ResourceCleanupError(AIRiskGuardError):
    """Raised when resource cleanup fails."""


class InputValidationError(AIRiskGuardError):
    """Raised when input validation fails."""
