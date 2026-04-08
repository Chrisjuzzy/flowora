import json
import os
import time
import statistics
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
CONCURRENCY = int(os.getenv("CONCURRENCY", "50"))
ITERATIONS = int(os.getenv("ITERATIONS", "1"))
AGENT_ID = int(os.getenv("LOAD_TEST_AGENT_ID", "1"))
WORKFLOW_ID = int(os.getenv("LOAD_TEST_WORKFLOW_ID", "1"))
TRANSPORT_RETRIES = int(os.getenv("TRANSPORT_RETRIES", "2"))

SHORT_PROMPT = "Summarize the Flowora value proposition in one sentence."
LONG_PROMPT = (
    "Create a launch plan for Flowora that includes a 10-step rollout, support FAQ, "
    "risk matrix, onboarding checklist, pricing assumptions, and founder memo. "
    "Keep it detailed enough to exercise long inference."
)


@dataclass
class Result:
    endpoint: str
    status: int
    latency_ms: float
    kind: str


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(0, min(len(values) - 1, int(round((len(values) - 1) * pct))))
    return values[index]


def call_endpoint(endpoint: str, payload: dict[str, Any], kind: str, timeout_seconds: float) -> Result:
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    request = urllib.request.Request(
        f"{API_BASE}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    status = 599
    for attempt in range(TRANSPORT_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response.read()
                status = response.status
            break
        except urllib.error.HTTPError as exc:
            exc.read()
            status = exc.code
            break
        except Exception:
            status = 599
            if attempt >= TRANSPORT_RETRIES:
                break
            time.sleep(0.2 * (attempt + 1))
    latency_ms = (time.perf_counter() - started) * 1000
    return Result(endpoint=endpoint, status=status, latency_ms=latency_ms, kind=kind)


def run_user(user_index: int) -> list[Result]:
    prompt = LONG_PROMPT if user_index % 3 == 0 else SHORT_PROMPT
    scenarios = [
        (
            f"/agents/{AGENT_ID}/run?async_execution=false",
            {"input_data": prompt},
            "agent_sync_long" if prompt == LONG_PROMPT else "agent_sync_short",
            180.0,
        ),
        (
            f"/agents/{AGENT_ID}/run?async_execution=true",
            {"input_data": SHORT_PROMPT},
            "agent_async_queue",
            90.0,
        ),
        (
            f"/workflows/{WORKFLOW_ID}/run?async_execution=false",
            {"input_data": SHORT_PROMPT},
            "workflow_sync",
            180.0,
        ),
        (
            f"/workflows/{WORKFLOW_ID}/run?async_execution=true",
            {"input_data": SHORT_PROMPT},
            "workflow_async_queue",
            90.0,
        ),
    ]
    return [call_endpoint(endpoint, payload, kind, timeout_seconds) for endpoint, payload, kind, timeout_seconds in scenarios]


def main() -> None:
    started = time.perf_counter()
    results: list[Result] = []
    total_workers = CONCURRENCY * ITERATIONS

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(run_user, worker_index) for worker_index in range(total_workers)]
        for future in as_completed(futures):
            results.extend(future.result())

    elapsed = time.perf_counter() - started
    by_kind: dict[str, list[Result]] = defaultdict(list)
    status_counts: Counter[int] = Counter()

    for result in results:
        by_kind[result.kind].append(result)
        status_counts[result.status] += 1

    summary: dict[str, Any] = {
        "concurrency": CONCURRENCY,
        "iterations": ITERATIONS,
        "total_requests": len(results),
        "elapsed_seconds": round(elapsed, 2),
        "requests_per_second": round(len(results) / elapsed, 2) if elapsed else 0.0,
        "status_counts": {str(key): value for key, value in sorted(status_counts.items())},
        "groups": {},
    }

    for kind, samples in sorted(by_kind.items()):
        latencies = [sample.latency_ms for sample in samples]
        statuses = Counter(sample.status for sample in samples)
        summary["groups"][kind] = {
            "count": len(samples),
            "status_counts": {str(key): value for key, value in sorted(statuses.items())},
            "avg_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p95_ms": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
            "max_ms": round(max(latencies), 2) if latencies else 0.0,
        }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
