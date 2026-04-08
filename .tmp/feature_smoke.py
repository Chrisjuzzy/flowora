import json
import random
import string
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def _request(method: str, path: str, payload=None, token=None, params: str = ""):
    url = f"{BASE_URL}{path}{params}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body
    except Exception as e:
        return None, str(e)


def _rand_email():
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f"feature.smoke.{suffix}@flowora.local"


def main():
    email = _rand_email()
    password = "SmokeTest!123"

    print("Registering:", email)
    status, body = _request("POST", "/auth/register", {"email": email, "password": password})
    print("Register:", status, body)

    status, body = _request("POST", "/auth/login", {"email": email, "password": password})
    print("Login:", status, body)
    if status != 200 or not isinstance(body, dict):
        raise SystemExit("Login failed")
    token = body.get("access_token")

    def authed(method, path, payload=None, params=""):
        return _request(method, path, payload=payload, token=token, params=params)

    checks = [
        ("Dashboard", authed("GET", "/intelligence/dashboard")),
        ("Agents list", authed("GET", "/agents/")),
        ("Executions list", authed("GET", "/executions/")),
        ("Workspaces list", authed("GET", "/workspaces/")),
        ("Create workspace", authed("POST", "/workspaces/", {"name": "Smoke Workspace"})),
        ("Wallet balance", authed("GET", "/wallet/balance")),
        ("Wallet recharge", authed("POST", "/wallet/recharge", None, params="?amount=10")),
        ("Billing subscription", authed("GET", "/billing/subscription")),
        ("Billing usage", authed("GET", "/billing/usage")),
        ("Growth referrals", authed("GET", "/growth/referrals")),
    ]

    charge_id = None
    for label, result in checks:
        status, body = result
        print(f"{label}: {status}")
        if label == "Wallet recharge" and isinstance(body, dict):
            charge_id = body.get("charge_id")

    if charge_id:
        status, _ = authed("POST", f"/wallet/recharge/{charge_id}/confirm")
        print("Wallet confirm:", status)
        status, _ = authed("GET", "/wallet/transactions")
        print("Wallet transactions:", status)

    public_checks = [
        ("Marketplace listings", _request("GET", "/marketplace/listings")),
        ("Templates list", _request("GET", "/templates/agents")),
        ("Revenue leaderboard", _request("GET", "/revenue/leaderboard")),
    ]
    for label, result in public_checks:
        status, _ = result
        print(f"{label}: {status}")


if __name__ == "__main__":
    main()
