"""Метрики Prometheus (локальный registry)."""

from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()

requests_total = Counter(
    "requests_total",
    "Total number of requests",
    ["endpoint", "provider", "status"],
    registry=registry,
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "provider"],
    registry=registry,
)

jobs_total = Counter(
    "jobs_total",
    "Total jobs processed",
    ["provider", "status"],
    registry=registry,
)

webhook_deliveries_total = Counter(
    "webhook_deliveries_total",
    "Total webhook deliveries",
    ["status"],
    registry=registry,
)

tokens_total = Counter(
    "tokens_total",
    "Total tokens",
    ["provider", "model", "kind"],
    registry=registry,
)

cost_rub_total = Counter(
    "cost_rub_total",
    "Total cost in RUB",
    ["provider", "model"],
    registry=registry,
)
