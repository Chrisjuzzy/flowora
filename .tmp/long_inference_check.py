import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid


BASE = "http://localhost:8000"
EMAIL = f"longrun_{uuid.uuid4().hex[:8]}@flowora.local"
PASSWORD = "FloworaPass123!"
PROMPT = (
    "Write a detailed launch plan for Flowora with a 10-step rollout, risk matrix, "
    "metrics plan, founder memo, and support FAQ. Keep it substantial but concise."
)

results = {
    "stats_samples": [],
    "request": None,
}


def api(method, path, data=None, token=None, timeout=30):
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return exc.code, parsed


def run_long_agent(token, agent_id):
    started = time.time()
    status, body = api(
        "POST",
        f"/agents/{agent_id}/run?async_execution=false",
        {"input_data": PROMPT},
        token=token,
        timeout=240,
    )
    results["request"] = {
        "status": status,
        "body": body,
        "elapsed_seconds": round(time.time() - started, 2),
    }


status, body = api(
    "POST",
    "/auth/register",
    {"email": EMAIL, "password": PASSWORD, "full_name": "Long Run User"},
)
if status not in (200, 201):
    raise SystemExit(f"register failed: {status} {body}")

status, body = api("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
if status != 200 or "access_token" not in body:
    raise SystemExit(f"login failed: {status} {body}")
token = body["access_token"]

agent_payload = {
    "name": "Long Inference Agent",
    "description": "Exercises long local inference safely.",
    "config": {
        "system_prompt": "You are a precise SaaS strategy assistant.",
        "prompt": "{input}",
    },
}
status, body = api("POST", "/agents/", agent_payload, token=token)
if status not in (200, 201):
    raise SystemExit(f"create agent failed: {status} {body}")
agent_id = body["id"]

thread = threading.Thread(target=run_long_agent, args=(token, agent_id), daemon=True)
thread.start()

for _ in range(24):
    sample_started = time.time()
    try:
        proc = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}",
                "flowora-backend",
                "flowora-ollama",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        results["stats_samples"].append(
            {
                "t": round(time.time() - sample_started, 2),
                "output": proc.stdout.strip().splitlines(),
                "stderr": proc.stderr.strip(),
            }
        )
    except subprocess.TimeoutExpired:
        results["stats_samples"].append(
            {
                "t": round(time.time() - sample_started, 2),
                "output": [],
                "stderr": "docker stats timed out",
            }
        )
    if not thread.is_alive():
        break
    time.sleep(5)

thread.join(timeout=1)

inspect = subprocess.run(
    ["docker", "inspect", "flowora-backend", "--format", "{{json .State}}"],
    capture_output=True,
    text=True,
    timeout=20,
)
results["backend_state"] = inspect.stdout.strip()

logs = subprocess.run(
    ["docker-compose", "logs", "--tail=80", "backend"],
    capture_output=True,
    text=True,
    timeout=30,
)
results["backend_logs_tail"] = logs.stdout.splitlines()[-40:]

print(json.dumps(results, indent=2))
