"""
core/config/app_config.py
Pydantic v2 model for application-level configuration.
"""


from pydantic import BaseModel, Field


class LlmConfig(BaseModel):
    model_fallback_chain: list[str] = Field(
        default_factory=lambda: [
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ],
        description="Ordered list of Gemini models to try (first available wins)"
    )


class ServerConfig(BaseModel):
    host: str = Field("0.0.0.0", description="Server bind address")
    port: int = Field(8000, description="Server port", ge=1, le=65535)
    debug: bool = Field(False, description="Enable debug mode")
    workers: int = Field(1, description="Number of worker threads", ge=1, le=10)


class WebhookConfig(BaseModel):
    max_concurrent_analyses: int = Field(3, description="Max simultaneous PR analyses", ge=1)
    analysis_timeout_seconds: int = Field(300, description="Max seconds for a single PR analysis, posts partial results if exceeded", ge=30)
    max_request_size_bytes: int = Field(5_242_880, description="Max accepted webhook payload size (bytes)", ge=1024, le=104_857_600)
    ignored_dirs: list[str] = Field(
        default_factory=lambda: [".venv", "venv", "node_modules", "migrations", "vendor", "__pycache__", "site-packages"],
        description="Directories to skip during scanning"
    )


class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Logging level")
    format: str = Field("json", description="Log output format (json or text)")


class SARIFConfig(BaseModel):
    upload_to_code_scanning: bool = Field(True, description="Upload SARIF to GitHub Code Scanning API")
    skip_if_all_dismissed: bool = Field(False, description="Skip SARIF upload if all alerts have been dismissed in GitHub UI")
    comment_on_pr: bool = Field(True, description="Post lean security report as PR comment")
    update_existing_comment: bool = Field(True, description="Update existing PR comment instead of creating new ones")

class GitHubAppConfig(BaseModel):
    set_pr_labels: bool = Field(True, description="Add security risk labels to PRs")


class ChecksConfig(BaseModel):
    create_check: bool = Field(True, description="Create an informational Check Run on PRs")
    name: str = Field("ai-risk-guard/validation", description="Check Run name shown on the Checks tab")
    gating: bool = Field(False, description="Whether the check gates merges. When false, failures are reported as neutral so the check never blocks merges")


class CodeQLConfig(BaseModel):
    enabled: bool = Field(True, description="Enable CodeQL provisioning for installed repos")
    auto_provision: bool = Field(True, description="Open a CodeQL setup PR when the app is installed on a repo")
    workflow_branch: str = Field("ai-risk-guard/codeql-setup", description="Branch used for the provisioning PR")
    pr_title: str = Field("Enable GitHub CodeQL analysis (via AI Risk Guard)", description="Title of the provisioning PR")


class ReactionFeedbackConfig(BaseModel):
    enabled: bool = Field(True, description="Enable polling 🚀/👎 reactions on bot PR comments")
    poll_interval_seconds: int = Field(900, description="How often to poll reactions for feedback", ge=60)
    max_comments_per_cycle: int = Field(50, description="Max bot comments checked per poll cycle", ge=1)


class TriageConfig(BaseModel):
    enabled: bool = Field(True, description="Enable LLM confirmation of low-confidence detections")
    min_detection_confidence: float = Field(
        0.95,
        description="Only findings with detection_confidence below this are sent to LLM triage",
        ge=0.0,
        le=1.0,
    )
    max_findings_per_call: int = Field(8, description="Max findings batched into one triage prompt", ge=1)


class ExplainerConfig(BaseModel):
    enabled: bool = Field(True, description="Enable LLM-generated context-aware risk explanations")


class SummaryConfig(BaseModel):
    enabled: bool = Field(True, description="Enable LLM-generated one-line PR summary in the report")


class RegressionExplainConfig(BaseModel):
    enabled: bool = Field(True, description="Enable LLM plain-language regression-test explanations in the PR report")
    max_test_names_in_prompt: int = Field(20, description="Max test names included in the LLM prompt", ge=1)


class ValidationConfig(BaseModel):
    enabled: bool = Field(True, description="Enable deferred re-validation: re-run scans whose sandbox validation failed closed once Docker is available again")
    poll_interval_seconds: int = Field(60, description="How often the background worker checks for pending scans and Docker availability", ge=10)
    max_revalidations_per_cycle: int = Field(3, description="Max scans re-triggered per worker cycle", ge=1, le=20)


class CIRunnerConfig(BaseModel):
    enabled: bool = Field(True, description="Enable GitHub Actions fallback validation: when Docker is unavailable locally, candidates are validated on a hosted runner via repository_dispatch")
    workflow_repo: str = Field("", description="Repo hosting the ai-risk-guard-validate workflow (owner/name). Empty falls back to the GITHUB_REPOSITORY env var, then skips")
    event_type: str = Field("ai-risk-guard-validate", description="repository_dispatch event type the validation workflow listens for")
    base_url: str = Field("", description="Public base URL the runner uses to fetch jobs and post results. Falls back to the CI_VALIDATION_BASE_URL env var")
    secret_env: str = Field("CI_VALIDATION_SECRET", description="Env var holding the shared secret used to authenticate runner <-> app calls")
    token_env: str = Field("CI_VALIDATION_TOKEN", description="Env var holding a GitHub token allowed to dispatch repository_dispatch to workflow_repo")


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)  # type: ignore[arg-type]
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)  # type: ignore[arg-type]
    logging: LoggingConfig = Field(default_factory=LoggingConfig)  # type: ignore[arg-type]
    sarif: SARIFConfig = Field(default_factory=SARIFConfig)  # type: ignore[arg-type]
    github_app: GitHubAppConfig = Field(default_factory=GitHubAppConfig)  # type: ignore[arg-type]
    checks: ChecksConfig = Field(default_factory=ChecksConfig)  # type: ignore[arg-type]
    codeql: CodeQLConfig = Field(default_factory=CodeQLConfig)  # type: ignore[arg-type]
    llm: LlmConfig = Field(default_factory=LlmConfig)  # type: ignore[arg-type]
    feedback: ReactionFeedbackConfig = Field(default_factory=ReactionFeedbackConfig)  # type: ignore[arg-type]
    triage: TriageConfig = Field(default_factory=TriageConfig)  # type: ignore[arg-type]
    explainer: ExplainerConfig = Field(default_factory=ExplainerConfig)  # type: ignore[arg-type]
    summary: SummaryConfig = Field(default_factory=SummaryConfig)  # type: ignore[arg-type]
    regression_explain: RegressionExplainConfig = Field(default_factory=RegressionExplainConfig)  # type: ignore[arg-type]
    validation: ValidationConfig = Field(default_factory=ValidationConfig)  # type: ignore[arg-type]
    ci_runner: CIRunnerConfig = Field(default_factory=CIRunnerConfig)  # type: ignore[arg-type]
