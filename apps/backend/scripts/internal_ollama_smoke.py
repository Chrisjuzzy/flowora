import json
import random
import string
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 300


def request(method: str, path: str, payload=None, token: str | None = None):
    url = BASE_URL + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body


def main():
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    email = f"internal.ollama.{suffix}@flowora.local"
    password = "SmokeTest!123"

    status, body = request("POST", "/auth/register", {"email": email, "password": password})
    print("REGISTER", status, body)
    if status not in (200, 201):
        raise SystemExit("register failed")

    status, body = request("POST", "/auth/login", {"email": email, "password": password})
    print("LOGIN", status, body)
    if status != 200 or not isinstance(body, dict):
        raise SystemExit("login failed")

    token = body.get("access_token") or body.get("token") or body.get("accessToken")
    if not token:
        raise SystemExit("missing token")

    agent_payload = {
        "name": "Internal Ollama Verification Agent",
        "description": "Checks internal-only Ollama inference",
        "config": {
            "system_prompt": "You are a concise SaaS copywriter.",
            "prompt": "Write one short tagline about {input}.",
            "tools": [],
            "max_steps": 2,
        },
        "ai_provider": "local",
        "model_name": "qwen2.5:7b-instruct",
        "temperature": 0.3,
    }
    status, body = request("POST", "/agents/", agent_payload, token=token)
    print("CREATE_AGENT", status, body)
    if status != 200:
        raise SystemExit("agent create failed")
    agent_id = body["id"]

    status, body = request(
        "POST",
        f"/agents/{agent_id}/run?async_execution=false",
        {"input_data": "Flowora"},
        token=token,
    )
    print("RUN_AGENT", status, body)
    if status != 200 or body.get("status") != "completed":
        raise SystemExit("agent run failed")
    agent_result = body.get("result", "")
    if "mock" in str(agent_result).lower():
        raise SystemExit("mock output detected")

    workflow_payload = {
        "name": "Internal Ollama Verification Workflow",
        "description": "Single-step workflow",
        "config_json": {"steps": [{"agent_id": agent_id, "name": "Tagline"}]},
    }
    status, body = request("POST", "/workflows/", workflow_payload, token=token)
    print("CREATE_WORKFLOW", status, body)
    if status != 200:
        raise SystemExit("workflow create failed")
    workflow_id = body["id"]

    status, body = request(
        "POST",
        f"/workflows/{workflow_id}/run?async_execution=false",
        {"input_data": "Flowora internal AI routing"},
        token=token,
    )
    print("RUN_WORKFLOW", status, body)
    if status != 200 or body.get("status") != "completed":
        raise SystemExit("workflow run failed")
    workflow_result = body.get("final_output", "")
    if "mock" in str(workflow_result).lower():
        raise SystemExit("mock workflow output detected")

    print("AGENT_RESULT", agent_result)
    print("WORKFLOW_RESULT", workflow_result)


if __name__ == "__main__":
    main()
