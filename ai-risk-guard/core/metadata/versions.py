"""
core/metadata/versions.py
Centralized tool/rules version and pipeline constants shared by the PR comment
and SARIF output so the two never drift apart.
"""

TOOL_NAME = "ai-risk-guard"
TOOL_VERSION = "2.1.0"
RULES_VERSION = "2026.08"
LANGUAGE = "Python"
SCAN_MODE = "PR diff"
ANALYSIS_ENGINE = "AST + Regex"
PATCH_ENGINE = "Deterministic AST + LLM (Gemini)"
VALIDATOR = "Docker sandbox + local fallback"
