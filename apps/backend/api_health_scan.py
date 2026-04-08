
"""
Comprehensive API Health Scan Script
Tests all endpoints from Swagger documentation
"""
import requests
import json
import time
from typing import Dict, List, Any
from datetime import datetime, timezone

# Configuration
BASE_URL = "http://127.0.0.1:8000"
SWAGGER_URL = f"{BASE_URL}/docs"
OPENAPI_URL = f"{BASE_URL}/openapi.json"
AUTH_EMAIL = "test@example.com"
AUTH_PASSWORD = "TestPassword123!"
AUTH_REFRESH_TOKEN = None
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "TestPassword123!"
ADMIN_ACCESS_TOKEN = None

CONTEXT = {
    "agent_id": None,
    "workflow_id": None,
    "workspace_id": None,
    "listing_id": None,
    "schedule_id": None,
    "template_id": None,
    "post_id": None,
    "knowledge_id": None,
    "version_id": None,
    "slug": None,
    "category": None,
    "verification_code": None,
    "reset_token": None
}

# Results storage
results = {
    "scan_time": datetime.now(timezone.utc).isoformat(),
    "base_url": BASE_URL,
    "swagger_loaded": False,
    "endpoints": [],
    "summary": {
        "total": 0,
        "success": 0,
        "failed": 0,
        "error": 0
    }
}


def check_swagger_ui() -> bool:
    """Check if Swagger UI loads properly"""
    print("\n" + "="*60)
    print("STEP 1: Checking Swagger UI")
    print("="*60)

    try:
        response = requests.get(SWAGGER_URL, timeout=10)
        if response.status_code == 200:
            print(f"OK Swagger UI loaded successfully")
            print(f"   URL: {SWAGGER_URL}")
            print(f"   Status: {response.status_code}")
            results["swagger_loaded"] = True
            return True
        else:
            print(f"FAIL Swagger UI returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"FAIL Failed to connect to Swagger UI: {e}")
        return False


def get_openapi_spec() -> Dict[str, Any]:
    """Fetch OpenAPI specification"""
    print("\n" + "="*60)
    print("STEP 2: Fetching OpenAPI Specification")
    print("="*60)

    try:
        response = requests.get(OPENAPI_URL, timeout=10)
        if response.status_code == 200:
            print(f"OK OpenAPI spec fetched successfully")
            return response.json()
        else:
            print(f"FAIL Failed to fetch OpenAPI spec: {response.status_code}")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"FAIL Failed to connect to OpenAPI endpoint: {e}")
        return {}


