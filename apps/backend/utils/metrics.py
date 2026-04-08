import time
from threading import Lock

_lock = Lock()
_metrics = {
    "total_requests": 0,
    "error_requests": 0,
    "avg_latency_ms": 0.0,
    "min_latency_ms": None,
    "max_latency_ms": None
}


def record_request(duration_ms: float, status_code: int) -> None:
    with _lock:
        _metrics["total_requests"] += 1
        if status_code >= 400:
            _metrics["error_requests"] += 1

        # Incremental average
        total = _metrics["total_requests"]
        prev_avg = _metrics["avg_latency_ms"]
        _metrics["avg_latency_ms"] = prev_avg + ((duration_ms - prev_avg) / total)

        if _metrics["min_latency_ms"] is None or duration_ms < _metrics["min_latency_ms"]:
            _metrics["min_latency_ms"] = duration_ms
        if _metrics["max_latency_ms"] is None or duration_ms > _metrics["max_latency_ms"]:
            _metrics["max_latency_ms"] = duration_ms



def snapshot() -> dict:
    with _lock:
        return dict(_metrics)
