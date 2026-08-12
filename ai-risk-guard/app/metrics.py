"""
app/metrics.py
Prometheus metrics for AI Risk Guard monitoring.
"""

from datetime import UTC

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
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
    ["mode", "success"],  # mode: docker_run, docker_test, local_run, local_test
)

# Sandbox timeouts
sandbox_timeouts_total = Counter(
    "ai_risk_guard_sandbox_timeouts_total",
    "Total sandbox timeouts",
    ["mode"],  # docker, local
)

# Sandbox execution duration
sandbox_duration = Histogram(
    "ai_risk_guard_sandbox_duration_seconds",
    "Sandbox execution duration in seconds",
    ["mode"],  # docker_run, docker_test, local_run, local_test
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
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


# ============================================================
# SUMMARY AGGREGATION
# ============================================================

def _collect_samples() -> dict:
    """Gather all metric samples from the in-process registry.

    Returns a mapping of sample name -> list of (labels, value) tuples.
    Sample names carry the _bucket/_sum/_count suffixes for histograms.
    """
    samples: dict[str, list] = {}
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            samples.setdefault(sample.name, []).append((sample.labels, sample.value))
    return samples


def _counter_by_label(samples: dict, name: str, label: str) -> dict:
    """Group a labeled counter (or gauge) by the given label value."""
    grouped: dict[str, float] = {}
    for labels, value in samples.get(name, []):
        key = labels.get(label, "unknown")
        grouped[key] = grouped.get(key, 0.0) + value
    return grouped


def _histogram_stats(samples: dict, name: str) -> dict:
    """Derive count/sum/avg/p50/p95 from a Prometheus histogram's samples."""
    bucket_counts: list[tuple[float, float]] = []
    total = 0.0
    count = 0.0
    for sample_name, series in samples.items():
        if sample_name.startswith(name + "_bucket"):
            for labels, value in series:
                bucket_counts.append((float(labels.get("le", "0")), value))
        elif sample_name == name + "_sum":
            total = sum(v for _, v in series)
        elif sample_name == name + "_count":
            count = sum(v for _, v in series)
    bucket_counts.sort()

    def quantile(q: float) -> float:
        if count <= 0 or not bucket_counts:
            return 0.0
        target = count * q
        for le, cum in bucket_counts:
            if cum >= target:
                return le
        return bucket_counts[-1][0]

    return {
        "count": int(count),
        "sum": round(total, 3),
        "avg": round(total / count, 3) if count else 0.0,
        "p50": quantile(0.50),
        "p95": quantile(0.95),
    }


def _counter_value(samples: dict, name: str) -> float:
    """Sum all series values for a counter metric."""
    return sum(v for _, v in samples.get(name, []))


def build_metrics_summary() -> dict:
    """Flatten the in-process Prometheus collectors into a JSON-friendly summary.

    Safe to call on an idle registry: every section degrades to zeros.
    """
    from datetime import datetime

    s = _collect_samples()

    cache_hits = _counter_by_label(s, "ai_risk_guard_cache_hits_total", "cache_type")
    cache_misses = _counter_by_label(s, "ai_risk_guard_cache_misses_total", "cache_type")
    cache_keys = set(cache_hits) | set(cache_misses)
    hit_ratio = {
        k: round(cache_hits.get(k, 0.0) / (cache_hits.get(k, 0.0) + cache_misses.get(k, 0.0)), 4)
        if (cache_hits.get(k, 0.0) + cache_misses.get(k, 0.0)) else 0.0
        for k in cache_keys
    }

    by_type: dict[str, dict[str, float]] = {}
    vuln_total = 0.0
    for labels, value in s.get("ai_risk_guard_vulnerabilities_total", []):
        vt = labels.get("type", "unknown")
        sev = labels.get("severity", "unknown")
        records = by_type.setdefault(vt, {})
        records[sev] = records.get(sev, 0.0) + value
        vuln_total += value

    patch_status = _counter_by_label(s, "ai_risk_guard_patches_total", "status")
    gemini_calls = _counter_by_label(s, "ai_risk_guard_gemini_calls_total", "status")
    agent_errors = _counter_by_label(s, "ai_risk_guard_agent_errors_total", "agent")
    sandbox_runtime = _counter_by_label(s, "ai_risk_guard_sandbox_runs_total", "mode")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scans": {
            "total": int(_counter_value(s, "ai_risk_guard_scans_total")),
            "success": int(_counter_by_label(s, "ai_risk_guard_scans_total", "status").get("success", 0)),
            "failure": int(_counter_by_label(s, "ai_risk_guard_scans_total", "status").get("failure", 0)),
            "duration_seconds": _histogram_stats(s, "ai_risk_guard_scan_duration_seconds"),
        },
        "vulnerabilities": {
            "total": int(vuln_total),
            "by_type": by_type,
            "active": _counter_by_label(s, "ai_risk_guard_vulnerabilities_active", "severity"),
        },
        "patches": {
            "total": int(_counter_value(s, "ai_risk_guard_patches_total")),
            "success": int(patch_status.get("success", 0)),
            "failure": int(patch_status.get("failure", 0)),
            "quality_score": _histogram_stats(s, "ai_risk_guard_patch_quality_score"),
        },
        "gemini": {
            "calls": {k: int(v) for k, v in gemini_calls.items()},
            "latency_seconds": _histogram_stats(s, "ai_risk_guard_gemini_latency_seconds"),
        },
        "triage": {
            "verdicts": _counter_by_label(s, "ai_risk_guard_triage_verdicts_total", "verdict"),
        },
        "cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_ratio": hit_ratio,
        },
        "agents": {
            "duration_seconds": {
                agent: _histogram_stats_by(s, "ai_risk_guard_agent_duration_seconds", agent)
                for agent in _agent_labels(s)
            },
            "errors": agent_errors,
        },
        "sandbox": {
            "runs": sandbox_runtime,
            "timeouts": _counter_by_label(s, "ai_risk_guard_sandbox_timeouts_total", "mode"),
            "duration_seconds": {
                mode: _histogram_stats_by(s, "ai_risk_guard_sandbox_duration_seconds", mode)
                for mode in _histogram_modes(s, "ai_risk_guard_sandbox_duration_seconds")
            },
        },
        "system": {
            "active_analyses": int(_counter_value(s, "ai_risk_guard_active_analyses")),
        },
    }


