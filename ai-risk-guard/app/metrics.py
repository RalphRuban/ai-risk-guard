"""
app/metrics.py
Prometheus metrics for AI Risk Guard monitoring.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ============================================================
# SCAN METRICS
# ============================================================

# Total number of scans performed
scan_total = Counter(
    "ai_risk_guard_scans_total",
    "Total number of scans performed",
    ["status"],  # success, failure
)

# Scan duration in seconds
scan_duration = Histogram(
    "ai_risk_guard_scan_duration_seconds",
    "Duration of security scans in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ============================================================
# VULNERABILITY METRICS
# ============================================================

# Total vulnerabilities detected
vulnerabilities_total = Counter(
    "ai_risk_guard_vulnerabilities_total",
    "Total vulnerabilities detected",
    ["type", "severity"],  # vulnerability type and severity
)

# Active vulnerabilities (gauge for current state)
vulnerabilities_active = Gauge(
    "ai_risk_guard_vulnerabilities_active",
    "Current number of active vulnerabilities",
    ["severity"],
)

# ============================================================
# PATCH METRICS
# ============================================================

# Total patches generated
patches_total = Counter(
    "ai_risk_guard_patches_total",
    "Total patches generated",
    ["status"],  # success, failure
)

# Patch quality scores
patch_quality = Histogram(
    "ai_risk_guard_patch_quality_score",
    "Distribution of patch quality scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ============================================================
# GEMINI API METRICS
# ============================================================

# Total Gemini API calls
gemini_calls_total = Counter(
    "ai_risk_guard_gemini_calls_total",
    "Total Gemini API calls",
    ["status"],  # success, failure, cache_hit
)

# Gemini API latency
gemini_latency = Histogram(
    "ai_risk_guard_gemini_latency_seconds",
    "Gemini API call latency in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 120.0],
)

# ============================================================
# LLM TRIAGE METRICS
# ============================================================

# LLM triage verdicts by outcome
triage_verdicts_total = Counter(
    "ai_risk_guard_triage_verdicts_total",
    "LLM triage verdicts",
    ["verdict"],  # confirmed, rejected, uncertain
)

# ============================================================
# CACHE METRICS
# ============================================================

# Cache hits and misses
cache_hits = Counter(
    "ai_risk_guard_cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # scan, ast, gemini
)

cache_misses = Counter(
    "ai_risk_guard_cache_misses_total",
    "Total cache misses",
    ["cache_type"],  # scan, ast, gemini
)

# Cache hit ratio
cache_hit_ratio = Gauge(
    "ai_risk_guard_cache_hit_ratio",
    "Cache hit ratio (0.0-1.0)",
    ["cache_type"],
)

# ============================================================
# AGENT METRICS
# ============================================================

# Agent execution duration
agent_duration = Histogram(
    "ai_risk_guard_agent_duration_seconds",
    "Duration of agent execution in seconds",
    ["agent"],  # scanner, patcher, validator, risk, orchestrator
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# Agent errors
agent_errors = Counter(
    "ai_risk_guard_agent_errors_total",
    "Total agent errors",
    ["agent", "error_type"],
)

# ============================================================
# SANDBOX METRICS
# ============================================================

# Sandbox executions by mode
sandbox_runs_total = Counter(
    "ai_risk_guard_sandbox_runs_total",
    "Total sandbox executions",
    ["mode", "success"],  # mode: docker_run, docker_test
)

# Sandbox timeouts
sandbox_timeouts_total = Counter(
    "ai_risk_guard_sandbox_timeouts_total",
    "Total sandbox timeouts",
    ["mode"],  # docker
)

# Sandbox execution duration
sandbox_duration = Histogram(
    "ai_risk_guard_sandbox_duration_seconds",
    "Sandbox execution duration in seconds",
    ["mode"],  # docker_run, docker_test
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# Sandbox runs that failed closed because Docker or the image was unavailable
sandbox_fail_closed_total = Counter(
    "ai_risk_guard_sandbox_fail_closed_total",
    "Sandbox runs that failed closed because Docker or the image was unavailable",
    ["reason"],  # daemon, image
)

# Whether the sandbox can currently execute (1 = Docker + image available)
sandbox_available = Gauge(
    "ai_risk_guard_sandbox_available",
    "Whether the sandbox can execute (1 = Docker + image available, 0 = unavailable)",
)

# ============================================================
# SYSTEM METRICS
# ============================================================

# Application info
app_info = Info(
    "ai_risk_guard",
    "AI Risk Guard application information",
)

# Active analyses
active_analyses = Gauge(
    "ai_risk_guard_active_analyses",
    "Number of currently running analyses",
)


def get_metrics() -> bytes:
    """Get all metrics in Prometheus format."""
    return generate_latest()


def get_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


def init_app_info():
    """Initialize application info metric."""
    app_info.info({
        "version": "2.0.0",
        "python_version": "3.13",
    })


def record_cache_event(cache_type: str, hit: bool):
    """Record a cache hit/miss and keep the per-type hit-ratio gauge in sync."""
    try:
        cache_hits.labels(cache_type=cache_type).inc() if hit else cache_misses.labels(cache_type=cache_type).inc()
        hits = cache_hits.labels(cache_type=cache_type)._value.get()
        misses = cache_misses.labels(cache_type=cache_type)._value.get()
        ratio = hits / (hits + misses) if (hits + misses) else 0.0
        cache_hit_ratio.labels(cache_type=cache_type).set(ratio)
    except Exception:
        pass



