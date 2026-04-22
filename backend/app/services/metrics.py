"""
Metrics collector for observability.

Collects and exposes metrics for alerts, delivery, circuit breakers,
and queue performance. Outputs in Prometheus text exposition format
and JSON summary for admin dashboards.
"""

import time
from collections import defaultdict
from typing import Any

import structlog

from app.services.circuit_breaker import get_all_circuit_breakers

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """In-memory metrics collector with Prometheus-format export.

    Collects gauges, counters, and histogram-like distributions
    for alert and system performance monitoring.

    Attributes:
        _counters: Simple increment counters.
        _gauges: Point-in-time values.
        _histograms: Lists of observed values for distribution stats.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.monotonic()

    # ── Recording Methods ────────────────────────────────────────────────

    def record_alert_created(self, severity: str) -> None:
        """Record an alert creation event.

        Args:
            severity: Alert severity level.
        """
        self._counters["alert_created_total"] += 1
        self._counters[f"alert_created_{severity}"] += 1

    def record_delivery_attempt(
        self,
        channel: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record a notification delivery attempt.

        Args:
            channel: Notification channel (sms, email, push).
            success: Whether the delivery succeeded.
            latency_ms: Delivery latency in milliseconds.
        """
        self._counters[f"delivery_attempts_{channel}"] += 1
        if success:
            self._counters[f"delivery_success_{channel}"] += 1
        else:
            self._counters[f"delivery_failure_{channel}"] += 1

        self._histograms[f"delivery_latency_ms_{channel}"].append(latency_ms)
        self._histograms["alert_delivery_latency_ms"].append(latency_ms)

    def record_retry(self, channel: str) -> None:
        """Record a notification retry attempt.

        Args:
            channel: Notification channel being retried.
        """
        self._counters["alert_retry_total"] += 1
        self._counters[f"alert_retry_{channel}"] += 1

    def record_dlq_entry(self, channel: str) -> None:
        """Record an item being sent to DLQ.

        Args:
            channel: Notification channel.
        """
        self._counters["dlq_entries_total"] += 1
        self._counters[f"dlq_entries_{channel}"] += 1

    def set_queue_length(self, length: int) -> None:
        """Update the current queue length gauge.

        Args:
            length: Current number of items in queue.
        """
        self._gauges["queue_length"] = float(length)

    def record_queue_processing(self, latency_ms: float) -> None:
        """Record queue task processing latency.

        Args:
            latency_ms: Processing time in milliseconds.
        """
        self._histograms["queue_processing_latency_ms"].append(latency_ms)

    # ── Query Methods ────────────────────────────────────────────────────

    def get_delivery_success_rate(self, channel: str | None = None) -> float:
        """Calculate delivery success rate.

        Args:
            channel: Optional channel filter. None for overall rate.

        Returns:
            Success rate as a float (0.0 to 1.0).
        """
        if channel:
            total = self._counters.get(f"delivery_attempts_{channel}", 0)
            success = self._counters.get(f"delivery_success_{channel}", 0)
        else:
            total = sum(
                v for k, v in self._counters.items()
                if k.startswith("delivery_attempts_")
            )
            success = sum(
                v for k, v in self._counters.items()
                if k.startswith("delivery_success_")
            )

        return success / total if total > 0 else 0.0

    def _histogram_stats(self, key: str) -> dict[str, float]:
        """Calculate histogram statistics.

        Args:
            key: Histogram key.

        Returns:
            Dict with count, sum, avg, min, max, p50, p95, p99.
        """
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "sum": round(sum(sorted_vals), 2),
            "avg": round(sum(sorted_vals) / n, 2),
            "min": round(sorted_vals[0], 2),
            "max": round(sorted_vals[-1], 2),
            "p50": round(sorted_vals[n // 2], 2),
            "p95": round(sorted_vals[int(n * 0.95)], 2) if n > 1 else round(sorted_vals[0], 2),
            "p99": round(sorted_vals[int(n * 0.99)], 2) if n > 1 else round(sorted_vals[0], 2),
        }

    # ── Export Methods ───────────────────────────────────────────────────

    def get_prometheus_format(self) -> str:
        """Export all metrics in Prometheus text exposition format.

        Returns:
            Prometheus-formatted metrics string.
        """
        lines: list[str] = []

        # Counters
        lines.append("# HELP alert_created_total Total alerts created")
        lines.append("# TYPE alert_created_total counter")
        lines.append(f"alert_created_total {self._counters.get('alert_created_total', 0)}")

        for severity in ["warning", "error", "critical"]:
            count = self._counters.get(f"alert_created_{severity}", 0)
            lines.append(f'alert_created_total{{severity="{severity}"}} {count}')

        lines.append("")
        lines.append("# HELP alert_retry_total Total retry attempts")
        lines.append("# TYPE alert_retry_total counter")
        lines.append(f"alert_retry_total {self._counters.get('alert_retry_total', 0)}")

        lines.append("")
        lines.append("# HELP dlq_entries_total Total DLQ entries")
        lines.append("# TYPE dlq_entries_total counter")
        lines.append(f"dlq_entries_total {self._counters.get('dlq_entries_total', 0)}")

        # Delivery per channel
        for channel in ["sms", "email", "push"]:
            attempts = self._counters.get(f"delivery_attempts_{channel}", 0)
            success = self._counters.get(f"delivery_success_{channel}", 0)
            failure = self._counters.get(f"delivery_failure_{channel}", 0)
            rate = success / attempts if attempts > 0 else 0.0

            lines.append("")
            lines.append(f'# HELP delivery_attempts_total{{channel="{channel}"}} Delivery attempts for {channel}')
            lines.append(f'delivery_attempts_total{{channel="{channel}"}} {attempts}')
            lines.append(f'delivery_success_total{{channel="{channel}"}} {success}')
            lines.append(f'delivery_failure_total{{channel="{channel}"}} {failure}')
            lines.append(f'delivery_success_rate{{channel="{channel}"}} {rate:.4f}')

        # Histograms
        latency_stats = self._histogram_stats("alert_delivery_latency_ms")
        lines.append("")
        lines.append("# HELP alert_delivery_latency_ms Alert delivery latency")
        lines.append("# TYPE alert_delivery_latency_ms histogram")
        lines.append(f"alert_delivery_latency_ms_count {latency_stats['count']}")
        lines.append(f"alert_delivery_latency_ms_sum {latency_stats['sum']}")

        queue_stats = self._histogram_stats("queue_processing_latency_ms")
        lines.append("")
        lines.append("# HELP queue_processing_latency_ms Queue processing latency")
        lines.append("# TYPE queue_processing_latency_ms histogram")
        lines.append(f"queue_processing_latency_ms_count {queue_stats['count']}")
        lines.append(f"queue_processing_latency_ms_sum {queue_stats['sum']}")

        # Gauges
        lines.append("")
        lines.append("# HELP queue_length Current queue length")
        lines.append("# TYPE queue_length gauge")
        lines.append(f"queue_length {int(self._gauges.get('queue_length', 0))}")

        # Circuit breaker states
        breakers = get_all_circuit_breakers()
        if breakers:
            lines.append("")
            lines.append("# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half_open)")
            lines.append("# TYPE circuit_breaker_state gauge")
            state_map = {"closed": 0, "open": 1, "half_open": 2}
            for name, cb in breakers.items():
                state_val = state_map.get(cb.state.value, -1)
                lines.append(f'circuit_breaker_state{{service="{name}"}} {state_val}')

        lines.append("")
        return "\n".join(lines)

    def get_summary(self) -> dict[str, Any]:
        """Return a JSON-friendly metrics summary for admin dashboards.

        Returns:
            Dict with all metrics organized by category.
        """
        breakers = get_all_circuit_breakers()
        cb_summary = {
            name: cb.get_metrics() for name, cb in breakers.items()
        }

        return {
            "alerts": {
                "total_created": self._counters.get("alert_created_total", 0),
                "by_severity": {
                    s: self._counters.get(f"alert_created_{s}", 0)
                    for s in ["warning", "error", "critical"]
                },
                "retry_total": self._counters.get("alert_retry_total", 0),
                "dlq_total": self._counters.get("dlq_entries_total", 0),
            },
            "delivery": {
                channel: {
                    "attempts": self._counters.get(f"delivery_attempts_{channel}", 0),
                    "success": self._counters.get(f"delivery_success_{channel}", 0),
                    "failure": self._counters.get(f"delivery_failure_{channel}", 0),
                    "success_rate": self.get_delivery_success_rate(channel),
                    "latency": self._histogram_stats(f"delivery_latency_ms_{channel}"),
                }
                for channel in ["sms", "email", "push"]
            },
            "queue": {
                "length": int(self._gauges.get("queue_length", 0)),
                "processing_latency": self._histogram_stats("queue_processing_latency_ms"),
            },
            "circuit_breakers": cb_summary,
            "uptime_seconds": round(time.monotonic() - self._start_time, 2),
        }
