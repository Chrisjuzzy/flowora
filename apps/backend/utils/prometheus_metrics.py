from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["path"])
ERROR_COUNT = Counter("http_errors_total", "Total HTTP errors", ["path", "status"])
LLM_TIMEOUT_TOTAL = Counter("llm_timeout_total", "Total LLM timeout events", ["provider", "model"])
REQUEST_TIMEOUT_TOTAL = Counter("request_timeout_total", "Total API request timeout events", ["route"])

TOTAL_REQUESTS_GAUGE = Gauge("total_requests", "Total requests (app snapshot)")
ERROR_REQUESTS_GAUGE = Gauge("error_requests", "Error requests (app snapshot)")
AVG_LATENCY_GAUGE = Gauge("avg_latency_ms", "Average request latency (ms)")
MIN_LATENCY_GAUGE = Gauge("min_latency_ms", "Min request latency (ms)")
MAX_LATENCY_GAUGE = Gauge("max_latency_ms", "Max request latency (ms)")
QUEUE_DEPTH = Gauge("celery_queue_depth", "Celery queue depth", ["queue"])


def record_http_request(duration_ms: float, status_code: int, path: str, method: str) -> None:
    status = str(status_code)
    REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
    REQUEST_LATENCY.labels(path=path).observe(duration_ms / 1000.0)
    if status_code >= 400:
        ERROR_COUNT.labels(path=path, status=status).inc()


def update_snapshot_metrics(snapshot: dict) -> None:
    TOTAL_REQUESTS_GAUGE.set(snapshot.get("total_requests", 0))
    ERROR_REQUESTS_GAUGE.set(snapshot.get("error_requests", 0))
    AVG_LATENCY_GAUGE.set(snapshot.get("avg_latency_ms", 0.0))
    MIN_LATENCY_GAUGE.set(snapshot.get("min_latency_ms") or 0.0)
    MAX_LATENCY_GAUGE.set(snapshot.get("max_latency_ms") or 0.0)


def record_queue_depth(queue: str, depth: int) -> None:
    QUEUE_DEPTH.labels(queue=queue).set(depth)


def record_llm_timeout(provider: str, model: str) -> None:
    LLM_TIMEOUT_TOTAL.labels(provider=provider, model=model).inc()


def record_request_timeout(route: str) -> None:
    REQUEST_TIMEOUT_TOTAL.labels(route=route).inc()
