import json
import random
import string
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 300


def _request(method: str, path: str, payload=None, token=None):
    url = f"{BASE_URL}{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body
    except Exception as e:
        return None, str(e)


def _rand_email():
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f"ceo.smoke.{suffix}@flowora.local"


def main():
    email = _rand_email()
    password = "SmokeTest!123"

    print("Registering user:", email)
    status, body = _request("POST", "/auth/register", {"email": email, "password": password})
    print("Register:", status, body)

    print("Logging in...")
    status, body = _request("POST", "/auth/login", {"email": email, "password": password})
    print("Login:", status, body)
    if status != 200 or not isinstance(body, dict):
        raise SystemExit("Login failed; aborting.")

    token = body.get("access_token") or body.get("token") or body.get("accessToken")
    if not token:
        raise SystemExit("No access token returned; aborting.")

    print("Creating agent...")
    agent_payload = {
        "name": "CEO Smoke Test Agent",
        "description": "Quick agent used for smoke testing",
        "config": {
            "system_prompt": "You are a concise product copywriter.",
            "prompt": "Generate one crisp tagline about {input}.",
            "tools": [],
            "max_steps": 2,
        },
        "ai_provider": "local",
        "model_name": "qwen2.5:7b-instruct",
        "temperature": 0.3,
    }
    status, body = _request("POST", "/agents/", agent_payload, token=token)
    print("Create agent:", status, body)
    if status != 200:
        raise SystemExit("Agent creation failed; aborting.")
    agent_id = body.get("id")

    print("Running agent...")
    status, body = _request(
        "POST",
        f"/agents/{agent_id}/run?async_execution=false",
        {"input_data": "Flowora"},
        token=token,
    )
    print("Agent run:", status, body)
    if status != 200:
        raise SystemExit("Agent run failed; aborting.")
    if not isinstance(body, dict) or body.get("status") != "completed":
        raise SystemExit(f"Agent run did not complete successfully: {body}")
    result_text = body.get("result") if isinstance(body, dict) else ""
    if isinstance(result_text, str) and "mock" in result_text.lower():
        raise SystemExit("Agent run returned mock output; Ollama not healthy.")

    print("Creating workflow...")
    workflow_payload = {
        "name": "CEO Smoke Workflow",
        "description": "Single-step workflow for smoke testing",
        "config_json": {
            "steps": [
                {"agent_id": agent_id, "name": "Tagline"}
            ]
        },
    }
    status, body = _request("POST", "/workflows/", workflow_payload, token=token)
    print("Create workflow:", status, body)
    if status != 200:
        raise SystemExit("Workflow creation failed; aborting.")
    workflow_id = body.get("id")

    print("Running workflow...")
    status, body = _request(
        "POST",
        f"/workflows/{workflow_id}/run?async_execution=false",
        {"input_data": "Flowora platform benefits"},
        token=token,
    )
    print("Workflow run:", status, body)
    if status != 200:
        raise SystemExit("Workflow run failed; aborting.")
    if not isinstance(body, dict) or body.get("status") != "completed":
        raise SystemExit(f"Workflow run did not complete successfully: {body}")
    wf_text = body.get("final_output") if isinstance(body, dict) else ""
    if isinstance(wf_text, str) and "mock" in wf_text.lower():
        raise SystemExit("Workflow run returned mock output; Ollama not healthy.")


if __name__ == "__main__":
    main()