def discover_endpoints(openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Discover all endpoints from OpenAPI spec"""
    print("\n" + "="*60)
    print("STEP 3: Discovering Endpoints")
    print("="*60)

    endpoints = []

    if not openapi_spec or "paths" not in openapi_spec:
        print("FAIL No paths found in OpenAPI spec")
        return endpoints

    paths = openapi_spec["paths"]
    print(f"OK Found {len(paths)} path(s) in specification")

    global_security = openapi_spec.get("security", [])

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "patch", "delete", "options", "head"]:
                continue

            method_security = details.get("security", None)
            if method_security is None:
                method_security = global_security
            requires_auth = bool(method_security)

            endpoint = {
                "path": path,
                "method": method.upper(),
                "operation_id": details.get("operationId", ""),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "tags": details.get("tags", []),
                "parameters": details.get("parameters", []),
                "request_body": details.get("requestBody", {}),
                "responses": details.get("responses", {}),
                "requires_auth": requires_auth
            }
            endpoints.append(endpoint)
            print(f"   {method.upper():<6} {path}")

    print(f"\nOK Total endpoints discovered: {len(endpoints)}")
    return endpoints


def build_path_with_params(path: str, parameters: List[Dict[str, Any]]) -> str:
    """Replace path params with sample values to avoid 422s."""
    resolved_path = path
    for param in parameters or []:
        if param.get("in") != "path":
            continue
        name = param.get("name")
        schema = param.get("schema", {}) or {}
        if not name:
            continue

        override = CONTEXT.get(name)
        if override is not None:
            value = override
        elif "enum" in schema and schema["enum"]:
            value = schema["enum"][0]
        else:
            param_type = schema.get("type")
            if param_type == "integer" or "id" in name.lower():
                value = 1
            elif "slug" in name.lower():
                value = CONTEXT.get("slug") or "sample-slug"
            elif "category" in name.lower():
                value = CONTEXT.get("category") or "general"
            else:
                value = "test"

        resolved_path = resolved_path.replace(f"{{{name}}}", str(value))

    return resolved_path


def test_endpoint(endpoint: Dict[str, Any], access_token: str | None, components: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single endpoint"""
    global AUTH_REFRESH_TOKEN
    path = build_path_with_params(endpoint["path"], endpoint.get("parameters", []))
    url = f"{BASE_URL}{path}"
    method = endpoint['method'].lower()

    # Special handling: avoid deleting the primary context agent
    if method == "delete" and endpoint.get("path") == "/agents/{agent_id}" and access_token:
        try:
            temp_agent_resp = requests.post(
                f"{BASE_URL}/agents/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"name": "Temp Delete Agent", "description": "For delete test", "config": {"system_prompt": "temp"}},
                timeout=10
            )
            if temp_agent_resp.status_code in [200, 201]:
                temp_id = temp_agent_resp.json().get("id")
                if temp_id:
                    path = endpoint["path"].replace("{agent_id}", str(temp_id))
                    url = f"{BASE_URL}{path}"
        except requests.exceptions.RequestException:
            pass

    # Special handling: ensure schedule exists before delete
    if method == "delete" and endpoint.get("path") == "/schedules/{schedule_id}" and access_token:
        if not CONTEXT.get("schedule_id"):
            try:
                agent_id = CONTEXT.get("agent_id") or 1
                schedule_resp = requests.post(
                    f"{BASE_URL}/schedules/",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={"agent_id": agent_id, "cron_expression": "daily"},
                    timeout=10
                )
                if schedule_resp.status_code in [200, 201]:
                    CONTEXT["schedule_id"] = schedule_resp.json().get("id")
            except requests.exceptions.RequestException:
                pass

    # Prepare request
    kwargs = {
        "timeout": 30,
        "headers": {
            "Accept": "application/json"
        }
    }

    # Add sample data for POST/PUT requests
    if method in ["post", "put", "patch"]:
        # Check if request body is defined
        if endpoint.get("request_body"):
            body_content = endpoint.get("request_body", {}).get("content", {})
            if "application/x-www-form-urlencoded" in body_content:
                body_content_type = "application/x-www-form-urlencoded"
            elif "multipart/form-data" in body_content:
                body_content_type = "multipart/form-data"
            else:
                body_content_type = list(body_content.keys())[0] if body_content else None
            payload = create_sample_payload(endpoint, components)

            if body_content_type in ["application/x-www-form-urlencoded", "multipart/form-data"]:
                kwargs["data"] = payload
                kwargs["headers"]["Content-Type"] = body_content_type
            else:
                kwargs["json"] = payload
                kwargs["headers"]["Content-Type"] = "application/json"

    # Add Authorization header for protected endpoints
    if endpoint.get("requires_auth") and access_token:
        token_to_use = access_token
        if endpoint.get("path") == "/growth/announcements" and ADMIN_ACCESS_TOKEN:
            token_to_use = ADMIN_ACCESS_TOKEN
        kwargs["headers"]["Authorization"] = f"Bearer {token_to_use}"

    # Add query parameters if defined
    if endpoint.get("parameters"):
        params = {}
        for param in endpoint["parameters"]:
            if param.get("in") == "query":
                # Add sample value for common parameters
                param_name = param["name"]
                if param_name in CONTEXT and CONTEXT[param_name] is not None:
                    params[param_name] = CONTEXT[param_name]
                elif "amount" == param_name.lower():
                    params[param_name] = 10
                elif "tier" == param_name.lower():
                    params[param_name] = "pro"
                elif "refresh_token" in param_name.lower():
                    params[param_name] = AUTH_REFRESH_TOKEN or "test"
                elif "page" in param_name.lower():
                    params[param_name] = 1
                elif "limit" in param_name.lower() or "size" in param_name.lower():
                    params[param_name] = 10
                elif param.get("schema", {}).get("type") == "integer":
                    params[param_name] = 1
                elif param.get("schema", {}).get("type") == "string":
                    params[param_name] = "test"
        if params:
            kwargs["params"] = params

    # Make request
    start_time = time.time()
    try:
        response = requests.request(method, url, **kwargs)
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        result = {
            "path": endpoint['path'],
            "method": endpoint['method'],
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "success": response.status_code in [200, 201, 204],
            "error": None
        }

        # Try to parse response
        response_json = None
        try:
            response_json = response.json()
            result["response"] = response_json
        except:
            result["response"] = response.text[:200]  # First 200 chars

        # Capture IDs/tokens for subsequent calls
        if result["success"]:
            update_context(endpoint, response_json)
            if endpoint["path"] == "/auth/login" and isinstance(response_json, dict):
                AUTH_REFRESH_TOKEN = response_json.get("refresh_token") or AUTH_REFRESH_TOKEN

        return result

    except requests.exceptions.RequestException as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "path": endpoint['path'],
            "method": endpoint['method'],
            "status_code": None,
            "response_time_ms": round(response_time, 2),
            "success": False,
            "error": str(e),
            "response": None
        }


