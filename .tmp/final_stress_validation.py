import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
METRICS_URL = f"{API_BASE}/metrics"
BACKEND_HEALTH_URL = f"{API_BASE}/api/health"
BACKEND_CONTAINER = "flowora-backend"
OLLAMA_CONTAINER = "flowora-ollama"


def api(method: str, path: str, data=None, token: str | None = None, timeout: int = 60):
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                return response.status, json.loads(raw)
            except Exception:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, raw


def read_metrics() -> dict[str, float]:
    with urllib.request.urlopen(METRICS_URL, timeout=30) as response:
        payload = response.read().decode("utf-8")
    targets = {
        "llm_timeout_total",
        "request_timeout_total",
        "http_requests_total",
        "http_errors_total",
    }
    values: dict[str, float] = {}
    for line in payload.splitlines():
        if not line or line.startswith("#"):
            continue
        metric_name = line.split("{", 1)[0].split(" ", 1)[0]
        if metric_name not in targets:
            continue
        try:
            values[line.rsplit(" ", 1)[0]] = float(line.rsplit(" ", 1)[1])
        except Exception:
            continue
    return values


def metric_delta(before: dict[str, float], after: dict[str, float], prefix: str) -> dict[str, float]:
    delta: dict[str, float] = {}
    for key, value in after.items():
        if not key.startswith(prefix):
            continue
        delta[key] = round(value - before.get(key, 0.0), 2)
    return dict(sorted(delta.items()))


def docker_json(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=60, check=True)
    return proc.stdout.strip()


def wait_for_health(timeout_seconds: int = 180) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=10) as response:
                body = response.read().decode("utf-8")
                if response.status == 200 and '"status":"healthy"' in body.replace(" ", ""):
                    return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("Backend health did not become healthy in time")


def setup_test_targets() -> tuple[str, int, int]:
    email = f"stress_{uuid.uuid4().hex[:8]}@flowora.local"
    password = "FloworaPass123!"

    status, body = api("POST", "/auth/register", {"email": email, "password": password, "full_name": "Stress User"})
    if status not in (200, 201):
        raise RuntimeError(f"Register failed: {status} {body}")

    status, body = api("POST", "/auth/login", {"email": email, "password": password})
    if status != 200 or "access_token" not in body:
        raise RuntimeError(f"Login failed: {status} {body}")
    token = body["access_token"]

    status, body = api(
        "POST",
        "/agents/",
        {
            "name": "Stress Validation Agent",
            "description": "Used for final launch validation.",
            "config": {
                "system_prompt": "You are a precise assistant for Flowora launch testing.",
                "prompt": "{input}",
            },
        },
        token=token,
    )
    if status not in (200, 201):
        raise RuntimeError(f"Create agent failed: {status} {body}")
    agent_id = body["id"]

    workflow_payload = {
        "name": "Stress Validation Workflow",
        "description": "Single-step workflow for launch validation.",
        "config_json": {"steps": [{"agent_id": agent_id}]},
        "is_public": False,
    }
    status, body = api("POST", "/workflows/", workflow_payload, token=token)
    if status not in (200, 201):
        raise RuntimeError(f"Create workflow failed: {status} {body}")
    workflow_id = body["id"]
    return token, agent_id, workflow_id


def run_load(concurrency: int, token: str, agent_id: int, workflow_id: int) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "ACCESS_TOKEN": token,
            "CONCURRENCY": str(concurrency),
            "ITERATIONS": "1",
            "LOAD_TEST_AGENT_ID": str(agent_id),
            "LOAD_TEST_WORKFLOW_ID": str(workflow_id),
            "API_BASE_URL": API_BASE,
        }
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "load_test.py")],
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"load_test failed for concurrency={concurrency}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def sample_docker_stats() -> list[str]:
    proc = subprocess.run(
        ["docker", "stats", "--no-stream", BACKEND_CONTAINER, OLLAMA_CONTAINER],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def backend_state() -> dict:
    raw = docker_json(["docker", "inspect", BACKEND_CONTAINER, "--format", "{{json .State}}"])
    return json.loads(raw)


def restart_count(container_name: str) -> int:
    return int(docker_json(["docker", "inspect", container_name, "--format", "{{.RestartCount}}"]))


def backend_log_tail() -> list[str]:
    proc = subprocess.run(
        ["docker-compose", "logs", "--tail=120", "backend"],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
        cwd=ROOT,
    )
    return proc.stdout.splitlines()[-60:]


def queue_lengths() -> dict[str, int]:
    proc = subprocess.run(
        [
            "docker-compose",
            "exec",
            "-T",
            "redis",
            "redis-cli",
            "--raw",
            "LLEN",
            "celery",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=ROOT,
        check=True,
    )
    celery_depth = int(proc.stdout.strip() or "0")
    return {"celery": celery_depth}


def main() -> None:
    wait_for_health()
    token, agent_id, workflow_id = setup_test_targets()

    restart_before = {
        BACKEND_CONTAINER: restart_count(BACKEND_CONTAINER),
        OLLAMA_CONTAINER: restart_count(OLLAMA_CONTAINER),
    }
    metrics_before = read_metrics()

    scenarios = []
    for concurrency in (50, 100, 200):
        summary = run_load(concurrency, token, agent_id, workflow_id)
        scenarios.append(summary)

    time.sleep(5)
    metrics_after = read_metrics()
    docker_stats_after = sample_docker_stats()
    backend_after = backend_state()
    restart_after = {
        BACKEND_CONTAINER: restart_count(BACKEND_CONTAINER),
        OLLAMA_CONTAINER: restart_count(OLLAMA_CONTAINER),
    }
    queues_after = queue_lengths()
    logs = backend_log_tail()

    allowed_statuses = {200, 202, 429, 504}
    unexpected_statuses = {}
    for scenario in scenarios:
        for status, count in scenario["status_counts"].items():
            if int(status) not in allowed_statuses:
                unexpected_statuses[status] = unexpected_statuses.get(status, 0) + count

    report = {
        "scenarios": scenarios,
        "metric_delta": {
            "llm_timeout_total": metric_delta(metrics_before, metrics_after, "llm_timeout_total"),
            "request_timeout_total": metric_delta(metrics_before, metrics_after, "request_timeout_total"),
            "http_errors_total": metric_delta(metrics_before, metrics_after, "http_errors_total"),
        },
        "restart_before": restart_before,
        "restart_after": restart_after,
        "backend_state": backend_after,
        "docker_stats_after": docker_stats_after,
        "queue_lengths_after": queues_after,
        "unexpected_statuses": unexpected_statuses,
        "backend_log_tail": logs,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
