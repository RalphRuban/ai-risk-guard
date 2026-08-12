"""
core/config/sandbox_config.py
Pydantic v2 model for Docker sandbox execution configuration.
"""


from pydantic import BaseModel, Field


class DockerConfig(BaseModel):
    image: str = Field("ai-risk-guard:sandbox", description="Docker image name for sandbox (build with: docker build -f sandbox/Dockerfile.sandbox -t ai-risk-guard:sandbox .)")
    dockerfile: str = Field("sandbox/Dockerfile.sandbox", description="Path to the sandbox Dockerfile, used to auto-build a local image when it cannot be pulled")
    build_local_image: bool = Field(True, description="Auto-build the sandbox image from the Dockerfile when it is not present locally and cannot be pulled")
    memory: str = Field("512m", description="Memory limit (Docker format, e.g. 512m, 1g)")
    cpu: float = Field(0.5, description="CPU quota", ge=0.1, le=8.0)
    pids_limit: int = Field(32, description="Maximum number of processes", ge=1)
    network: str = Field("none", description="Network mode (none, bridge, host)")
    read_only: bool = Field(True, description="Mount filesystem as read-only")
    tmpfs: str = Field("/tmp:rw,noexec,nosuid,size=64m", description="Tmpfs mount for writable temp")
    timeout_seconds: int = Field(10, description="Execution timeout in seconds", ge=1, le=120)
    test_timeout_seconds: int = Field(60, description="Pytest execution timeout in seconds", ge=1, le=300)
    max_output_bytes: int = Field(65536, description="Max stdout/stderr bytes before truncation", ge=1024, le=1048576)
    test_max_output_bytes: int = Field(262144, description="Max pytest stdout/stderr bytes before truncation", ge=1024, le=5242880)
    cap_drop: list[str] = Field(
        default_factory=lambda: ["ALL"],
        description="Linux capabilities to drop"
    )
    security_opts: list[str] = Field(
        default_factory=lambda: ["no-new-privileges"],
        description="Docker --security-opt flags (e.g. no-new-privileges, seccomp=profile.json)"
    )


class LocalConfig(BaseModel):
    memory_limit_mb: int = Field(256, description="Max memory per child process in MB (0=unlimited, Linux only)", ge=0)
    cpu_time_seconds: int = Field(8, description="Max CPU time in seconds (0=unlimited, Linux only)", ge=0)
    max_processes: int = Field(16, description="Max child processes (0=unlimited, Linux only)", ge=0)
    max_file_bytes: int = Field(1048576, description="Max file write size in bytes (0=unlimited, Linux only)", ge=0)
    timeout_seconds: int = Field(10, description="Execution timeout in seconds", ge=1, le=120)
    test_timeout_seconds: int = Field(60, description="Pytest execution timeout in seconds", ge=1, le=300)
    max_output_bytes: int = Field(65536, description="Max stdout/stderr bytes before truncation", ge=1024, le=1048576)
    test_max_output_bytes: int = Field(262144, description="Max pytest stdout/stderr bytes before truncation", ge=1024, le=5242880)
    strip_secrets: bool = Field(True, description="Strip sensitive env vars from child process")


class SandboxConfig(BaseModel):
    docker: DockerConfig = Field(default_factory=DockerConfig)  # type: ignore[arg-type]
    local: LocalConfig = Field(default_factory=LocalConfig)  # type: ignore[arg-type]
    enable_local_fallback_comparison: bool = Field(
        False,
        description="Run local tests when Docker tests fail to show comparison in PR comment"
    )
    enable_expected_failure_analysis: bool = Field(
        True,
        description="Attribute regression-test failures that pin removed vulnerabilities to the fix (expected failures) instead of reporting them as regressions"
    )
