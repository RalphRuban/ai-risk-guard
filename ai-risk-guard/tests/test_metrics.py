"""
tests/test_metrics.py
Tests for Prometheus-based metrics instrumentation.
"""

import prometheus_client

from app import metrics


class TestMetrics:
    """Tests for Prometheus metrics definitions."""

    def test_scan_total_counter(self):
        assert isinstance(metrics.scan_total, prometheus_client.Counter)

    def test_scan_duration_histogram(self):
        assert isinstance(metrics.scan_duration, prometheus_client.Histogram)

    def test_vulnerabilities_total_counter(self):
        assert isinstance(metrics.vulnerabilities_total, prometheus_client.Counter)

    def test_vulnerabilities_active_gauge(self):
        assert isinstance(metrics.vulnerabilities_active, prometheus_client.Gauge)

    def test_patches_total_counter(self):
        assert isinstance(metrics.patches_total, prometheus_client.Counter)

    def test_patch_quality_histogram(self):
        assert isinstance(metrics.patch_quality, prometheus_client.Histogram)

    def test_gemini_calls_total_counter(self):
        assert isinstance(metrics.gemini_calls_total, prometheus_client.Counter)

    def test_gemini_latency_histogram(self):
        assert isinstance(metrics.gemini_latency, prometheus_client.Histogram)

    def test_cache_hits_counter(self):
        assert isinstance(metrics.cache_hits, prometheus_client.Counter)

    def test_cache_misses_counter(self):
        assert isinstance(metrics.cache_misses, prometheus_client.Counter)

    def test_cache_hit_ratio_gauge(self):
        assert isinstance(metrics.cache_hit_ratio, prometheus_client.Gauge)

    def test_agent_duration_histogram(self):
        assert isinstance(metrics.agent_duration, prometheus_client.Histogram)

    def test_agent_errors_counter(self):
        assert isinstance(metrics.agent_errors, prometheus_client.Counter)

    def test_active_analyses_gauge(self):
        assert isinstance(metrics.active_analyses, prometheus_client.Gauge)

    def test_get_metrics_returns_bytes(self):
        result = metrics.get_metrics()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_get_content_type(self):
        ct = metrics.get_content_type()
        assert "text/plain" in ct
        assert "charset=utf-8" in ct

    def test_metrics_output_contains_metric_names(self):
        output = metrics.get_metrics().decode("utf-8")
        assert "ai_risk_guard_scans_total" in output
        assert "ai_risk_guard_vulnerabilities_total" in output
        assert "ai_risk_guard_patches_total" in output
        assert "ai_risk_guard_gemini_calls_total" in output

    def test_counter_increment(self):
        metrics.cache_hits.labels(cache_type="test_metrics").inc()
        output = metrics.get_metrics().decode("utf-8")
        assert 'cache_type="test_metrics"' in output

    def test_gauge_set_value(self):
        metrics.vulnerabilities_active.labels(severity="test_gauge").set(42)
        output = metrics.get_metrics().decode("utf-8")
        assert "42.0" in output

    def test_histogram_observes(self):
        metrics.scan_duration.observe(0.5)
        output = metrics.get_metrics().decode("utf-8")
        assert "ai_risk_guard_scan_duration_seconds" in output

    def test_init_app_info(self):
        metrics.init_app_info()
        output = metrics.get_metrics().decode("utf-8")
        assert "ai_risk_guard_info" in output
        assert "python_version" in output

    def test_metric_labels_preserved(self):
        metrics.scan_total.labels(status="test_preserved_success").inc()
        metrics.scan_total.labels(status="test_preserved_failure").inc()
        output = metrics.get_metrics().decode("utf-8")
        assert 'status="test_preserved_success"' in output
        assert 'status="test_preserved_failure"' in output