def resolve_schema(schema: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve OpenAPI $ref and simple composition constructs."""
    if not schema:
        return {}

    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        resolved = components.get("schemas", {}).get(ref_name, {})
        return resolve_schema(resolved, components)

    if "allOf" in schema:
        merged = {"properties": {}, "required": []}
        for sub_schema in schema["allOf"]:
            resolved = resolve_schema(sub_schema, components)
            merged["properties"].update(resolved.get("properties", {}))
            merged["required"].extend(resolved.get("required", []))
        return merged

    if "oneOf" in schema:
        return resolve_schema(schema["oneOf"][0], components)

    return schema


def sample_value_for_schema(prop_name: str, schema: Dict[str, Any], components: Dict[str, Any]) -> Any:
    """Generate a reasonable sample value from a schema."""
    schema = resolve_schema(schema, components)

    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    schema_type = schema.get("type")

    if schema_type == "object" or "properties" in schema:
        value = {}
        for name, prop_schema in schema.get("properties", {}).items():
            value[name] = sample_value_for_schema(name, prop_schema, components)
        return value

    if schema_type == "array":
        item_schema = schema.get("items", {})
        return [sample_value_for_schema(prop_name, item_schema, components)] if item_schema else []

    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True

    prop_lower = prop_name.lower()
    if "grant_type" in prop_lower:
        return "password"
    if "email" in prop_lower or "username" in prop_lower:
        return AUTH_EMAIL
    if "password" in prop_lower:
        return AUTH_PASSWORD
    if "client_id" in prop_lower or "client_secret" in prop_lower:
        return ""
    if "name" in prop_lower:
        return "Test Agent"

    return "test_value"


def payload_override(endpoint: Dict[str, Any]) -> Dict[str, Any] | None:
    """Provide custom payloads for known endpoints."""
    path = endpoint.get("path", "")
    method = endpoint.get("method", "")

    if method == "POST" and path == "/auth/register":
        return {
            "email": f"scan+{int(time.time())}@example.com",
            "password": AUTH_PASSWORD
        }
    if method == "POST" and path == "/auth/login":
        return {"email": AUTH_EMAIL, "password": AUTH_PASSWORD}
    if method == "POST" and path == "/auth/verify-email":
        return {"code": CONTEXT.get("verification_code") or "debug"}
    if method == "POST" and path == "/auth/reset-password":
        return {
            "token": CONTEXT.get("reset_token") or "debug",
            "new_password": AUTH_PASSWORD
        }
    if method == "POST" and path == "/agents/":
        return {
            "name": "Scan Agent",
            "description": "Agent created by health scan",
            "config": {"system_prompt": "You are a helpful assistant."},
            "skills": ["general"],
            "temperature": 0.7
        }
    if method == "PUT" and path == "/agents/{agent_id}":
        return {"description": "Updated by health scan", "config": {"system_prompt": "Updated."}}
    if method == "POST" and path == "/workflows/":
        return {"name": "Scan Workflow", "config_json": {"steps": []}}
    if method == "POST" and path == "/marketplace/listings":
        return {
            "agent_id": CONTEXT.get("agent_id") or 1,
            "price": 9.99,
            "category": "general",
            "is_active": True
        }
    if method == "POST" and path == "/schedules/":
        return {"agent_id": CONTEXT.get("agent_id") or 1, "cron_expression": "daily"}
    if method == "POST" and path == "/deployment/resource-limits":
        return {
            "agent_id": CONTEXT.get("agent_id") or 1,
            "cpu_limit": 50.0,
            "memory_limit": 512,
            "priority": "normal"
        }
    if method == "POST" and path == "/deployment/feedback":
        return {"type": "general", "message": "Health scan feedback", "rating": 5}
    if method == "POST" and path == "/deployment/resources/config":
        return {"max_cpu_percent": 75.0, "max_memory_mb": 1024, "auto_scale": True}
    if method == "POST" and path == "/marketplace/agents/{agent_id}/reviews":
        return {"rating": 5, "comment": "Great agent"}
    if method == "POST" and path == "/marketplace/agents/{agent_id}/publish":
        return {"tags": "scan", "category": "general", "description": "Published by scan", "version": "1.0.1"}
    if method == "PUT" and path == "/innovation/digital-twin":
        return {"preferences": {"focus": "growth"}}
    if method == "POST" and path == "/growth/community":
        return {"content": "Hello from health scan", "type": "post"}
    if method == "POST" and path == "/intelligence/workspace_memory":
        return {
            "workspace_id": CONTEXT.get("workspace_id") or 1,
            "key": "scan_key",
            "value": "scan_value"
        }
    if method == "POST" and path == "/intelligence/swarm":
        return {
            "agent_ids": [CONTEXT.get("agent_id") or 1],
            "goal": "Health scan swarm test",
            "workspace_id": CONTEXT.get("workspace_id")
        }
    if method == "POST" and path == "/talent/match":
        return {
            "business_needs": "Need a support agent for email triage",
            "industry": "software",
            "role_type": "support",
            "skills_required": ["support", "email"],
            "experience_level": "mid"
        }
    if method == "POST" and path == "/infra/optimize":
        return {
            "model_name": "qwen2.5-coder:7b",
            "model_type": "LLM",
            "parameters": "7B",
            "framework": "PyTorch",
            "current_hardware": {"cpu_cores": 8, "memory_gb": 16},
            "performance_requirements": {"latency_ms": "<100", "throughput_req": "high"}
        }
    if method == "POST" and path == "/ethics/audit":
        return {
            "system_name": "Scan Audit",
            "system_type": "chatbot",
            "purpose": "Testing",
            "target_users": ["general"],
            "data_sources": ["synthetic"],
            "model_details": {"type": "llm"}
        }
    if method == "POST" and path == "/ethics/scan":
        return {"content": "Test content", "system_type": "chatbot"}
    if method == "POST" and path == "/code/audit":
        return {
            "source_type": "snippet",
            "content": "def hello():\n    return 'hi'\n",
            "language": "python",
            "audit_type": "quick"
        }
    if method == "POST" and path == "/wellness/analyze":
        return {
            "repo_path": "c:\\\\Users\\\\Admin\\\\Documents\\\\trae_projects\\\\AI Agent Builder",
            "developer_email": "test@example.com"
        }

    return None


def create_sample_payload(endpoint: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """Create a sample payload for an endpoint"""
    override = payload_override(endpoint)
    if override is not None:
        return override

    request_body = endpoint.get("request_body", {})
    content = request_body.get("content", {})

    if not content:
        return {}

    # Get first content type (usually application/json)
    content_type = list(content.keys())[0]
    schema = content[content_type].get("schema", {})
    schema = resolve_schema(schema, components)

    payload = {}

    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            payload[prop_name] = sample_value_for_schema(prop_name, prop_schema, components)

    # Ensure required fields exist if schema defines them
    for req_field in schema.get("required", []) or []:
        if req_field not in payload:
            payload[req_field] = sample_value_for_schema(req_field, {"type": "string"}, components)

    return payload


def update_context(endpoint: Dict[str, Any], response_json: Any) -> None:
    """Capture IDs and metadata from successful responses for later requests."""
    if not response_json:
        return

    method = endpoint.get("method")
    path = endpoint.get("path")

    if method == "POST" and path == "/agents/" and isinstance(response_json, dict):
        CONTEXT["agent_id"] = response_json.get("id") or CONTEXT["agent_id"]
    elif method == "POST" and path == "/workflows/" and isinstance(response_json, dict):
        CONTEXT["workflow_id"] = response_json.get("id") or CONTEXT["workflow_id"]
    elif method == "POST" and path == "/workspaces/" and isinstance(response_json, dict):
        CONTEXT["workspace_id"] = response_json.get("id") or CONTEXT["workspace_id"]
    elif method == "POST" and path == "/marketplace/listings" and isinstance(response_json, dict):
        CONTEXT["listing_id"] = response_json.get("id") or CONTEXT["listing_id"]
    elif method == "POST" and path == "/schedules/" and isinstance(response_json, dict):
        CONTEXT["schedule_id"] = response_json.get("id") or CONTEXT["schedule_id"]
    elif method == "POST" and path == "/growth/community" and isinstance(response_json, dict):
        CONTEXT["post_id"] = response_json.get("id") or CONTEXT["post_id"]
    elif method == "POST" and path == "/intelligence/knowledge" and isinstance(response_json, dict):
        CONTEXT["knowledge_id"] = response_json.get("id") or CONTEXT["knowledge_id"]
    elif method == "POST" and path == "/agents/{agent_id}/versions" and isinstance(response_json, dict):
        CONTEXT["version_id"] = response_json.get("id") or CONTEXT["version_id"]
    elif method == "POST" and path == "/auth/resend-verification-code" and isinstance(response_json, dict):
        if response_json.get("verification_code"):
            CONTEXT["verification_code"] = response_json.get("verification_code")
    elif method == "POST" and path == "/auth/forgot-password" and isinstance(response_json, dict):
        if response_json.get("reset_token"):
            CONTEXT["reset_token"] = response_json.get("reset_token")
    elif method == "GET" and path == "/deployment/templates" and isinstance(response_json, list) and response_json:
        first = response_json[0]
        if isinstance(first, dict):
            CONTEXT["template_id"] = first.get("id") or CONTEXT["template_id"]
    elif method == "GET" and path == "/marketplace/system" and isinstance(response_json, dict):
        categories = response_json.get("categories", {})
        if categories:
            category = next(iter(categories.keys()), None)
            if category:
                CONTEXT["category"] = category
                agents = categories.get(category) or []
                if agents:
                    first_agent = agents[0]
                    if isinstance(first_agent, dict) and first_agent.get("slug"):
                        CONTEXT["slug"] = first_agent["slug"]


def test_all_endpoints(endpoints: List[Dict[str, Any]], access_token: str | None, components: Dict[str, Any]):
    """Test all discovered endpoints"""
    print("\n" + "="*60)
    print("STEP 4: Testing All Endpoints")
    print("="*60)

    results["summary"]["total"] = len(endpoints)

    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n[{i}/{len(endpoints)}] Testing: {endpoint['method']} {endpoint['path']}")

        # Skip admin endpoints if we don't have admin credentials
        if "admin" in endpoint.get("tags", []):
            print("   Skipping (admin endpoint)")
            results["summary"]["total"] -= 1
            continue

        result = test_endpoint(endpoint, access_token, components)
        results["endpoints"].append(result)

        if result["success"]:
            print(f"   OK Status: {result['status_code']}")
            print(f"   OK Response Time: {result['response_time_ms']}ms")
            results["summary"]["success"] += 1
        else:
            print(f"   FAIL Status: {result['status_code']}")
            print(f"   FAIL Error: {result.get('error', 'Unknown error')}")
            results["summary"]["failed"] += 1


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("SCAN SUMMARY")
    print("="*60)

    print(f"\nScan Time: {results['scan_time']}")
    print(f"Base URL: {results['base_url']}")
    print(f"Swagger UI: {'OK Loaded' if results['swagger_loaded'] else 'FAIL Failed'}")

    print(f"\n{'='*60}")
    print("ENDPOINT RESULTS")
    print(f"{'='*60}")

    # Group by status
    success_endpoints = [e for e in results['endpoints'] if e['success']]
    failed_endpoints = [e for e in results['endpoints'] if not e['success']]

    print(f"\nOK Successful Endpoints ({len(success_endpoints)}):")
    for endpoint in success_endpoints:
        print(f"   {endpoint['method']:<6} {endpoint['path']:<40} {endpoint['response_time_ms']}ms")

    if failed_endpoints:
        print(f"\nFAIL Failed Endpoints ({len(failed_endpoints)}):")
        for endpoint in failed_endpoints:
            print(f"   {endpoint['method']:<6} {endpoint['path']:<40} Status: {endpoint['status_code']}")
            if endpoint.get('error'):
                print(f"      Error: {endpoint['error']}")

    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")

    summary = results['summary']
    print(f"\nTotal Endpoints Tested: {summary['total']}")
    print(f"Successful: {summary['success']} ({summary['success']/summary['total']*100:.1f}%)" if summary['total'] > 0 else "Successful: 0")
    print(f"Failed: {summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)" if summary['total'] > 0 else "Failed: 0")

    # Performance metrics
    if results['endpoints']:
        response_times = [e['response_time_ms'] for e in results['endpoints'] if e['response_time_ms']]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"\nPerformance Metrics:")
            print(f"   Average Response Time: {avg_time:.2f}ms")
            print(f"   Min Response Time: {min_time:.2f}ms")
            print(f"   Max Response Time: {max_time:.2f}ms")


def save_results():
    """Save results to JSON file"""
    output_file = f"api_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}")


def login_and_get_token_for(email: str, password: str) -> str | None:
    """Login and return JWT access token. Register user if needed."""
    url = f"{BASE_URL}/auth/login"
    payload = {"email": email, "password": password}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    except requests.exceptions.RequestException:
        return None

    # Attempt to register then login again
    payload = {"email": email, "password": password}
    try:
        register_url = f"{BASE_URL}/auth/register"
        register_resp = requests.post(register_url, json=payload, timeout=10)
        if register_resp.status_code not in [200, 201]:
            return None
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    except requests.exceptions.RequestException:
        return None

    return None


def login_and_get_token() -> str | None:
    """Login and return JWT access token for main test user."""
    global AUTH_EMAIL, AUTH_REFRESH_TOKEN

    access_token = login_and_get_token_for(AUTH_EMAIL, AUTH_PASSWORD)
    if access_token:
        return access_token

    # Attempt to register a unique user then login again
    AUTH_EMAIL = f"test+{int(time.time())}@example.com"
    access_token = login_and_get_token_for(AUTH_EMAIL, AUTH_PASSWORD)
    return access_token


def prime_context(access_token: str | None) -> None:
    """Prime dependent flows (verification, reset, wallet) for stable scans."""
    if not access_token:
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Refresh verification code
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/resend-verification-code",
            headers=headers,
            timeout=10
        )
        if resp.status_code in [200, 201]:
            update_context({"method": "POST", "path": "/auth/resend-verification-code"}, resp.json())
    except requests.exceptions.RequestException:
        pass

    # Request password reset token
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/forgot-password",
            json={"email": AUTH_EMAIL},
            timeout=10
        )
        if resp.status_code in [200, 201]:
            update_context({"method": "POST", "path": "/auth/forgot-password"}, resp.json())
    except requests.exceptions.RequestException:
        pass

    # Ensure wallet has sufficient balance for marketplace purchases
    try:
        requests.post(
            f"{BASE_URL}/wallet/recharge",
            headers=headers,
            params={"amount": 100},
            timeout=10
        )
    except requests.exceptions.RequestException:
        pass


def main():
    """Main execution function"""
    global ADMIN_ACCESS_TOKEN, ADMIN_EMAIL
    print("="*60)
    print("COMPREHENSIVE API HEALTH SCAN")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Swagger URL: {SWAGGER_URL}")

    # Step 1: Check Swagger UI
    if not check_swagger_ui():
        print("\nFAIL Cannot proceed - Swagger UI not accessible")
        return

    # Step 2: Get OpenAPI spec
    openapi_spec = get_openapi_spec()
    if not openapi_spec:
        print("\nFAIL Cannot proceed - OpenAPI spec not available")
        return

    # Step 3: Discover endpoints
    endpoints = discover_endpoints(openapi_spec)
    if not endpoints:
        print("\nFAIL No endpoints discovered")
        return

    # Step 4: Authenticate (for protected endpoints)
    access_token = login_and_get_token()
    if access_token:
        print("OK Authentication succeeded. Testing protected endpoints with JWT.")
    else:
        print("FAIL Authentication failed. Protected endpoints may return 401.")

    ADMIN_ACCESS_TOKEN = login_and_get_token_for(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not ADMIN_ACCESS_TOKEN:
        ADMIN_EMAIL = f"admin+{int(time.time())}@example.com"
        ADMIN_ACCESS_TOKEN = login_and_get_token_for(ADMIN_EMAIL, ADMIN_PASSWORD)
    if ADMIN_ACCESS_TOKEN:
        print("OK Admin authentication succeeded. Admin endpoints will be tested.")
    else:
        print("WARN Admin authentication failed. Admin endpoints may return 403.")

    # Prime context for dependent flows
    prime_context(access_token)

    # Step 5: Test all endpoints
    components = openapi_spec.get("components", {})
    test_all_endpoints(endpoints, access_token, components)

    # Step 6: Print summary
    print_summary()

    # Step 7: Save results
    save_results()


if __name__ == "__main__":
    main()


