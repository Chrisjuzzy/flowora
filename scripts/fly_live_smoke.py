#!/usr/bin/env python3
"""Lightweight live smoke test for a deployed Flowora environment."""

from __future__ import annotations

import argparse
import json
import sys
import time
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    status: int
    body: Any


class FloworaSmokeError(RuntimeError):
    pass


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = 30,
) -> Response:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else None
            return Response(status=resp.status, body=body)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw
        return Response(status=exc.code, body=body)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise FloworaSmokeError(f"network request failed for {url}: {exc}") from exc


def ensure_ok(response: Response, step: str, allowed: tuple[int, ...] = (200,)) -> Response:
    if response.status not in allowed:
        raise FloworaSmokeError(f"{step} failed: HTTP {response.status} -> {response.body}")
    return response


def health_check(api_base: str) -> dict[str, Any]:
    response = ensure_ok(request_json("GET", f"{api_base}/api/health", timeout=45), "health check")
    if not isinstance(response.body, dict) or response.body.get("status") != "healthy":
        raise FloworaSmokeError(f"health check returned unexpected body: {response.body}")
    return response.body


def register_user(api_base: str, email: str, password: str) -> None:
    payload = {
        "email": email,
        "password": password,
        "subscription_tier": "free",
        "subscription_status": "active",
    }
    response = request_json("POST", f"{api_base}/auth/register", payload=payload)
    if response.status not in (200, 201, 400):
        raise FloworaSmokeError(f"register failed: HTTP {response.status} -> {response.body}")


def login(api_base: str, email: str, password: str) -> str:
    payload = {"username": email, "password": password}
    response = ensure_ok(request_json("POST", f"{api_base}/auth/login", payload=payload), "login")
    token = response.body.get("access_token") if isinstance(response.body, dict) else None
    if not token:
        raise FloworaSmokeError(f"login response missing access token: {response.body}")
    return token


def create_agent(api_base: str, token: str) -> int:
    payload = {
        "name": "Fly Smoke Agent",
        "description": "Controlled smoke test agent",
        "config": {"system_prompt": "You are a concise helpful assistant."},
        "ai_provider": "mock",
        "model_name": "mock",
        "temperature": 0.1,
    }
    response = ensure_ok(
        request_json("POST", f"{api_base}/agents", payload=payload, token=token),
        "create agent",
    )
    agent_id = response.body.get("id") if isinstance(response.body, dict) else None
    if not agent_id:
        raise FloworaSmokeError(f"create agent response missing id: {response.body}")
    return int(agent_id)


def run_agent(api_base: str, token: str, agent_id: int) -> dict[str, Any]:
    url = f"{api_base}/agents/{agent_id}/run?async_execution=false"
    payload = {"input_data": "Say hello from the live Flowora smoke test."}
    response = ensure_ok(request_json("POST", url, payload=payload, token=token, timeout=90), "run agent")
    return response.body if isinstance(response.body, dict) else {"raw": response.body}


def create_workflow(api_base: str, token: str, agent_id: int) -> int:
    payload = {
        "name": "Fly Smoke Workflow",
        "description": "One-step smoke workflow",
        "config_json": {
            "steps": [
                {"agent_id": agent_id},
            ]
        },
    }
    response = ensure_ok(
        request_json("POST", f"{api_base}/workflows", payload=payload, token=token),
        "create workflow",
    )
    workflow_id = response.body.get("id") if isinstance(response.body, dict) else None
    if not workflow_id:
        raise FloworaSmokeError(f"create workflow response missing id: {response.body}")
    return int(workflow_id)


def run_workflow(api_base: str, token: str, workflow_id: int) -> dict[str, Any]:
    url = f"{api_base}/workflows/{workflow_id}/run?async_execution=false"
    payload = {"input_data": "Turn this into a short live smoke workflow response."}
    response = ensure_ok(request_json("POST", url, payload=payload, token=token, timeout=90), "run workflow")
    return response.body if isinstance(response.body, dict) else {"raw": response.body}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://flowora-api.fly.dev")
    parser.add_argument("--site-url", default="https://flowora-web.fly.dev")
    parser.add_argument("--password", default="FloworaSmoke!123")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    site_url = args.site_url.rstrip("/")
    stamp = int(time.time())
    email = f"smoke-{stamp}@flowora.dev"

    report: dict[str, Any] = {
        "site_url": site_url,
        "api_base": api_base,
        "email": email,
    }

    try:
        report["health"] = health_check(api_base)
        register_user(api_base, email, args.password)
        token = login(api_base, email, args.password)
        report["login"] = "ok"
        agent_id = create_agent(api_base, token)
        report["agent_id"] = agent_id
        report["agent_run"] = run_agent(api_base, token, agent_id)
        workflow_id = create_workflow(api_base, token, agent_id)
        report["workflow_id"] = workflow_id
        report["workflow_run"] = run_workflow(api_base, token, workflow_id)
    except FloworaSmokeError as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        print(json.dumps(report, indent=2))
        return 1

    report["status"] = "passed"
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