def _histogram_modes(samples: dict, name: str) -> list:
    """Collect the distinct label modes present across a labeled histogram."""
    modes: set[str] = set()
    for sample_name, series in samples.items():
        if sample_name.startswith(name + "_bucket"):
            for labels, _ in series:
                if "mode" in labels:
                    modes.add(labels["mode"])
                elif "agent" in labels:
                    modes.add(labels["agent"])
    return sorted(modes)


def _agent_labels(samples: dict) -> list:
    """Collect distinct agent labels from the agent duration histogram."""
    agents: set[str] = set()
    for sample_name, series in samples.items():
        if sample_name.startswith("ai_risk_guard_agent_duration_seconds_bucket"):
            for labels, _ in series:
                if "agent" in labels:
                    agents.add(labels["agent"])
    return sorted(agents)


def _histogram_stats_by(samples: dict, name: str, label: str) -> dict:
    """Histogram stats restricted to a single matching label value."""
    bucket_counts: list[tuple[float, float]] = []
    total = 0.0
    count = 0.0
    for sample_name, series in samples.items():
        prefix = name + "_bucket"
        if sample_name.startswith(prefix):
            for labels, value in series:
                src = labels.get("mode") or labels.get("agent")
                if src == label:
                    bucket_counts.append((float(labels.get("le", "0")), value))
        elif sample_name == name + "_sum":
            for labels, value in series:
                src = labels.get("mode") or labels.get("agent")
                if src == label:
                    total += value
        elif sample_name == name + "_count":
            for labels, value in series:
                src = labels.get("mode") or labels.get("agent")
                if src == label:
                    count += value
    bucket_counts.sort()

    def quantile(q: float) -> float:
        if count <= 0 or not bucket_counts:
            return 0.0
        target = count * q
        for le, cum in bucket_counts:
            if cum >= target:
                return le
        return bucket_counts[-1][0]

    return {
        "count": int(count),
        "sum": round(total, 3),
        "avg": round(total / count, 3) if count else 0.0,
        "p50": quantile(0.50),
        "p95": quantile(0.95),
    }
