# Grafana Dashboards Configuration

The `/api/v1/metrics` Prometheus text exporter exposes essential metrics that should be configured into Grafana dashboards.

## System Health Dashboard
- **Panel 1: Global Error Rate**: Queries the 4xx and 5xx rates across standard endpoints.
- **Panel 2: Queue Depth**: Queries the `task_queue_length` parameter. Anything > 100 goes into Warning alerting limits.
- **Panel 3: API Latency (P99)**: Visualizes requests taking over 5.0s to full-resolve.

## Alert Delivery Dashboard
- **Panel 1: Success Rate by Channel**: Tracks SMS vs Email vs Push success rates avoiding DLQ trips.
- **Panel 2: Circuit Breaker Status**: Maps states of the connection instances (Closed -> Open).

## Privacy Monitoring Dashboard
- **Panel 1: Redaction Volume**: Counts the sum triggers of `PrivacyFilter` stripping PII.
- **Panel 2: Blocked Payload Metrics**: Rate of 422 errors due to extreme non-compliance in the payloads.

*Note: For actual JSON dashboard imports, utilize standard Prometheus endpoint queries constructed natively in the Grafana workspace.*
