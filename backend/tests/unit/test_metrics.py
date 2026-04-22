"""
Unit tests for the metrics collector.

Tests counter increments, histogram recording,
Prometheus format export, and summary endpoint.
"""

import pytest

from app.services.circuit_breaker import reset_all_circuit_breakers, get_circuit_breaker
from app.services.metrics import MetricsCollector


class TestMetricsCounters:
    """Tests for counter-based metrics."""

    def setup_method(self):
        reset_all_circuit_breakers()

    def test_alert_created_increments(self):
        mc = MetricsCollector()
        mc.record_alert_created("critical")
        mc.record_alert_created("warning")
        mc.record_alert_created("critical")
        summary = mc.get_summary()
        assert summary["alerts"]["total_created"] == 3
        assert summary["alerts"]["by_severity"]["critical"] == 2
        assert summary["alerts"]["by_severity"]["warning"] == 1

    def test_delivery_attempt_success(self):
        mc = MetricsCollector()
        mc.record_delivery_attempt("sms", True, 50.0)
        mc.record_delivery_attempt("sms", True, 75.0)
        mc.record_delivery_attempt("sms", False, 100.0)
        summary = mc.get_summary()
        assert summary["delivery"]["sms"]["attempts"] == 3
        assert summary["delivery"]["sms"]["success"] == 2
        assert summary["delivery"]["sms"]["failure"] == 1

    def test_retry_counter(self):
        mc = MetricsCollector()
        mc.record_retry("sms")
        mc.record_retry("email")
        mc.record_retry("sms")
        summary = mc.get_summary()
        assert summary["alerts"]["retry_total"] == 3

    def test_dlq_counter(self):
        mc = MetricsCollector()
        mc.record_dlq_entry("sms")
        summary = mc.get_summary()
        assert summary["alerts"]["dlq_total"] == 1


class TestMetricsDeliveryRate:
    """Tests for delivery success rate calculation."""

    def test_success_rate_all_success(self):
        mc = MetricsCollector()
        mc.record_delivery_attempt("sms", True, 50.0)
        mc.record_delivery_attempt("sms", True, 60.0)
        assert mc.get_delivery_success_rate("sms") == 1.0

    def test_success_rate_mixed(self):
        mc = MetricsCollector()
        mc.record_delivery_attempt("email", True, 50.0)
        mc.record_delivery_attempt("email", False, 60.0)
        assert mc.get_delivery_success_rate("email") == 0.5

    def test_success_rate_no_attempts(self):
        mc = MetricsCollector()
        assert mc.get_delivery_success_rate("sms") == 0.0

    def test_overall_success_rate(self):
        mc = MetricsCollector()
        mc.record_delivery_attempt("sms", True, 50.0)
        mc.record_delivery_attempt("email", False, 60.0)
        assert mc.get_delivery_success_rate() == 0.5


class TestMetricsHistogram:
    """Tests for histogram-based metrics."""

    def test_delivery_latency_stats(self):
        mc = MetricsCollector()
        for latency in [10, 20, 30, 40, 50]:
            mc.record_delivery_attempt("sms", True, latency)
        summary = mc.get_summary()
        latency = summary["delivery"]["sms"]["latency"]
        assert latency["count"] == 5
        assert latency["avg"] == 30.0
        assert latency["min"] == 10.0
        assert latency["max"] == 50.0

    def test_queue_processing_latency(self):
        mc = MetricsCollector()
        mc.record_queue_processing(100.0)
        mc.record_queue_processing(200.0)
        summary = mc.get_summary()
        assert summary["queue"]["processing_latency"]["count"] == 2
        assert summary["queue"]["processing_latency"]["avg"] == 150.0


class TestMetricsQueueGauge:
    """Tests for queue length gauge."""

    def test_set_queue_length(self):
        mc = MetricsCollector()
        mc.set_queue_length(42)
        summary = mc.get_summary()
        assert summary["queue"]["length"] == 42


class TestPrometheusFormat:
    """Tests for Prometheus text exposition format."""

    def setup_method(self):
        reset_all_circuit_breakers()

    def test_prometheus_output_contains_counters(self):
        mc = MetricsCollector()
        mc.record_alert_created("critical")
        output = mc.get_prometheus_format()
        assert "alert_created_total 1" in output
        assert 'alert_created_total{severity="critical"} 1' in output

    def test_prometheus_output_contains_delivery(self):
        mc = MetricsCollector()
        mc.record_delivery_attempt("sms", True, 50.0)
        output = mc.get_prometheus_format()
        assert 'delivery_attempts_total{channel="sms"} 1' in output
        assert 'delivery_success_total{channel="sms"} 1' in output

    def test_prometheus_output_contains_queue(self):
        mc = MetricsCollector()
        mc.set_queue_length(5)
        output = mc.get_prometheus_format()
        assert "queue_length 5" in output

    def test_prometheus_output_contains_circuit_breakers(self):
        get_circuit_breaker("twilio")
        mc = MetricsCollector()
        output = mc.get_prometheus_format()
        assert 'circuit_breaker_state{service="twilio"} 0' in output  # 0 = closed


class TestMetricsSummary:
    """Tests for JSON summary structure."""

    def setup_method(self):
        reset_all_circuit_breakers()

    def test_summary_structure(self):
        mc = MetricsCollector()
        summary = mc.get_summary()
        assert "alerts" in summary
        assert "delivery" in summary
        assert "queue" in summary
        assert "circuit_breakers" in summary
        assert "uptime_seconds" in summary

    def test_summary_includes_cb_metrics(self):
        cb = get_circuit_breaker("test-svc")
        mc = MetricsCollector()
        summary = mc.get_summary()
        assert "test-svc" in summary["circuit_breakers"]
